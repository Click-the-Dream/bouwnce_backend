from __future__ import annotations

import re
from fastapi import BackgroundTasks
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.matching_ground.core.interest_normalization import normalize_interest_name
from app.matching_ground.model.match import Match, MatchRequest
from app.matching_ground.model.user_block import UserBlock
from app.matching_ground.model.notification import Notification
from app.models.user import User
from app.matching_ground.service.buddy_search import BuddySearchService
from app.utils.exception import ForbiddenException, NotFoundException, BadRequestException
from app.utils.emails import generate_email_content, send_email


@dataclass
class MatchLifecycleService:
    @staticmethod
    def _parse_search_message(message: str) -> tuple[str | None, float]:
  
        text = (message or "").strip()
        if not text:
            return None, 10.0

        radius_km = 10.0
        radius_match = re.search(
            r"(?i)(?:within|radius|around|near|in)\s*(\d+(?:\.\d+)?)\s*km", text
        )
        if radius_match:
            try:
                radius_km = float(radius_match.group(1))
            except ValueError:
                radius_km = 10.0

        interest_hint = normalize_interest_name(text)
        return interest_hint, radius_km

    async def search_candidates_from_message(
        self,
        *,
        session: AsyncSession,
        requester_id: uuid.UUID,
        message: str,
        page: int = 1,
        page_size: int = 10,
    ) -> dict:
        interest_hint, radius_km = self._parse_search_message(message)
        result = await self.suggest_candidates(
            session=session,
            requester_id=requester_id,
            interest_hint=interest_hint,
            radius_km=radius_km,
        )

        items = result.get("items", []) or []
        start = (page - 1) * page_size
        end = start + page_size
        return {
            "status": result.get("status", "ok"),
            "reason": result.get("reason"),
            "page": page,
            "page_size": page_size,
            "total": len(items),
            "items": items[start:end],
            "query": {
                "message": message,
                "radius_km": radius_km,
                "interest_hint": interest_hint,
            },
        }
    
    async def suggest_candidates(
        self, session: AsyncSession, requester_id: uuid.UUID, interest_hint: str | None = None, radius_km: float = 10.0
    ) -> dict:
        buddy_search_service = BuddySearchService()
        result = await buddy_search_service.search(
            session=session,
            requester_id=requester_id,
            radius_km=radius_km,
            interest_hint=interest_hint,
        )
        filtered_matches = []
        for item in result.matches:
            if await UserBlock.is_blocked_between(session, requester_id, uuid.UUID(item.user_id)):
                continue
            filtered_matches.append(item)
        return {
            "status": result.status,
            "reason": result.reason,
            "items": [
                {
                    "user_id": item.user_id,
                    "full_name": item.full_name,
                    "distance_km": item.distance_km,
                    "score": item.score,
                    "shared_interests": item.shared_interests,
                    "shared_traits": item.shared_traits,
                    "score_explanation": (
                        f"distance={item.distance_km}km, "
                        f"shared_interests={len(item.shared_interests)}, "
                        f"shared_traits={len(item.shared_traits)}"
                    ),
                }
                for item in filtered_matches
            ],
        }
    
    async def list_requests_for_user(self, session: AsyncSession, user_id: uuid.UUID) -> dict:
        rows = await MatchRequest.list_for_user(session, user_id)
        return {
            "items": [
                {
                    "request_id": str(row.id),
                    "requester_id": str(row.requester_id),
                    "target_user_id": str(row.target_user_id),
                    "status": row.status,
                    "note": row.note,
                    "created_at": row.created_at.isoformat(),
                    "responded_at": row.responded_at.isoformat() if row.responded_at else None,
                }
                for row in rows
            ]
        }

    async def list_matches_for_user(self, session: AsyncSession, user_id: uuid.UUID) -> dict:
        rows = await Match.list_for_user(session, user_id)
        return {
            "items": [
                {
                    "match_id": str(row.id),
                    "user_id": str(row.user_id),
                    "target_user_id": str(row.target_user_id),
                    "status": row.status,
                    "accepted_at": row.accepted_at.isoformat() if row.accepted_at else None,
                }
                for row in rows
            ]
        }


    async def create_request(
        self,
        session: AsyncSession,
        requester: User,
        target_user_id: uuid.UUID,
        note: str | None,
        background_tasks: BackgroundTasks
    ) -> dict:
        existing = await MatchRequest.find_open_for_pair(session, requester.id, target_user_id)
        if existing is not None:
            return {"status": "already_pending", "request_id": str(existing.id)}
        
        if await UserBlock.is_blocked_between(session, requester.id, target_user_id):
            raise ForbiddenException("You can match with someone who has blocked you")
        
        if requester.id == target_user_id:
            raise BadRequestException("You can't match with yourself")
        
        request = await MatchRequest.create_pending(session, requester.id, target_user_id, note)
        
        target_user = await User.get_by_id(str(target_user_id), session)
        
        email_context = {
            "requester_name": requester.full_name,
            "requester_location": "Lagos",
            "year": datetime.now().year
        }
        email_data = generate_email_content(
            subject="Match Request", 
            template_name="match_request.html", 
            context=email_context
        )
        
        background_tasks.add_task(
            send_email,
            email_to=target_user.email,
            subject=email_data.subject,
            html_content=email_data.html_content
        )
        return {
            "status": "pending",
            "request_id": str(request.id),
            "recipient_email": target_user.email if target_user else None,
        }

    async def respond_request(
        self,
        session: AsyncSession,
        request_id: uuid.UUID,
        responder_user_id: uuid.UUID,
        accepted: bool,
    ) -> dict:
        request = await MatchRequest.get_by_id(str(request_id), session)
        if request is None:
            raise NotFoundException("Match request not found")
        
        if request.target_user_id != responder_user_id:
            raise ForbiddenException("Match Request doesn't belong to user")
        
        if request.status != "pending":
            return {"status": "already_responded"}
        
        if request.expires_at and request.expires_at <= datetime.now(timezone.utc):
            await request.set_status(session, "expired")
            return {"status": "expired"}

        if not accepted:
            await request.set_status(session, "rejected")
            return {"status": "rejected", "request_id": str(request.id)}

        await request.set_status(session, "accepted")
        
        match = await MatchRequest.create_accepted(session, request.requester_id, request.target_user_id)

        notif_data = {
            "user_id": request.requester_id,
            "title": "Match accepted",
            "body": "Your match request has been accepted. Your 3-day chat window is now open.",
            "event_type": "match_accepted"
        }
        await Notification.create(
            data=notif_data,
            db=session,
        )
        return {"status": "accepted", "request_id": str(request.id), "match_id": str(match.id)}


  
