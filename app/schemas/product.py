from typing import Annotated

from fastapi import Form
from pydantic import BaseModel, Field

from app.models.products import Images


class ProductBase(BaseModel):
    name: Annotated[str, Field(min_length=2, examples=["Round Neck"])]
    description: Annotated[
        str, Field(min_length=5, examples=["This is straight from New York"])
    ]
    amount: Annotated[int, Field(ge=0, examples=[25000])]
    stock: Annotated[int, Field(ge=0, examples=[20])]
    category: Annotated[str, Field(examples=["clothes"])]


class ProductResponse(ProductBase):
    id: Annotated[str, Field(examples=["cd7369f3-5f04-4dd0-a8f4-9b3566867e13"])]
    vendor_id: Annotated[str, Field(examples=["cd7369f3-5f04-4dd0-a8f4-9b3566867e13"])]
    status: Annotated[str, Field(examples=["draft"])]
    images: list[Images]
    created_at: Annotated[str, Field(examples=["2025-04-03"])]
    updated_at: Annotated[str, Field(examples=["2025-04-03"])]


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


class CategoryResponse(BaseModel):
    id: Annotated[str, Field(examples=["cd7369f3-5f04-4dd0-a8f4-9b3566867e13"])]
    name: Annotated[str, Field(examples=["clothes"])]
    description: Annotated[str | None, Field(examples=["This is a clothe category"])]
