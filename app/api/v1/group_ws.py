"""
Group Chat WebSocket Endpoint
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, WebSocket

from app.service.group_ws_service import handle_group_websocket

# Create router
router = APIRouter(prefix="/groups/ws", tags=["Group WebSocket"])


@router.websocket("/chat")
async def group_chat_websocket(
    websocket: WebSocket,
    token: Annotated[str, Query(description="Authentication token")],
    group_id: Annotated[uuid.UUID, Query(description="Group ID")],
):
    """WebSocket endpoint for group chat."""
    await handle_group_websocket(websocket, token)
