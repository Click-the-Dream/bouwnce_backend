from app.event_broadcast.models.events import OutingEvent


class CreateEventService:
    @staticmethod
    async def create_event(db, event_data: dict) -> bool:
        return await OutingEvent.create_event(db, event_data)

    @staticmethod
    async def paginate_events(db, page: int, page_size: int) -> list[OutingEvent]:
        return await OutingEvent.paginate_events(db, page, page_size)

    @staticmethod
    async def get_event_by_id(db, event_id: str) -> OutingEvent | None:
        return await OutingEvent.get_event_by_id(db, event_id)
