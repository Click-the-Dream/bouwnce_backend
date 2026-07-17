from fastapi import APIRouter

from app.event_broadcast.api.v1 import attendance as event_attendance
from app.event_broadcast.api.v1 import events as event_management

event_router = APIRouter(prefix="/outgoing/events", tags=["User Outgoing Event"])

event_router.include_router(event_attendance.router)
event_router.include_router(event_management.router)
