import requests

def vndformat(amount: int) -> str:
    return f"{amount:,}vnđ".replace(",", ".")

async def vnd2text(amount: int) -> str:
    response = requests.get(f"http://forum.vdevs.net/nossl/mtw.php?number={amount}")
    return response.json().get("result", "Không thể chuyển đổi") if response.status_code == 200 else "Không thể kết nối"