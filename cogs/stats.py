import psutil
import discord
from datetime import datetime
from discord import app_commands
from discord.ext import commands

from __future__ import annotations
from utils.utils import EmbedX, vndformat, hasperm

class StatsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="status", description="Show bot status")
    async def status(self, interaction: discord.Interaction):
        if not await hasperm(interaction, self.bot):
            return
        ram = psutil.virtual_memory()
        desc = (
            f"📡 **Ping:** `{round(self.bot.latency * 1000, 1)}ms`\n"
            f"💾 **RAM:** `{ram.used // (1024 * 1024):,} MB / {ram.total // (1024 * 1024):,} MB ({ram.percent}%)`\n"
            f"🕒 **Uptime:** `{str(datetime.now() - self.bot.start_time).split('.')[0]}`"
        )
        await interaction.response.send_message(embed=EmbedX("📊 Bot Status", desc, discord.Color.green()))

    @app_commands.command(name="daily", description="Thống kê donate hôm nay")
    async def daily(self, interaction: discord.Interaction):
        if not await hasperm(interaction, self.bot):
            return
        total, count = await self.bot.db.server_totals("day")
        await interaction.response.send_message(embed=EmbedX("📈 Hôm nay", f"Giao dịch: `{count}`\nTổng: `{vndformat(total)}`", discord.Color.green()))

    @app_commands.command(name="serverstats", description="Tổng doanh thu hôm nay/tuần/tháng")
    @app_commands.describe(period="ngày | tuần | tháng")
    async def serverstats(self, interaction: discord.Interaction, period: str):
        if not await hasperm(interaction, self.bot):
            return
        total, count = await self.bot.db.server_totals(period)
        await interaction.response.send_message(
            embed=EmbedX("🏦 Doanh thu", f"Kỳ: `{period}`\nGiao dịch: `{count}`\nTổng: `{vndformat(total)}`", discord.Color.purple())
        )