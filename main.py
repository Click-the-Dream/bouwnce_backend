from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.db.mongo import mongo_conn


@asynccontextmanager
async def fastapi_lifespan(app: FastAPI):
    client = await mongo_conn()
    yield
    client.close()
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


if __name__ == "main":
    uvicorn.run(app, host="0.0.0.0", port=10000)
