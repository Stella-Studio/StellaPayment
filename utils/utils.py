import requests
import discord
from discord.ui import Button, View

def vndformat(amount: int) -> str:
    return f"{amount:,}vnđ".replace(",", ".")

async def vnd2text(amount: int) -> str:
    response = requests.get(f"http://forum.vdevs.net/nossl/mtw.php?number={amount}")
    return response.json().get("result", "Không thể chuyển đổi") if response.status_code == 200 else "Không thể kết nối"

def EmbedX(title: str, desc: str = "", color: int | discord.Color = discord.Color.blurple()) -> discord.Embed:
    return discord.Embed(title=title, description=desc, color=color, timestamp=discord.utils.utcnow())

roles = [1195351303182889031, 1204404049210769418, 1280481283713273969, 894579088843485244, 1275479502050426901]

async def hasperm(interaction: discord.Interaction, bot: discord.Client) -> bool:
    if not interaction.guild or interaction.guild.id != bot.guild_id:
        view = View()
        view.add_item(Button(label="Click to join Stella Studio", url="https://discord.gg/4EBvf37MkU", style=discord.ButtonStyle.link))
        await interaction.response.send_message(
            embed=EmbedX("❌ Lệnh này chỉ có thể sử dụng trong server Stella Studio", color=discord.Color.red()),
            view=view,
            ephemeral=True,
        )
        return False
    if not any(role.id in roles for role in interaction.user.roles):
        await interaction.response.send_message(
            embed=EmbedX("❌ Bạn không có quyền sử dụng lệnh này!", color=discord.Color.red()),
            ephemeral=True,
        )
        return False
    return True

def format_amount_time_line(amount, ts) -> str:
    return f"• `{vndformat(int(amount))}` — <t:{int(ts.timestamp())}:f>"