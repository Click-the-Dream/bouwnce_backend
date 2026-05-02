from typing import Annotated

from pydantic import BaseModel, Field

from app.models.products import Images
from app.utils.responses import BaseResponse


class ProductResponse(BaseModel):
    id: Annotated[str, Field(examples=["cd7369f3-5f04-4dd0-a8f4-9b3566867e13"])]
    name: Annotated[str, Field(min_length=2, examples=["Round Neck"])]
    description: Annotated[
        str, Field(min_length=5, examples=["This is straight from New York"])
    ]
    amount: Annotated[int, Field(ge=0, examples=[25000])]
    images: list[Images]

class StoreResponse(BaseModel):
    id: Annotated[str, Field(examples=["cd7369f3-5f04-4dd0-a8f4-9b3566867e13"])]
    name: Annotated[str, Field(min_length=2, examples=["My Awesome Store"])]
    store_description: Annotated[str | None, Field(examples=["This is the best Store"])]
    store_logo: Annotated[Images | None, Field(...)]
    store_banner: Annotated[Images | None, Field(...)]
    
class CartCreate(BaseModel):
    product_id: Annotated[str, Field(examples=["cd7369f3-5f04-4dd0-a8f4-9b3566867e13"])]
    quantity: Annotated[int, Field(gt=0, examples=[2])]


class CartResponseSchema(BaseModel):
    id: Annotated[str, Field(examples=["cd7369f3-5f04-4dd0-a8f4-9b3566867e13"])]
    user_id: Annotated[str, Field(examples=["cd7369f3-5f04-4dd0-a8f4-9b3566867e13"])]
    product: Annotated[ProductResponse, Field(description="Product detail response")]
    store: Annotated[StoreResponse | None, Field(description="Store details response")] = None
    quantity: Annotated[int, Field(gt=0, examples=[2])]
    created_at: Annotated[str, Field(examples=["2025-04-03"])]
    updated_at: Annotated[str, Field(examples=["2025-04-03"])]


class CartResponse(BaseResponse):
    data: Annotated[CartResponseSchema, Field(description="Cart response data")]


class ListCartResponse(BaseResponse):
    data: Annotated[list[CartResponseSchema], Field(description="List of carts")]


class PaginatedCartResponseSchema(BaseModel):
    carts: Annotated[list[CartResponseSchema], Field(description="List of carts")]
    total: Annotated[int, Field(examples=[100])]
    page: Annotated[int, Field(examples=[1])]
    page_size: Annotated[int, Field(examples=[10])]


class PaginatedCartResponse(BaseResponse):
    data: Annotated[
        PaginatedCartResponseSchema, Field(description="Paginated carts data")
    ]


class UpdateCart(BaseModel):
    quantity: Annotated[int, Field(examples=[20])]


class ProductCheckoutInfo(BaseModel):
    id: Annotated[str, Field(examples=["cd7369f3-5f04-4dd0-a8f4-9b3566867e13"])]
    store_id: Annotated[str, Field(examples=["cd7369f3-5f04-4dd0-a8f4-9b3566867e13"])]
    name: Annotated[str, Field(examples=["Round Neck"])]
    category: Annotated[str, Field(examples=["Clothing"])]
    images: list[Images]
    stock: Annotated[int, Field(examples=[10])]
    quantity: Annotated[int, Field(examples=[2])]
    amount: Annotated[int, Field(examples=[25000])]
    error: Annotated[str | None, Field(examples=["Insufficient stock"])] = None


class CheckoutResponseSchema(BaseModel):
    payment_url: Annotated[str, Field(examples=["https://paymentgateway.com/pay/xyz"])]
    available_products: Annotated[
        list[ProductCheckoutInfo], Field(description="List of available products")
    ]
    unavailable_products: Annotated[
        list[ProductCheckoutInfo] | None, Field(description="List of unavailable products")
    ] = None


class CheckoutResponse(BaseResponse):
    data: Annotated[CheckoutResponseSchema, Field(description="Checkout response data")]
