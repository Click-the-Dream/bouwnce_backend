from contextlib import asynccontextmanager

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.core.rate_limiter import rate_limiter
from app.core.logger import log_internal_error
from app.db.mongo import mongo_conn
from app.db.postgres_db_conn import engine
from app.worker.jobs import (
    call_health_endpoint_cron_task,
    mark_order_and_payment_abandoned,
    product_reservation,
)

# Not going to be used in production
# Just used to prevent render shuting down due to inactivity
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def fastapi_lifespan(app: FastAPI):

    await rate_limiter.init()
    print("✅ Rate Limiter Initialized successfully")

    client = await mongo_conn()

    if settings.NAME == "staging":
        scheduler.add_job(call_health_endpoint_cron_task, CronTrigger(minute="*/5"))
    scheduler.add_job(product_reservation, CronTrigger(minute="*/1"))
    scheduler.add_job(mark_order_and_payment_abandoned, CronTrigger(minute="*/2"))

    scheduler.start()

    yield

    await engine.dispose()
    print("✅ succeffully shutdown postgres engine")

    client.close()
    print("✅ succeffully shutdown mongo client")

    scheduler.shutdown()
    print("✅ succeffully closed all cron jobs")


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


# Add Global Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):

    message = str(exc) if settings.FASTAPI_ENV == "dev" else "Internal server Error"

    log_internal_error(
        exc=exc,
        message="Unhandled Exception Occurred",
        context={"message": message},
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "status": "error",
            "message": message,
        },
    )



app.include_router(api_router, prefix=settings.API_STR)


if __name__ == "__main__":

    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT)
