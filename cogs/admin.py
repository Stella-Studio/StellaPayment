from __future__ import annotations
import io
import discord
from typing import Optional
from discord import app_commands
from discord.ext import commands

from utils.utils import EmbedX, vndformat, hasperm, format_amount_time_line


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="resetstats", description="Reset thống kê theo khoảng thời gian")
    @app_commands.describe(period="ngày | tuần | tháng")
    async def resetstats(self, interaction: discord.Interaction, period: str):
        if not await hasperm(interaction, self.bot):
            return
        await interaction.response.defer(ephemeral=True)
        deleted = await self.bot.db.reset_stats(period)
        await interaction.followup.send(
            embed=EmbedX("🧹 Đã reset", f"Đã xoá `{deleted}` giao dịch trong kỳ `{period}`.", discord.Color.red()),
            ephemeral=True,
        )

    @app_commands.command(name="check", description="Xem tổng và lịch sử của một user")
    @app_commands.describe(user="Người dùng cần kiểm tra")
    async def check(self, interaction: discord.Interaction, user: discord.User):
        if not await hasperm(interaction, self.bot):
            return
        await interaction.response.defer(ephemeral=True)
        total, count, recent = await self.bot.db.check_user(user.id)
        if not count:
            return await interaction.followup.send(
                embed=EmbedX(":x: Không có dữ liệu", f"{user.mention} chưa có giao dịch.", discord.Color.orange()),
                ephemeral=True,
            )
        lines = []
        for r in recent:
            lines.append(format_amount_time_line(r.get("amount", 0), r.get("timestamp")))
        desc = f"Người dùng: {user.mention}\nTổng: `{vndformat(total)}` — Giao dịch: `{count}`\n\n" + "\n".join(lines)
        await interaction.followup.send(embed=EmbedX("🔎 Kiểm tra người dùng", desc, discord.Color.blurple()), ephemeral=True)

    @app_commands.command(name="export", description="Xuất CSV lịch sử giao dịch một tháng")
    @app_commands.describe(month="Tháng (1-12)", year="Năm (mặc định: năm hiện tại)")
    async def export(self, interaction: discord.Interaction, month: int, year: Optional[int] = None):
        if not await hasperm(interaction, self.bot):
            return
        await interaction.response.defer(ephemeral=True)
        filename, content = await self.bot.db.export_month_csv(month, year)
        await interaction.followup.send(content="CSV xuất thành công", file=discord.File(io.BytesIO(content.encode('utf-8')), filename=filename), ephemeral=True)