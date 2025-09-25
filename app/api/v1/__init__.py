from fastapi import APIRouter

from app.api.v1 import auth_router, product_router, user_router, verification_router

api_router = APIRouter()


api_router.include_router(auth_router.router)
api_router.include_router(user_router.router)
api_router.include_router(verification_router.router)
api_router.include_router(product_router.router)
