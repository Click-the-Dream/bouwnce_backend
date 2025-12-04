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
            shipments: ShipmentInfo | None = store.shipment_info
            if not shipments:
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    message="Shipment info not found.",
                )
            data = []
            for shipment in shipments:
                shipment = shipment.to_dict()
                shipment["user_id"] = str(store.user_id)
                data.append(ShipmentsInfoResponse(**shipment))

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
        self, shipment_id: str, db: AsyncSession, data: dict[str, Any], store: Store
    ) -> JSONResponse:

        try:
            shipments: ShipmentInfo | None = store.shipment_info
            if not shipments:
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    message="Shipment info not found.",
                )
            shipment_to_update = None
            for shipment in shipments:
                if str(shipment.id) == shipment_id:
                    shipment_to_update = shipment
                    break
            else:
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    message="shipment not found",
                )

            updated_shipment = await shipment_to_update.update(db, data)
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

    async def delete(
        self, shipment_id: str, db: AsyncSession, store: Store
    ) -> JSONResponse:
        try:
            shipments: ShipmentInfo | None = store.shipment_info
            if not shipments:
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    message="Shipment info not found.",
                )

            for shipment in shipments:
                if str(shipment.id) == shipment_id:
                    break
            else:
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    message="shipment not found",
                )

            await ShipmentInfo.delete_permanently_by_id(id=shipment_id, db=db)
            return response_builder(
                status_code=status.HTTP_204_NO_CONTENT,
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
