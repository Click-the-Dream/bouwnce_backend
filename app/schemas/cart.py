from typing import Annotated

from pydantic import BaseModel, Field

from app.models.products import Images


class ProductResponse(BaseModel):
    id: Annotated[str, Field(examples=["cd7369f3-5f04-4dd0-a8f4-9b3566867e13"])]
    name: Annotated[str, Field(min_length=2, examples=["Round Neck"])]
    description: Annotated[
        str, Field(min_length=5, examples=["This is straight from New York"])
    ]
    amount: Annotated[int, Field(ge=0, examples=[25000])]
    images: list[Images]


class CartCreate(BaseModel):
    product_id: Annotated[str, Field(examples=["cd7369f3-5f04-4dd0-a8f4-9b3566867e13"])]
    quantity: Annotated[int, Field(gt=0, examples=[2])]


class CartResponse(BaseModel):
    id: Annotated[str, Field(examples=["cd7369f3-5f04-4dd0-a8f4-9b3566867e13"])]
    user_id: Annotated[str, Field(examples=["cd7369f3-5f04-4dd0-a8f4-9b3566867e13"])]
    product: ProductResponse
    quantity: Annotated[int, Field(gt=0, examples=[2])]
    created_at: Annotated[str, Field(examples=["2025-04-03"])]
    updated_at: Annotated[str, Field(examples=["2025-04-03"])]


class UpdateCart(BaseModel):
    quantity: Annotated[int, Field(examples=[20])]
