from typing import Annotated

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from app.api.dependencies import (
    CurrentAdmin,
    CurrentStore,
    dbSessionDep,
    redisSessionDep,
)
from app.schemas.product import (
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    PaginatedProductResponse,
    ProductResponse,
)
from app.service.product_service import product_service

router = APIRouter(prefix="/products", tags=["Products"])


ImageCreate = Annotated[list[UploadFile], File(...)]
ImageUpdate = Annotated[list[UploadFile] | None, File(...)]


@router.get(
    "/categories",
    summary="List of available product categories that you can choose from when creating a product",
    description="When creating a product, you must only use from the list of available categories",
    status_code=status.HTTP_200_OK,
    response_model=CategoryListResponse,
)
async def get_all_product_categories():
    return await product_service.get_product_categories()


@router.post(
    "/categories",
    summary="Create a new product category (Only Admin)",
    status_code=status.HTTP_201_CREATED,
    response_model=CategoryResponse,
)
async def create_product_category(category_data: CategoryCreate, _: CurrentAdmin):
    return await product_service.create_product_category(category_data.model_dump())


@router.delete(
    "/categories/{id}",
    summary="Delete product category by id (Only Admin)",
    status_code=status.HTTP_200_OK,
)
async def delete_product_category(id: str, _: CurrentAdmin):
    return await product_service.delete_product_category(id)


@router.post(
    "/",
    summary="Create a product for logged in vendor's store",
    status_code=status.HTTP_201_CREATED,
    response_model=ProductResponse,
)
async def create_product(
    current_store: CurrentStore,
    name: Annotated[str, Form(min_length=2, examples=["Round Neck"])],
    description: Annotated[
        str, Form(min_length=5, examples=["This is straight from New York"])
    ],
    amount: Annotated[int, Form(ge=0, examples=[25000])],
    stock: Annotated[int, Form(ge=0, examples=[20])],
    category: Annotated[str, Form(examples=["clothes"])],
    images: ImageCreate,
    db: dbSessionDep,
):

    product_data = {
        "name": name,
        "description": description,
        "amount": amount,
        "stock": stock,
        "category": category,
    }
    return await product_service.create_product(
        store_id=str(current_store.id), product_data=product_data, images=images, db=db
    )


@router.get(
    "/",
    summary="Get all product optionally by filter",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedProductResponse,
)
async def get_all_products(
    redis: redisSessionDep,
    name: str | None = Query(default=None, min_lenght=3, description="name of product"),
    category: str | None = Query(
        default=None, min_length=3, description="Category of product to search for"
    ),
    page: int | None = Query(default=1, gt=0, description="The page number to fetch"),
    per_page: int | None = Query(
        default=10, gt=0, description="The number of products in a page"
    ),
):
    return await product_service.get_products(
        product_name=name,
        produdct_category=category,
        redis=redis,
        page=page,
        per_page=per_page,
    )


@router.get(
    "/me",
    summary="Get all current logged vendor product",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedProductResponse,
)
async def get_all_vendor_products(
    current_store: CurrentStore,
    redis: redisSessionDep,
    name: str | None = Query(default=None, min_length=3, description="name of product"),
    category: str | None = Query(
        default=None, min_length=3, description="Category of product to search for"
    ),
    page: int | None = Query(default=1, gt=0, description="The page number to fetch"),
    per_page: int | None = Query(
        default=10, gt=0, description="The number of products per page to fetch"
    ),
):
    return await product_service.get_products_by_store(
        store_id=str(current_store.id),
        redis=redis,
        name=name,
        category=category,
        page=page,
        per_page=per_page,
    )


@router.get(
    "/store/{id}",
    summary="Get all products of a store",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedProductResponse,
)
async def get_all_vendor_products_by_id(
    id: str,
    redis: redisSessionDep,
    name: str | None = Query(default=None, min_length=3, description="name of product"),
    category: str | None = Query(
        default=None, min_length=3, description="Category of product to search for"
    ),
    page: int | None = Query(default=1, gt=0, description="The page number to fetch"),
    per_page: int | None = Query(
        default=10, gt=0, description="The number of products per page to fetch"
    ),
):
    return await product_service.get_products_by_store(
        store_id=id,
        name=name,
        category=category,
        redis=redis,
        page=page,
        per_page=per_page,
    )


@router.get("/{id}", summary="Get product by ID", response_model=ProductResponse)
async def get_product_by_id(id: str, redis: redisSessionDep):
    return await product_service.get_product_by_id(id, redis=redis)


@router.put(
    "/{id}",
    summary="Update product details (only by owned vendor)",
    status_code=status.HTTP_200_OK,
    response_model=ProductResponse,
)
async def update_product(
    id: str,
    current_store: CurrentStore,
    redis: redisSessionDep,
    images: ImageUpdate = None,
    name: Annotated[str | None, Form(min_length=2, examples=["Round Neck"])] = None,
    description: Annotated[
        str | None, Form(min_length=5, examples=["This is straight from New York"])
    ] = None,
    amount: Annotated[int | None, Form(ge=0, examples=[25000])] = None,
    stock: Annotated[int | None, Form(ge=0, examples=[20])] = None,
    category: Annotated[str | None, Form(examples=["clothes"])] = None,
):
    product_dict = {
        k: v
        for k, v in {
            "name": name,
            "description": description,
            "amount": amount,
            "stock": stock,
            "category": category,
        }.items()
        if v is not None
    }

    return await product_service.update_products(
        update_data=product_dict,
        redis=redis,
        product_id=id,
        store_id=str(current_store.id),
        images=images,
    )


@router.patch(
    "/{id}/toggle-state",
    summary="toggle product state",
    status_code=status.HTTP_200_OK,
    response_model=ProductResponse,
)
async def toggle_product_state(id: str, current_store: CurrentStore):
    return await product_service.toggle_current_store_product_state(
        current_store.id, id
    )


@router.delete(
    "/me",
    summary="Delete all the prouducts of a vendor",
    status_code=status.HTTP_200_OK,
)
async def delete_all_store_products(current_store: CurrentStore):
    return await product_service.delete_all_store_products(str(current_store.id))


@router.delete(
    "/{product_id}",
    summary="Delete a product (Only owned vendor)",
    status_code=status.HTTP_200_OK,
)
async def delete_product(product_id: str, current_store: CurrentStore):
    return await product_service.delete_products_by_id(
        product_id=product_id,
        store_id=str(current_store.id),
    )


@router.delete(
    "/{product_id}/image",
    summary="Delete an image from prudct images (only owned vendor)",
    status_code=status.HTTP_200_OK,
)
async def delete_product_image(
    product_id: str,
    redis: redisSessionDep,
    current_store: CurrentStore,
    image_public_id: str = Query(
        examples=["cd7369f3-5f04-4dd0-a8f4-9b3566867e13/i0hwxwlwbhfofmeumurh"]
    ),
):
    return await product_service.delete_product_image(
        product_id=product_id,
        redis=redis,
        image_public_id=image_public_id,
        store_id=str(current_store.id),
    )
