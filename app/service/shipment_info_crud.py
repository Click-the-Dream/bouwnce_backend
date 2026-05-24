from typing import Any

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ShipmentInfo, Store
from app.utils.exception import (
    NotFoundException,
)
from app.utils.responses import response_builder


class ShipmentInfoCRUDService:
    async def create(
        self, db: AsyncSession, data: dict[str, Any], store: Store
    ) -> dict[str, Any]:

        data["store_id"] = store.id
        new_shipment = await ShipmentInfo.create(data, db)
        new_shipment = new_shipment.to_dict()
        new_shipment["user_id"] = str(store.user_id)

        return response_builder(
            status_code=status.HTTP_201_CREATED,
            status="success",
            message="Shipment info created successfully.",
        )

    async def get(self, store: Store) -> dict[str, Any]:

        shipments: list[ShipmentInfo] | None = store.shipment_info
        if not shipments:
            raise NotFoundException(message="Shipment info not found.")

        data = []
        for shipment in shipments:
            shipment = shipment.to_dict()
            shipment["user_id"] = str(store.user_id)
            data.append(shipment)

        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Shipment info retrieved successfully.",
            data=data,
        )

    async def update(
        self, shipment_id: str, db: AsyncSession, data: dict[str, Any], store: Store
    ) -> dict[str, Any]:

        shipments: list[ShipmentInfo] | None = store.shipment_info
        if not shipments:
            raise NotFoundException(message="Shipment info not found.")

        shipment_to_update = None
        for shipment in shipments:
            if str(shipment.id) == shipment_id:
                shipment_to_update = shipment
                break
        else:
            raise NotFoundException(message="shipment not found")

        updated_shipment = await shipment_to_update.update(db, data)
        updated_shipment = updated_shipment.to_dict()
        updated_shipment["user_id"] = str(store.user_id)

        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Shipment info updated successfully.",
            data=updated_shipment,
        )

    async def delete(
        self, shipment_id: str, db: AsyncSession, store: Store
    ) -> dict[str, Any]:

        shipments: ShipmentInfo | None = store.shipment_info
        if not shipments:
            raise NotFoundException(message="Shipment info not found.")

        for shipment in shipments:
            if str(shipment.id) == shipment_id:
                break
        else:
            raise NotFoundException(message="shipment not found")

        await ShipmentInfo.delete_permanently_by_id(id=shipment_id, db=db)
        return response_builder(
            status_code=status.HTTP_204_NO_CONTENT,
            status="success",
            message="Shipment info deleted successfully.",
        )


shipment_info_service = ShipmentInfoCRUDService()
