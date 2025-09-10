from __future__ import annotations
import discord
from typing import Optional
from discord import app_commands
from discord.ext import commands

from utils.utils import vndformat, EmbedX, hasperm, format_amount_time_line
from utils.views import PaginatedView


class UsersCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="list", description="Liệt kê danh sách khách hàng")
    async def list_customers(self, interaction: discord.Interaction):
        if not await hasperm(interaction, self.bot):
            return
        await interaction.response.defer()
        customers = await self.bot.db.list_customers()
        if not customers:
            return await interaction.followup.send(
                embed=EmbedX(":x: Danh sách trống", "Chưa có giao dịch nào.", discord.Color.orange())
            )

        guilds = interaction.guild
        lines = []
        for idx, c in enumerate(customers, start=1):
            uid, total = int(c["_id"]), c.get("total_amount", 0)
            member, cached = guilds.get_member(uid) if guilds else None, self.bot.get_user(uid)
            lines.append(
                f"**#{idx}** {member.mention if member else f"<@{uid}>"}\n> :bust_in_silhouette: `{member.display_name if member else cached.name if cached else f"ID: {uid}"}` `<{uid}>`\n> :coin: `{vndformat(total)}`\n"
            )

        await PaginatedView(lines, 5, ":notepad_spiral: Danh sách khách hàng").send_message(interaction)

    @app_commands.command(name="top", description="Top đóng góp theo khoảng thời gian")
    @app_commands.describe(period="ngày | tuần | tháng", limit="Số lượng hiển thị (5-10)")
    async def top(self, interaction: discord.Interaction, period: str, limit: Optional[int] = 5):
        if not await hasperm(interaction, self.bot):
            return
        await interaction.response.defer()
        lim = max(1, min(int(limit or 5), 10))
        docs = await self.bot.db.top_donors(period, lim)
        if not docs:
            return await interaction.followup.send(
                embed=EmbedX(":x: Không có dữ liệu", "Chưa có giao dịch trong khoảng thời gian này.", discord.Color.orange())
            )
        guild = interaction.guild
        lines = []
        for idx, d in enumerate(docs, start=1):
            uid, total = int(d["_id"]), int(d.get("total_amount", 0))
            member, cached = guild.get_member(uid) if guild else None, self.bot.get_user(uid)
            prefix = {1: "🥇", 2: "🥈", 3: "🥉"}.get(idx, f"#{idx}")
            lines.append(f"{prefix} {member.mention if member else f"<@{uid}>"} — `{vndformat(total)}`")
        await interaction.followup.send(embed=EmbedX(f"📊 Top {lim} — {period}", "\n".join(lines), discord.Color.blue()))

    @app_commands.command(name="history", description="Lịch sử giao dịch của bạn theo khoảng thời gian")
    @app_commands.describe(period="ngày | tuần | tháng")
    async def history(self, interaction: discord.Interaction, period: str):
        if not await hasperm(interaction, self.bot):
            return
        await interaction.response.defer(ephemeral=True)
        total, records = await self.bot.db.user_history(interaction.user.id, period)
        if not records:
            return await interaction.followup.send(
                embed=EmbedX(":x: Không có giao dịch", "Bạn chưa có giao dịch trong khoảng thời gian này.", discord.Color.orange()),
                ephemeral=True,
            )
        lines = []
        for r in records[:20]:
            lines.append(format_amount_time_line(r.get("amount", 0), r.get("timestamp")))
        desc = f"Tổng: `{vndformat(total)}`\n\n" + "\n".join(lines)
        await interaction.followup.send(embed=EmbedX("🧾 Lịch sử giao dịch", desc, discord.Color.blurple()), ephemeral=True)

    @app_commands.command(name="myrank", description="Xem thứ hạng donate tháng này")
    async def myrank(self, interaction: discord.Interaction):
        if not await hasperm(interaction, self.bot):
            return
        rank, total, population = await self.bot.db.rank_in_month(interaction.user.id)
        if not rank:
            return await interaction.response.send_message(
                embed=EmbedX("🏅 Xếp hạng", "Bạn chưa có đóng góp trong tháng này.", discord.Color.orange()),
                ephemeral=True,
            )
        await interaction.response.send_message(
            embed=EmbedX("🏅 Xếp hạng", f"Bạn đang đứng hạng **#{rank}/{population}** với tổng `{vndformat(total)}`", discord.Color.gold()),
            ephemeral=True,
        )

    @app_commands.command(name="compare", description="So sánh donate giữa bạn và người khác")
    @app_commands.describe(user="Người để so sánh", period="ngày | tuần | tháng")
    async def compare(self, interaction: discord.Interaction, user: discord.User, period: str):
        if not await hasperm(interaction, self.bot):
            return
        a, b = await self.bot.db.compare_users(interaction.user.id, user.id, period)
        more = interaction.user if a >= b else user
        await interaction.response.send_message(
            embed=EmbedX("⚖️ So sánh", f"{interaction.user.mention}: `{vndformat(a)}`\n{user.mention}: `{vndformat(b)}`\n\nNgười đóng góp nhiều hơn: **{more.mention}**", discord.Color.teal())
        )