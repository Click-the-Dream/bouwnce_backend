import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.service import MetricService
from app.db.postgres_db_conn import get_async_session


async def run_metric_job():
    async with get_async_session() as db:
        await MetricService.calculate_all_stores(db)

async def reset_monthly_aov():
    async with get_async_session() as db:
        await db.execute("UPDATE store_metrics SET avg_order_value = 0")
        await db.commit()

async def reset_yearly_revenue():
    async with get_async_session() as db:
        await db.execute("UPDATE store_metrics SET total_revenue = 0")
        await db.commit()

def init_store_cron_jobs():
    scheduler = AsyncIOScheduler()

    scheduler.add_job(lambda: asyncio.create_task(run_metric_job()), "cron", hour=2)

    scheduler.add_job(lambda: asyncio.create_task(reset_monthly_aov()), "cron", day=1, hour=0, minute=5)

    scheduler.add_job(lambda: asyncio.create_task(reset_yearly_revenue()), "cron", month=1, day=1, hour=0, minute=10)

    scheduler.start()
