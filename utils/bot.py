import discord
import logging
import asyncio
import socket
import os
from dotenv import load_dotenv
from payos import PayOS
from datetime import datetime
from discord.ext import commands
from utils.database import DataBase
from cogs.commands import BotCommands

load_dotenv()

class Bot(commands.Bot):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.start_time = datetime.now()
        self.logger = logging.getLogger("discord.client")
        self.guild_id = 1275475899818442866
        self.log_channel = 1384716948939735084
        self.db = DataBase(self)
        self.payos = PayOS(client_id=os.getenv("PAYOS_CLIENT_ID"), api_key=os.getenv("PAYOS_API_KEY"), checksum_key=os.getenv("PAYOS_CHECKSUM_KEY"))

    async def setup_hook(self):
        await self.add_cog(BotCommands(self))
        await self.tree.sync()
    
    async def on_ready(self):
        self.logger.info(f"Bot logged in as {self.user}")
        
    async def on_disconnect(self):
        self.logger.error("Bot disconnected! Attempting to reconnect...")

    async def on_resumed(self):
        self.logger.info("Bot has successfully reconnected!")

    async def check_network(self):
        try:
            await asyncio.get_event_loop().getaddrinfo("gateway.discord.gg", 443)
            return True
        except socket.gaierror:
            self.logger.error("No network connectivity or DNS resolution failed.")
            return False

    async def run_bot(self, token):
        while True:
            try:
                await self.start(token)
            except discord.ConnectionClosed:
                self.logger.info("Connection closed, retrying in 5 seconds...")
                await asyncio.sleep(5)
            except Exception as e:
                self.logger.info(f"Unexpected error: {e}")
                await asyncio.sleep(5)
                
    async def log(self, title: str, message: str, user: discord.User = None) -> None:
        channel = self.get_channel(self.log_channel)
        embed = discord.Embed(title=title, description=message, color=discord.Color.dark_gray(), timestamp=discord.utils.utcnow())
        if user: embed.set_author(name=user.name, icon_url=user.display_avatar.url)
        await channel.send(embed=embed)