import time
import asyncio
import os
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

load_dotenv()

class DataBase:
    def __init__(self, bot):
        self.bot = bot
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri: raise RuntimeError("MONGO_URI is not set in .env")
        self.client = AsyncIOMotorClient(mongo_uri, server_api=ServerApi("1"))
        self.db = self.client["stella"]
        self.payments = self.db["payments"]
        self.meta = self.db["meta"]
        self._cache = None
        self._cache_version = -1
        self._cache_ts = 0.0
        self._cache_ttl = 60.0
        self._lock = asyncio.Lock()
        self.bot.logger.info("Database connected")

    async def _meta_version(self) -> int:
        doc = await self.meta.find_one({"_id": "payments_cache"}, projection={"version": 1})
        return int(doc.get("version", 0)) if doc else 0

    def _cache_valid(self, version: int) -> bool:
        return (self._cache is not None and self._cache_version == version and (time.time() - self._cache_ts) < self._cache_ttl)

    async def _bump_version(self):
        await self.meta.update_one({"_id": "payments_cache"}, {"$inc": {"version": 1}, "$currentDate": {"updatedAt": True}}, upsert=True)

    async def save(self, user_id: int, amount: int):
        await self.payments.insert_one({"user_id": user_id, "amount": amount, "timestamp": datetime.now(),})
        await self._bump_version()

        if self._cache is not None:
            row = next((r for r in self._cache if r["_id"] == user_id), None)
            if row: row["total_amount"] += amount
            else: self._cache.append({"_id": user_id, "total_amount": amount})
            self._cache.sort(key=lambda x: x["total_amount"], reverse=True)
            self._cache_ts = time.time()

    async def list_customers(self, use_cache: bool = True):
        meta_ver = await self._meta_version()
        if use_cache and self._cache_valid(meta_ver):
            return self._cache
        async with self._lock:
            meta_ver = await self._meta_version()
            if use_cache and self._cache_valid(meta_ver): return self._cache
            cursor = self.payments.aggregate([{"$group": {"_id": "$user_id", "total_amount": {"$sum": "$amount"}}}, {"$sort": {"total_amount": -1}},])
            self._cache = [doc async for doc in cursor]
            self._cache_version = meta_ver
            self._cache_ts = time.time()
            return self._cache