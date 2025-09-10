import uvicorn
import asyncio
import discord
import os
from dotenv import load_dotenv
from utils.bot import Bot
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager

load_dotenv()

discord.utils.setup_logging(root=False)    
app = FastAPI(title="Stella | Callback")
bot = Bot("!", help_command=None, intents=discord.Intents.all())
bot.pending_payments = {}
bot.guild_id = getattr(bot, "guild_id", None)

@asynccontextmanager
async def lifespan(app: FastAPI):
    bot.logger.info("Starting application...")
    asyncio.create_task(bot.start(os.getenv("DISCORD_TOKEN")))
    yield
    bot.logger.info("Shutting down...")
    await bot.close()

app.router.lifespan_context = lifespan  

@app.post("/api/payos")
async def payos_callback(request: Request):
    data = await request.json()
    bot.dispatch("payos", data)
    return {"success": True}

if __name__ == "__main__":
    # Chỉnh port phù hợp với bạn: port=<custom port>
    uvicorn.run(app, host="0.0.0.0", port=19131, loop="asyncio")