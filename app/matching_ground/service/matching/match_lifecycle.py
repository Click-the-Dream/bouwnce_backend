from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.matching_ground.core.interest_normalization import normalize_interest_name
from app.matching_ground.model.interest import Interest
from app.matching_ground.model.match import Match, MatchRequest
from app.matching_ground.model.notification import Notification
from app.matching_ground.model.user_block import UserBlock
from app.matching_ground.model.user_interest import UserInterest
from app.matching_ground.service.buddy_search import BuddySearchService
from app.models.chat import Conversation
from app.models.user import User
from app.utils.emails import generate_email_content, send_email
from app.utils.exception import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)


class MatchLifecycleService:
    @staticmethod
    def _parse_radius_km(message: str) -> float | None:

        text = (message or "").strip()
        if not text:
            return None

        radius_km: float | None = None
        radius_match = re.search(
            r"(?i)(?:within|radius|around|near|in)\s*(\d+(?:\.\d+)?)\s*km", text
        )
        if radius_match:
            try:
                radius_km = float(radius_match.group(1))
            except ValueError:
                radius_km = None

        return radius_km

    @staticmethod
    async def _extract_interest_hints(
        session: AsyncSession, message: str, *, max_hints: int = 5
    ) -> set[str]:
        """
        Extract interests from a natural language message by matching against
        known interests in the database (no AI models).

        Returns normalized interest names.
        """
        text = (message or "").strip()
        if not text:
            return set()

        normalized_message = normalize_interest_name(text)
        # Fetch only names (keep it cheap)
        rows = await session.execute(select(Interest.name))
        known_names = [r[0] for r in rows.all() if r and r[0]]

        hits: list[str] = []
        for name in known_names:
            n = normalize_interest_name(name)
            if not n:
                continue
            if n in normalized_message:
                hits.append(n)
                if len(hits) >= max_hints:
                    break

        return set(hits)

    @staticmethod
    def _normalize_search_text(message: str) -> str:
        return normalize_interest_name(message or "")

    async def _extract_user_hints(
        self,
        session: AsyncSession,
        message: str,
        *,
        max_users: int = 5,
    ) -> set[uuid.UUID]:
        text = self._normalize_search_text(message)
        if not text:
            return set()

        rows = await session.execute(
            select(User.id, User.username, User.full_name).where(
                User.is_active.is_(True), User.is_deleted.is_(False)
            )
        )
        hits: set[uuid.UUID] = set()
        for user_id, username, full_name in rows.all():
            candidates = [
                normalize_interest_name(username or ""),
                normalize_interest_name(full_name or ""),
            ]
            if any(candidate and candidate in text for candidate in candidates):
                hits.add(user_id)
                if len(hits) >= max_users:
                    break
        return hits

    async def _build_suggested_queries(
        self, session: AsyncSession, requester_id: uuid.UUID, *, limit: int = 5
    ) -> list[str]:
        rows = await session.execute(
            select(Interest.name)
            .join(UserInterest, UserInterest.interest_id == Interest.id)
            .where(UserInterest.user_id == requester_id)
            .order_by(Interest.name.asc())
        )
        interests = [name for (name,) in rows.all() if name]
        suggestions: list[str] = []
        for name in interests[:limit]:
            suggestions.append(f"people who like {name}")
        if not suggestions:
            suggestions = [
                "people near me",
                "people who like reading",
                "people who like podcast",
                "people who like volunteering",
            ][:limit]
        return suggestions

    async def search_candidates_from_message(
        self,
        *,
        session: AsyncSession,
        requester_id: uuid.UUID,
        message: str | None,
        page: int = 1,
        page_size: int = 10,
    ) -> dict:
        message_text = (message or "").strip()
        radius_km = self._parse_radius_km(message_text)
        interest_hints = await self._extract_interest_hints(session, message_text)
        target_user_ids = await self._extract_user_hints(session, message_text)
        result = await self.suggest_candidates(
            session=session,
            requester_id=requester_id,
            interest_hints=interest_hints,
            target_user_ids=target_user_ids,
            radius_km=radius_km,
        )

        items = result.get("items", []) or []
        if not message_text:
            suggested_queries = await self._build_suggested_queries(
                session, requester_id
            )
        else:
            suggested_queries = []

        if not items:
            fallback_result = await self.suggest_candidates(
                session=session,
                requester_id=requester_id,
                interest_hints=set(),
                target_user_ids=None,
                radius_km=radius_km,
            )
            fallback_items = fallback_result.get("items", []) or []
            if fallback_items:
                result = fallback_result
                items = fallback_items

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
                "message": message_text,
                "radius_km": radius_km,
                "interest_hints": sorted(interest_hints),
                "target_user_ids": sorted(str(uid) for uid in target_user_ids),
            },
            "suggested_queries": suggested_queries,
        }

    async def suggest_candidates(
        self,
        session: AsyncSession,
        requester_id: uuid.UUID,
        interest_hints: set[str] | None = None,
        target_user_ids: set[uuid.UUID] | None = None,
        radius_km: float | None = 10.0,
    ) -> dict:
        buddy_search_service = BuddySearchService()
        result = await buddy_search_service.search(
            session=session,
            requester_id=requester_id,
            radius_km=radius_km,
            interest_hints=interest_hints,
            target_user_ids=target_user_ids,
        )
        filtered_matches = []
        for item in result.matches:
            if str(item.user_id) == str(requester_id):
                continue
            if await UserBlock.is_blocked_between(
                session, requester_id, uuid.UUID(item.user_id)
            ):
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
                    "profile_pic": item.profile_pic,
                    "score": item.score,
                    "shared_interests": item.shared_interests,
                    "score_explanation": (
                        f"distance={item.distance_km}km, "
                        f"shared_interests={len(item.shared_interests)}, "
                        "shared_traits=0"
                    ),
                }
                for item in filtered_matches
            ],
        }

    async def list_requests_for_user(
        self, session: AsyncSession, user_id: uuid.UUID, page: int, page_size: int
    ) -> dict:
        rows = await MatchRequest.list_for_user(session, user_id, page, page_size)
        return {
            "items": [
                {
                    "request_id": str(row.id),
                    "requester": row.requester.to_dict() if row.requester else None,
                    "target_user": (
                        row.target_user.to_dict() if row.target_user else None
                    ),
                    "status": row.status,
                    "note": row.note,
                    "created_at": row.created_at.isoformat(),
                    "responded_at": (
                        row.responded_at.isoformat() if row.responded_at else None
                    ),
                }
                for row in rows
            ],
            "page": page,
            "page_size": page_size,
            "total": len(rows),
        }

    async def list_user_sent_requests(
        self, session: AsyncSession, user_id: uuid.UUID, page: int, page_size: int
    ) -> dict:
        rows = await MatchRequest.list_sent_by_user(session, user_id, page, page_size)
        return {
            "items": [
                {
                    "request_id": str(row.id),
                    "requester": row.requester.to_dict() if row.requester else None,
                    "target_user": (
                        row.target_user.to_dict() if row.target_user else None
                    ),
                    "status": row.status,
                    "note": row.note,
                    "created_at": row.created_at.isoformat(),
                    "responded_at": (
                        row.responded_at.isoformat() if row.responded_at else None
                    ),
                }
                for row in rows
            ],
            "page": page,
            "page_size": page_size,
            "total": len(rows),
        }

    async def list_matches_for_user(
        self, session: AsyncSession, user_id: uuid.UUID, page: int, page_size: int
    ) -> dict:
        rows = await Match.list_for_user(session, user_id, page, page_size)
        return {
            "items": [
                {
                    "match_id": str(row.id),
                    "user": row.user.to_dict() if row.user else None,
                    "target_user": (
                        row.target_user.to_dict() if row.target_user else None
                    ),
                    "status": row.status,
                    "accepted_at": (
                        row.accepted_at.isoformat() if row.accepted_at else None
                    ),
                }
                for row in rows
            ],
            "page": page,
            "page_size": page_size,
            "total": len(rows),
        }

    async def create_request(
        self,
        session: AsyncSession,
        requester: User,
        target_user_id: uuid.UUID,
        note: str | None,
        background_tasks: BackgroundTasks,
    ) -> dict:
        existing = await MatchRequest.find_open_for_pair(
            session, requester.id, target_user_id
        )
        if existing is not None:
            return {"status": "already_pending", "request_id": str(existing.id)}

        if await UserBlock.is_blocked_between(session, requester.id, target_user_id):
            raise ForbiddenException("You can match with someone who has blocked you")

        if requester.id == target_user_id:
            raise BadRequestException("You can't match with yourself")

        request = await MatchRequest.create_pending(
            session, requester.id, target_user_id, note
        )

        target_user = await User.get_by_id(str(target_user_id), session)
        requester_display = requester.username or requester.full_name or "someone"

        await Notification.create(
            data={
                "user_id": target_user_id,
                "title": f"New match request · {requester_display}",
                "body": f"{requester_display} sent you a match request.",
                "event_type": "match_request",
                "payload": {
                    "route": "match.request",
                    "request_id": str(request.id),
                    "from_user": {
                        "id": str(requester.id),
                        "username": requester.username,
                        "full_name": requester.full_name,
                        "profile_pic": requester.profile_pic,
                    },
                },
            },
            db=session,
        )

        email_context = {
            "requester_name": requester.full_name,
            "requester_location": "Lagos",
            "year": datetime.now().year,
        }
        email_data = generate_email_content(
            subject="Match Request",
            template_name="match_request.html",
            context=email_context,
        )

        background_tasks.add_task(
            send_email,
            email_to=target_user.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
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

        if request.expires_at and request.expires_at <= datetime.now(UTC):
            await request.set_status(session, "expired")
            return {"status": "expired"}

        if not accepted:
            await request.set_status(session, "rejected")
            responder_user = await User.get_by_id(str(request.target_user_id), session)
            responder_display = (
                responder_user.username or responder_user.full_name or "your match"
            )
            await Notification.create(
                data={
                    "user_id": request.requester_id,
                    "title": f"Match request declined · {responder_display}",
                    "body": f"{responder_display} declined your match request.",
                    "event_type": "match_rejected",
                    "payload": {
                        "route": "match.requests",
                        "request_id": str(request.id),
                        "other_user": {
                            "id": str(responder_user.id),
                            "username": responder_user.username,
                            "full_name": responder_user.full_name,
                            "profile_pic": responder_user.profile_pic,
                        },
                    },
                },
                db=session,
            )
            return {"status": "rejected", "request_id": str(request.id)}

        await request.set_status(session, "accepted")

        match = await Match.create_accepted(
            session, request.requester_id, request.target_user_id
        )
        conversation = await Conversation.get_or_create_between(
            session, request.requester_id, request.target_user_id
        )

        other_user = await User.get_by_id(str(request.target_user_id), session)
        other_display = other_user.username or other_user.full_name or "your match"

        notif_data = {
            "user_id": request.requester_id,
            "title": f"Match accepted · {other_display}",
            "body": f"You matched with {other_display}. Your 3-day chat window is now open.",
            "event_type": "match_accepted",
            "payload": {
                "route": "chat.conversation",
                "conversation_id": str(conversation.id),
                "match_id": str(match.id),
                "request_id": str(request.id),
                "unread_messages_count": 0,
                "other_user": {
                    "id": str(other_user.id),
                    "username": other_user.username,
                    "full_name": other_user.full_name,
                    "profile_pic": other_user.profile_pic,
                },
            },
        }
        await Notification.create(
            data=notif_data,
            db=session,
        )
        return {
            "status": "accepted",
            "request_id": str(request.id),
            "match_id": str(match.id),
            "conversation_id": str(conversation.id),
        }
