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
    description_key: str
    order_code: int
    expires_at: int
    embed: discord.Embed
    view: View

class EmptyView(View):
    def __init__(self):
        super().__init__(timeout=None)

async def build_payment(inuser_id: int, payer: discord.User, amount: int, bot: commands.Bot, channel: discord.abc.Messageable) -> BuiltPayment:
    payload = f"{inuser_id} {payer.id} {getattr(channel, 'id', 0)}"
    res = requests.post(
        "https://api.pastes.dev/post",
        data=payload.encode("utf-8"),
        headers={"Content-Type": "text/plain"}
    ).json().get("key")

    # Hạn thanh toán: +3h (múi giờ VN), chuyển sang unix UTC cho Discord timestamp
    expires_time = int((datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')) + timedelta(seconds=30)).astimezone(timezone.utc).timestamp())

    order_code = random.randint(1000, 999_999)
    pay = bot.payos.createPaymentLink(paymentData=PaymentData(
        orderCode=order_code,
        amount=amount,
        expiredAt=expires_time,  # PayOS nhận unix (giây)
        description=res.get("key"),
        returnUrl="https://stellamc.net/",
        cancelUrl="https://stellamc.net/",
    ))

    print(pay)

    # Dùng Discord Timestamps: <t:unix:T> hiển thị giờ cụ thể, <t:unix:R> đếm ngược
    embed = discord.Embed(
        title=":credit_card: Thanh toán bằng QR Code",
        description=(
            "Vui lòng quét mã phía dưới để thanh toán\n\n"
            ":bank: **|** **Thông tin:**\n"
            f"> Người thanh toán: {payer.mention}\n"
            f"> Thành tiền: `{vndformat(amount)}`\n"
            f"> Thành chữ: `{await vnd2text(amount)}`\n"
            f"> Nội dung thanh toán: `{res.get("key")}`\n"
            f"> Mã đơn: `{order_code}`\n\n"
            f":hourglass: Vui lòng thanh toán trước **<t:{pay.expiredAt}:T>** (**<t:{pay.expiredAt}:R>**)"
        ),
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow()
    )
    # QR
    #print(pay.qrCode.replace(" ", "%20").replace(f"{pay.description.split()[0]}", ""))
    embed.set_image(url=f"https://quickchart.io/qr?text={pay.qrCode.replace(" ", "%20")}&margin=1&size=450&centerImageSizeRatio=0.2&dark=82aafd")
    embed.set_footer(text="Cảm ơn bạn đã sử dụng dịch vụ", icon_url="https://qu.ax/yhuTd.png")
    embed.set_author(name=payer.name, icon_url=payer.display_avatar.url)

    return BuiltPayment(
        description_key=res.get("key"),
        order_code=order_code,
        expires_at=expires_time,
        embed=embed,
        view=EmptyView()
    )