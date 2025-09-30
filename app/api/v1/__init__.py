from fastapi import APIRouter
from fastapi import FastAPI

from app.api.v1 import auth_router
from app.api.v1 import user_router
from app.api.v1 import buisiness_info_crud
from app.api.v1 import contact_info_crud
from app.api.v1 import payout_info_crud
from app.api.v1 import store_info_crud

app = FastAPI(title="JustClick API")

api_router = APIRouter()


api_router.include_router(auth_router.router)
api_router.include_router(user_router.router)
api_router.include_router(buisiness_info_crud.router)
api_router.include_router(contact_info_crud.router)
api_router.include_router(payout_info_crud.router)
api_router.include_router(store_info_crud.router)
