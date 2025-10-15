from typing import Any

from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ShipmentInfo, Store
from app.schemas import ShipmentsInfoResponse
from app.utils.responses import response_builder


class ShipmentInfoCRUDService:

    async def create(
        self, db: AsyncSession, data: dict[str, Any], store: Store
    ) -> JSONResponse:

        try:
            shipment: ShipmentInfo | None = store.shipment_info

            if shipment:
                return response_builder(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    status="error",
                    message="Shipment info already exists for this store.",
                )

            data["store_id"] = store.id
            new_shipment = await ShipmentInfo.create(data, db)
            new_shipment = new_shipment.to_dict()
            new_shipment["user_id"] = str(store.user_id)
            data = ShipmentsInfoResponse(**new_shipment)

            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Shipment info created successfully.",
                data=data,
            )
        except Exception as e:
            print("Error occured while creating store shipment info: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while creating shipment info.",
            )

    async def get(self, store: Store) -> JSONResponse:
        try:
            shipment: ShipmentInfo | None = store.shipment_info
            if not shipment:
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    message="Shipment info not found.",
                )

            shipment = shipment.to_dict()
            shipment["user_id"] = str(store.user_id)
            data = ShipmentsInfoResponse(**shipment)
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Shipment info retrieved successfully.",
                data=data,
            )
        except Exception as e:
            print("Error fetching store shipment info: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error fetching store shipment info",
            )

    async def update(
        self, db: AsyncSession, data: dict[str, Any], store: Store
    ) -> JSONResponse:

        try:
            shipment: ShipmentInfo | None = store.shipment_info
            if not shipment:
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    message="Shipment info not found.",
                )

            updated_shipment = await shipment.update(db, data)
            updated_shipment = updated_shipment.to_dict()
            updated_shipment["user_id"] = str(store.user_id)
            data = ShipmentsInfoResponse(**updated_shipment)
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Shipment info updated successfully.",
                data=data,
            )
        except Exception as e:
            print("Error occured while updating store shipment info: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while updating shipment info.",
            )

    async def delete(self, db: AsyncSession, store: Store) -> JSONResponse:
        try:
            shipment: ShipmentInfo | None = store.shipment_info
            if not shipment:
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    message="Shipment info not found.",
                )

            await ShipmentInfo.delete_permanently_by_id(id=shipment.id, db=db)
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Shipment info deleted successfully.",
            )
        except Exception as e:
            print("Error occured while deleting store shipment info: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while deleting shipment info.",
            )


shipment_info_service = ShipmentInfoCRUDService()
