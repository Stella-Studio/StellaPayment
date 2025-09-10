import pytz
import random
import discord
import requests
from dataclasses import dataclass
from discord.ui import View
from discord.ext import commands
from payos import PaymentData
from utils.utils import vndformat, vnd2text
from datetime import datetime, timedelta, timezone

@dataclass
class BuiltPayment:
    description: str
    ordercode: int
    expiresat: int
    embed: discord.Embed
    view: View

class EmptyView(View):
    def __init__(self):
        super().__init__(timeout=None)

async def build_payment(inuser: int, payer: discord.User, amount: int, bot: commands.Bot, channel: discord.abc.Messageable, note: str | None = None) -> BuiltPayment:
    description = requests.post("https://api.pastes.dev/post", data=f"{inuser} {payer.id} {getattr(channel, 'id', 0)}".encode("utf-8"), headers={"Content-Type": "text/plain"}).json().get("key")
    ordercode = random.randint(1000, 999_999)
    pay = bot.payos.createPaymentLink(paymentData=PaymentData(
        orderCode=ordercode,
        amount=amount,
        expiredAt=int((datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')) + timedelta(hours=3)).astimezone(timezone.utc).timestamp()),
        description=description,
        returnUrl="https://stellamc.net/",
        cancelUrl="https://stellamc.net/",
    ))

    base_desc = (
        "Vui lòng quét mã phía dưới để thanh toán\n\n"
        ":bank: **|** **Thông tin:**\n"
        f"> Người thanh toán: {payer.mention}\n"
        f"> Thành tiền: `{vndformat(amount)}`\n"
        f"> Thành chữ: `{await vnd2text(amount)}`\n"
        f"> Nội dung thanh toán: `{description}`\n"
        f"> Mã đơn: `{ordercode}`\n"
    )

    if note: base_desc += f"> Ghi chú: `{note[:120]}`\n"
    base_desc += f"\n:hourglass: Vui lòng thanh toán trước **<t:{pay.expiredAt}:T>** (**<t:{pay.expiredAt}:R>**)**\n\n*Author: _karisan_ • Support: Saly*"

    embed = discord.Embed(
        title=":credit_card: Thanh toán bằng QR Code",
        description=base_desc,
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow()
    )

    embed.set_image(url=f"https://quickchart.io/qr?text={pay.qrCode.replace(' ', '%20')}&margin=1&size=450&centerImageSizeRatio=0.2&dark=82aafd")
    embed.set_footer(text="Cảm ơn bạn đã sử dụng dịch vụ", icon_url="https://qu.ax/yhuTd.png")
    embed.set_author(name=payer.name, icon_url=payer.display_avatar.url)

    return BuiltPayment(description=description, ordercode=ordercode, expiresat=pay.expiredAt, embed=embed, view=EmptyView())