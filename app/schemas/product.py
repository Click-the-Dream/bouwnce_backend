from typing import Annotated

from fastapi import Form
from pydantic import BaseModel, Field

from app.models.products import Images
from app.utils.responses import BaseResponse


class ProductBase(BaseModel):
    name: Annotated[str, Field(min_length=2, examples=["Round Neck"])]
    description: Annotated[
        str, Field(min_length=5, examples=["This is straight from New York"])
    ]
    amount: Annotated[int, Field(ge=0, examples=[25000])]
    stock: Annotated[int, Field(ge=0, examples=[20])]
    category: Annotated[str, Field(examples=["clothes"])]


class ProductResponseSchema(ProductBase):
    id: Annotated[str, Field(examples=["cd7369f3-5f04-4dd0-a8f4-9b3566867e13"])]
    store_id: Annotated[str, Field(examples=["cd7369f3-5f04-4dd0-a8f4-9b3566867e13"])]
    state: Annotated[str, Field(examples=["draft"])]
    images: list[Images]
    created_at: Annotated[str, Field(examples=["2025-04-03"])]
    updated_at: Annotated[str, Field(examples=["2025-04-03"])]


class ProductResponse(BaseResponse):
    data: Annotated[
        ProductResponseSchema | None, Field(description="Product response data")
    ] = None


class PaginatedProductResponseSchema(BaseModel):
    products: Annotated[
        list[ProductResponseSchema], Field(description="List of products data")
    ]
    page: Annotated[int, Field(examples=[1])]
    total: Annotated[int, Field(examples=[100])]
    page_size: Annotated[int, Field(examples=[10])]


class PaginatedProductResponse(BaseResponse):
    data: Annotated[
        PaginatedProductResponseSchema, Field(description="Paginated Product data")
    ]


class ProductUpdate(BaseModel):
    name: Annotated[str | None, Form(min_length=2, examples=["Baggy Jeans"])] = None
    description: Annotated[
        str | None, Form(min_length=5, examples=["This is Original"])
    ] = None
    amount: Annotated[int | None, Form(ge=0, examples=[30000])] = None
    stock: Annotated[int, Form(ge=0, examples=[10])] = None
    category: Annotated[str | None, Form(examples=["clothes"])] = None


class CategoryCreate(BaseModel):
    name: Annotated[str, Field(examples=["shoes"])]
    description: Annotated[
        str | None, Field(examples=["The description of the category"])
    ]


class CategoryResponseSchema(BaseModel):
    id: Annotated[str, Field(examples=["cd7369f3-5f04-4dd0-a8f4-9b3566867e13"])]
    name: Annotated[str, Field(examples=["clothes"])]
    description: Annotated[str | None, Field(examples=["This is a clothe category"])]


class CategoryResponse(BaseResponse):
    data: Annotated[CategoryResponseSchema, Field(description="Category response data")]


class CategoryListResponse(BaseResponse):
    data: Annotated[
        list[CategoryResponseSchema], Field(description="Category list response data")
    ]
