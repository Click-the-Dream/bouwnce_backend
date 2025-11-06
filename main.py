from contextlib import asynccontextmanager
from time import sleep

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.db.mongo import mongo_conn

# Not going to be used in production
# Just used to prevent render shuting down due to inactivity
scheduler = AsyncIOScheduler()


async def cron_task():
    for _ in range(10):
        sleep(1)


@asynccontextmanager
async def fastapi_lifespan(app: FastAPI):
    client = await mongo_conn()
    scheduler.add_job(cron_task, CronTrigger(minute="*/2"))
    scheduler.start()
    yield
    client.close()
    scheduler.shutdown()
    print("Mongodb Client Closed successfully")


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    version="1.0.0",
    description="APIs for the Bouwnce Backend",
    lifespan=fastapi_lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_STR)


if __name__ == "__main__":

    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT)
