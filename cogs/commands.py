from __future__ import annotations
import asyncio
import time
import discord
import psutil
import requests
import io
from dataclasses import dataclass
from typing import Optional
from discord.ui import Button, View
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from utils.utils import vndformat, EmbedX
from utils.views import PaginatedView
from utils.views_callback import build_payment

roles = [1195351303182889031, 1204404049210769418, 1280481283713273969, 894579088843485244, 1275479502050426901]

@dataclass
class PaymentRecord:
    description: str
    order_code: int
    amount: int
    inuser_id: int
    payer_id: int
    channel_id: int
    message_id: int
    expires_at: int
    paid: bool = False
    cancelled: bool = False
    expire_task: Optional[asyncio.Task] = None

class BotCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def hasperm(self, interaction: discord.Interaction) -> bool:
        if not interaction.guild or interaction.guild.id != self.bot.guild_id:
            view = View().add_item(Button(label="Click to join Stella Studio", url="https://discord.gg/4EBvf37MkU", style=discord.ButtonStyle.link))
            await interaction.response.send_message(embed=EmbedX("❌ Lệnh này chỉ có thể sử dụng trong server Stella Studio", color=discord.Color.red()), view=view, ephemeral=True)
            return False
        if not any(role.id in roles for role in interaction.user.roles):
            await interaction.response.send_message(embed=EmbedX("❌ Bạn không có quyền sử dụng lệnh này!", color=discord.Color.red()), ephemeral=True)
            return False
        return True

    @app_commands.command(name="payment", description="Định dạng <user> <số tiền> [ghi chú]")
    @app_commands.describe(user="Vui lòng chọn khách hàng", amount="Định dạng tiền VNĐ", note="Ghi chú ngắn sẽ hiển thị trong hoá đơn")
    async def payment(self, interaction: discord.Interaction, user: discord.User, amount: int, note: Optional[str] = None):
        await interaction.response.defer(ephemeral=True)
        if not await self.hasperm(interaction): return
        if amount < 2000:
            await interaction.followup.send(embed=EmbedX("❌ Số tiền tối thiểu là 2,000 VND", color=discord.Color.red()), ephemeral=True)
            return

        pay = await build_payment(inuser=interaction.user.id, payer=user, amount=amount, bot=self.bot, channel=interaction.channel, note=note)
        sent: discord.Message = await interaction.channel.send(embed=pay.embed, view=pay.view)
        record = PaymentRecord(pay.description, pay.ordercode, amount, interaction.user.id, user.id, sent.channel.id, sent.id, pay.expiresat)
        self.bot.pending_payments[pay.description] = record
        record.expire_task = asyncio.create_task(self.autodelete(pay.description))

        await interaction.followup.send(embed=EmbedX("✅ Đã tạo QR trong kênh", color=discord.Color.green()), ephemeral=True)

    async def autodelete(self, description: str):
        try:
            record: Optional[PaymentRecord] = self.bot.pending_payments.get(description)
            if not record: return
            await asyncio.sleep(max(0, record.expires_at - int(time.time())))
            record = self.bot.pending_payments.get(description)
            if not record or record.paid or record.cancelled: return

            channel = self.bot.get_channel(record.channel_id)
            if isinstance(channel, (discord.TextChannel, discord.Thread)):
                try: msg = await channel.fetch_message(record.message_id)
                except Exception:
                    self.bot.pending_payments.pop(description, None)
                    return
                latest = self.bot.pending_payments.get(description)
                if not latest or latest.paid or latest.cancelled: return

                await msg.delete()
                try: await channel.send(embed=EmbedX("⌛ Hóa đơn đã hết hạn", f"Đơn `{record.order_code}` cho <@{record.payer_id}> đã hết hạn.", discord.Color.orange()))
                except Exception: pass
            self.bot.pending_payments.pop(description, None)

        except asyncio.CancelledError: return
        except Exception as e: self.bot.logger.error(f"Auto-expire error: {e}")

    @app_commands.command(name="cancelpayment", description="Huỷ một hóa đơn đang chờ (theo mã đơn)")
    @app_commands.describe(order_code="Mã đơn (orderCode) đã tạo")
    async def cancelpayment(self, interaction: discord.Interaction, order_code: int):
        await interaction.response.defer(ephemeral=True)
        if not await self.hasperm(interaction): return
        desc_key, record = next(((k, v) for k, v in list(self.bot.pending_payments.items()) if v.order_code == order_code), (None, None))
        if not record:
            await interaction.followup.send(embed=EmbedX("❌ Không tìm thấy hóa đơn đang chờ với mã này", color=discord.Color.red()), ephemeral=True)
            return
        if record.paid:
            await interaction.followup.send(embed=EmbedX("ℹ️ Hóa đơn này đã thanh toán trước đó", color=discord.Color.blue()), ephemeral=True)
            return
        if record.expire_task and not record.expire_task.done():
            record.expire_task.cancel()
        record.cancelled = True
        channel = self.bot.get_channel(record.channel_id)
        if isinstance(channel, (discord.TextChannel, discord.Thread)):
            try:
                msg = await channel.fetch_message(record.message_id)
                await channel.send(reference=msg, mention_author=False,
                    embed=EmbedX("🛑 Hóa đơn đã bị huỷ", f"Đơn `{record.order_code}` đã bị huỷ bởi <@{interaction.user.id}>.", discord.Color.red()))
                await msg.delete()
            except: pass
        if desc_key:
            self.bot.pending_payments.pop(desc_key, None)

        await interaction.followup.send(embed=EmbedX("✅ Đã huỷ hóa đơn", f"Mã đơn: `{record.order_code}` cho <@{record.payer_id}> đã được huỷ thành công.", discord.Color.green()), ephemeral=True)

    @app_commands.command(name="status", description="Show bot status")
    async def status(self, interaction: discord.Interaction):
        if not await self.hasperm(interaction): return
        ram = psutil.virtual_memory()
        desc = (
            f"📡 **Ping:** `{round(self.bot.latency * 1000, 1)}ms`\n"
            f"💾 **RAM:** `{ram.used // (1024 * 1024):,} MB / {ram.total // (1024 * 1024):,} MB ({ram.percent}%)`\n"
            f"🕒 **Uptime:** `{str(datetime.now() - self.bot.start_time).split('.')[0]}`"
        )
        await interaction.response.send_message(embed=EmbedX("📊 Bot Status", desc, discord.Color.green()))

    @app_commands.command(name="list", description="Liệt kê danh sách khách hàng")
    async def list_customers(self, interaction: discord.Interaction):
        if not await self.hasperm(interaction): return
        await interaction.response.defer()
        customers = await self.bot.db.list_customers()
        if not customers: return await interaction.followup.send(embed=EmbedX(":x: Danh sách trống", "Chưa có giao dịch nào.", discord.Color.orange()))

        guilds = interaction.guild
        lines = []
        for idx, c in enumerate(customers, start=1):
            uid, total = int(c["_id"]), c.get("total_amount", 0)
            member, cached = guilds.get_member(uid) if guilds else None, self.bot.get_user(uid)
            lines.append(f"**#{idx}** {member.mention if member else f"<@{uid}>"}\n> :bust_in_silhouette: `{member.display_name if member else cached.name if cached else f"ID: {uid}"}` `<{uid}>`\n> :coin: `{vndformat(total)}`\n")

        await PaginatedView(lines, 5, ":notepad_spiral: Danh sách khách hàng").send_message(interaction)

    @app_commands.command(name="top", description="Top đóng góp theo khoảng thời gian")
    @app_commands.describe(period="ngày | tuần | tháng", limit="Số lượng hiển thị (5-10)")
    async def top(self, interaction: discord.Interaction, period: str, limit: Optional[int] = 5):
        if not await self.hasperm(interaction): return
        await interaction.response.defer()
        lim = max(1, min(int(limit or 5), 10))
        docs = await self.bot.db.top_donors(period, lim)
        if not docs:
            return await interaction.followup.send(embed=EmbedX(":x: Không có dữ liệu", "Chưa có giao dịch trong khoảng thời gian này.", discord.Color.orange()))
        guild = interaction.guild
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        lines = []
        for idx, d in enumerate(docs, start=1):
            uid, total = int(d["_id"]), int(d.get("total_amount", 0))
            member, cached = guild.get_member(uid) if guild else None, self.bot.get_user(uid)
            prefix = medals.get(idx, f"#{idx}")
            lines.append(f"{prefix} {member.mention if member else f"<@{uid}>"} — `{vndformat(total)}`")
        await interaction.followup.send(embed=EmbedX(f"📊 Top {lim} — {period}", "\n".join(lines), discord.Color.blue()))

    @app_commands.command(name="history", description="Lịch sử giao dịch của bạn theo khoảng thời gian")
    @app_commands.describe(period="ngày | tuần | tháng")
    async def history(self, interaction: discord.Interaction, period: str):
        if not await self.hasperm(interaction): return
        await interaction.response.defer(ephemeral=True)
        total, records = await self.bot.db.user_history(interaction.user.id, period)
        if not records:
            return await interaction.followup.send(embed=EmbedX(":x: Không có giao dịch", "Bạn chưa có giao dịch trong khoảng thời gian này.", discord.Color.orange()), ephemeral=True)
        lines = []
        for r in records[:20]:
            ts = r.get("timestamp")
            ts_unix = int(ts.timestamp()) if hasattr(ts, "timestamp") else 0
            amt = int(r.get("amount", 0))
            lines.append(f"• `{vndformat(amt)}` — <t:{ts_unix}:f>")
        desc = f"Tổng: `{vndformat(total)}`\n\n" + "\n".join(lines)
        await interaction.followup.send(embed=EmbedX("🧾 Lịch sử giao dịch", desc, discord.Color.blurple()), ephemeral=True)

    @app_commands.command(name="myrank", description="Xem thứ hạng donate tháng này")
    async def myrank(self, interaction: discord.Interaction):
        if not await self.hasperm(interaction): return
        rank, total, population = await self.bot.db.rank_in_month(interaction.user.id)
        if not rank:
            return await interaction.response.send_message(embed=EmbedX("🏅 Xếp hạng","Bạn chưa có đóng góp trong tháng này.",discord.Color.orange()), ephemeral=True)
        await interaction.response.send_message(embed=EmbedX("🏅 Xếp hạng", f"Bạn đang đứng hạng **#{rank}/{population}** với tổng `{vndformat(total)}`", discord.Color.gold()), ephemeral=True)

    @app_commands.command(name="daily", description="Thống kê donate hôm nay")
    async def daily(self, interaction: discord.Interaction):
        if not await self.hasperm(interaction): return
        total, count = await self.bot.db.server_totals("day")
        await interaction.response.send_message(embed=EmbedX("📈 Hôm nay", f"Giao dịch: `{count}`\nTổng: `{vndformat(total)}`", discord.Color.green()))

    @app_commands.command(name="serverstats", description="Tổng doanh thu hôm nay/tuần/tháng")
    @app_commands.describe(period="ngày | tuần | tháng")
    async def serverstats(self, interaction: discord.Interaction, period: str):
        if not await self.hasperm(interaction): return
        total, count = await self.bot.db.server_totals(period)
        await interaction.response.send_message(embed=EmbedX("🏦 Doanh thu", f"Kỳ: `{period}`\nGiao dịch: `{count}`\nTổng: `{vndformat(total)}`", discord.Color.purple()))

    @app_commands.command(name="compare", description="So sánh donate giữa bạn và người khác")
    @app_commands.describe(user="Người để so sánh", period="ngày | tuần | tháng")
    async def compare(self, interaction: discord.Interaction, user: discord.User, period: str):
        if not await self.hasperm(interaction): return
        a, b = await self.bot.db.compare_users(interaction.user.id, user.id, period)
        more = interaction.user if a >= b else user
        await interaction.response.send_message(embed=EmbedX("⚖️ So sánh", f"{interaction.user.mention}: `{vndformat(a)}`\n{user.mention}: `{vndformat(b)}`\n\nNgười đóng góp nhiều hơn: **{more.mention}**", discord.Color.teal()))

    @app_commands.command(name="resetstats", description="[Admin] Reset thống kê theo khoảng thời gian")
    @app_commands.describe(period="ngày | tuần | tháng")
    async def resetstats(self, interaction: discord.Interaction, period: str):
        if not await self.hasperm(interaction): return
        await interaction.response.defer(ephemeral=True)
        deleted = await self.bot.db.reset_stats(period)
        await interaction.followup.send(embed=EmbedX("🧹 Đã reset", f"Đã xoá `{deleted}` giao dịch trong kỳ `{period}`.", discord.Color.red()), ephemeral=True)

    @app_commands.command(name="check", description="[Admin] Xem tổng và lịch sử của một user")
    @app_commands.describe(user="Người dùng cần kiểm tra")
    async def check(self, interaction: discord.Interaction, user: discord.User):
        if not await self.hasperm(interaction): return
        await interaction.response.defer(ephemeral=True)
        total, count, recent = await self.bot.db.check_user(user.id)
        if not count:
            return await interaction.followup.send(embed=EmbedX(":x: Không có dữ liệu", f"{user.mention} chưa có giao dịch.", discord.Color.orange()), ephemeral=True)
        lines = []
        for r in recent:
            ts = r.get("timestamp")
            ts_unix = int(ts.timestamp()) if hasattr(ts, "timestamp") else 0
            amt = int(r.get("amount", 0))
            lines.append(f"• `{vndformat(amt)}` — <t:{ts_unix}:f>")
        desc = f"Người dùng: {user.mention}\nTổng: `{vndformat(total)}` — Giao dịch: `{count}`\n\n" + "\n".join(lines)
        await interaction.followup.send(embed=EmbedX("🔎 Kiểm tra người dùng", desc, discord.Color.blurple()), ephemeral=True)

    @app_commands.command(name="export", description="[Admin] Xuất CSV lịch sử giao dịch một tháng")
    @app_commands.describe(month="Tháng (1-12)", year="Năm (mặc định: năm hiện tại)")
    async def export(self, interaction: discord.Interaction, month: int, year: Optional[int] = None):
        if not await self.hasperm(interaction): return
        await interaction.response.defer(ephemeral=True)
        filename, content = await self.bot.db.export_month_csv(month, year)
        buf = io.BytesIO(content.encode('utf-8'))
        await interaction.followup.send(content="CSV xuất thành công", file=discord.File(buf, filename=filename), ephemeral=True)

    @commands.Cog.listener()
    async def on_payos(self, data: dict) -> None:
        try:
            if not bool(data.get("success", False)) and str(data.get("desc", "")).lower() != "success": return await self.bot.log(title="❌ Webhook thất bại", message=f"Payload: `{data}`")

            desc_key: str = str(data["data"]["description"]).split()[-1]
            amount: int = int(data["data"]["amount"])
            order_code: Optional[int] = data["data"].get("orderCode")
            paste = requests.get(f"https://api.pastes.dev/{desc_key}", headers={"User-Agent": "Stella/1.0"}).text.split()

            inuser = await self.bot.fetch_user(int(paste[0]))
            payer = await self.bot.fetch_user(int(paste[1]))
            await self.bot.db.save(int(paste[1]), amount)

            guild = self.bot.get_guild(self.bot.guild_id)
            member = guild.get_member(payer.id) if guild else None
            role = guild.get_role(894580615146508289) if guild else None
            record: Optional[PaymentRecord] = self.bot.pending_payments.get(desc_key)
            channel = self.bot.get_channel(int(paste[2]))
            if record and record.expire_task and not record.expire_task.done():
                record.expire_task.cancel()

            pay_time_unix = int(time.time())
            embed = EmbedX(
                ":ringed_planet: Thanh toán thành công",
                (
                    "Cảm ơn bạn đã sử dụng dịch vụ của chúng tôi\n\n"
                    ":bank: **|** **Thông tin**:\n"
                    f"> Người thụ hưởng: {inuser.mention}\n"
                    f"> Số tiền đã thanh toán: `{amount:,}vnđ`\n"
                    f"> Thanh toán bởi: {payer.mention}\n"
                    f"> Mã đơn: `{order_code or (record.order_code if record else '—')}`\n\n"
                    f":hourglass: Thời gian thanh toán: **<t:{pay_time_unix}:F>**\n"
                ),
                discord.Color.blue()
            )
            embed.set_author(name=payer.name, icon_url=payer.display_avatar.url)
            if member and role and role not in member.roles:
                await member.add_roles(role)
                embed.description += f"\n> Đã thêm role `Customer` cho `{payer.name}`!"
            if record and isinstance(channel, (discord.TextChannel, discord.Thread)):
                try:
                    msg = await channel.fetch_message(record.message_id)
                    await channel.send(reference=msg.to_reference(), mention_author=False, embed=embed)
                    await msg.delete()
                except Exception:
                    if isinstance(channel, (discord.TextChannel, discord.Thread)): await channel.send(embed=embed)
                record.paid = True
                self.bot.pending_payments.pop(desc_key, None)
            else:
                if isinstance(channel, (discord.TextChannel, discord.Thread)):
                    await channel.send(embed=embed)
            await self.bot.log(embed.title, embed.description, payer)

        except Exception as e:
            self.bot.logger.error(f"Lỗi xử lý webhook: {e}")
