from typing import Annotated

from pydantic import BaseModel, Field


class CheckoutInputSchema(BaseModel):
    store_id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    shipment_id: Annotated[
        str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])
    ]
