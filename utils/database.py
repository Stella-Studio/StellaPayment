import time
import asyncio
import os
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import io
import csv

load_dotenv()

class DataBase:
    def __init__(self, bot):
        self.bot = bot
        mongo_uri = os.getenv("MONGO_URI")
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

    # ==== Stats helpers and queries ====
    def _period_start(self, period: str) -> datetime:
        now = datetime.now()
        p = (period or "day").lower()
        if p in ("day", "ngay", "hôm nay", "today"):
            return datetime(now.year, now.month, now.day)
        if p in ("week", "tuần", "tuan"):
            start = now - timedelta(days=now.weekday())
            return datetime(start.year, start.month, start.day)
        if p in ("month", "tháng", "thang"):
            return datetime(now.year, now.month, 1)
        return datetime(now.year, now.month, now.day)

    async def top_donors(self, period: str, limit: int = 5):
        start = self._period_start(period)
        pipeline = [
            {"$match": {"timestamp": {"$gte": start}}},
            {"$group": {"_id": "$user_id", "total_amount": {"$sum": "$amount"}}},
            {"$sort": {"total_amount": -1}},
            {"$limit": int(max(1, min(limit, 50)))}
        ]
        return [doc async for doc in self.payments.aggregate(pipeline)]

    async def user_history(self, user_id: int, period: str):
        start = self._period_start(period)
        cursor = self.payments.find({"user_id": user_id, "timestamp": {"$gte": start}}).sort("timestamp", -1)
        records = [doc async for doc in cursor]
        total = sum(r.get("amount", 0) for r in records)
        return total, records

    async def server_totals(self, period: str):
        start = self._period_start(period)
        pipeline = [
            {"$match": {"timestamp": {"$gte": start}}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}, "count": {"$sum": 1}}}
        ]
        docs = [doc async for doc in self.payments.aggregate(pipeline)]
        if not docs:
            return 0, 0
        d = docs[0]
        return int(d.get("total", 0)), int(d.get("count", 0))

    async def rank_in_month(self, user_id: int):
        start = self._period_start("month")
        pipeline = [
            {"$match": {"timestamp": {"$gte": start}}},
            {"$group": {"_id": "$user_id", "total_amount": {"$sum": "$amount"}}},
            {"$sort": {"total_amount": -1}}
        ]
        totals = [doc async for doc in self.payments.aggregate(pipeline)]
        rank = next((idx + 1 for idx, d in enumerate(totals) if int(d["_id"]) == int(user_id)), None)
        user_total = next((int(d["total_amount"]) for d in totals if int(d["_id"]) == int(user_id)), 0)
        return rank, user_total, len(totals)

    async def compare_users(self, user_a: int, user_b: int, period: str):
        start = self._period_start(period)
        pipeline = [
            {"$match": {"timestamp": {"$gte": start}, "user_id": {"$in": [int(user_a), int(user_b)]}}},
            {"$group": {"_id": "$user_id", "total_amount": {"$sum": "$amount"}}}
        ]
        docs = {int(d["_id"]): int(d.get("total_amount", 0)) async for d in self.payments.aggregate(pipeline)}
        return docs.get(int(user_a), 0), docs.get(int(user_b), 0)

    async def reset_stats(self, period: str) -> int:
        start = self._period_start(period)
        res = await self.payments.delete_many({"timestamp": {"$gte": start}})
        await self._bump_version()
        return int(getattr(res, "deleted_count", 0))

    async def check_user(self, user_id: int):
        pipeline = [
            {"$match": {"user_id": int(user_id)}},
            {"$group": {"_id": "$user_id", "total_amount": {"$sum": "$amount"}, "count": {"$sum": 1}}}
        ]
        docs = [doc async for doc in self.payments.aggregate(pipeline)]
        total = int(docs[0].get("total_amount", 0)) if docs else 0
        count = int(docs[0].get("count", 0)) if docs else 0
        recent = [doc async for doc in self.payments.find({"user_id": int(user_id)}).sort("timestamp", -1).limit(20)]
        return total, count, recent

    async def export_month_csv(self, month: int, year: int | None = None) -> tuple[str, str]:
        y = year or datetime.now().year
        start = datetime(y, month, 1)
        end = datetime(y + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
        cursor = self.payments.find({"timestamp": {"$gte": start, "$lt": end}}).sort("timestamp", 1)
        rows = [doc async for doc in cursor]
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["timestamp", "user_id", "amount"])
        for r in rows:
            ts = r.get("timestamp")
            writer.writerow([(ts.isoformat() if isinstance(ts, datetime) else str(ts)), int(r.get("user_id", 0)), int(r.get("amount", 0))])
        content = buf.getvalue()
        buf.close()
        filename = f"transactions_{y}_{str(month).zfill(2)}.csv"
        return filename, content
