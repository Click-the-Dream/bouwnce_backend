from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.matching_ground.core.interest_normalization import normalize_interest_name
from app.matching_ground.core.location import Coordinates
from app.matching_ground.model.interest import Interest
from app.matching_ground.model.match import Match, MatchRequest
from app.matching_ground.model.user_geolocation import UserGeolocation
from app.matching_ground.model.user_interest import UserInterest
from app.matching_ground.schema.buddy_search import BuddyMatch, BuddySearchResult
from app.models.user import User


class BuddySearchService:
    def __init__(self) -> None:
        self.geolocation_model = UserGeolocation
        self.interest_model = UserInterest
        self.user_model = User

    async def search(
        self,
        session: AsyncSession,
        requester_id: uuid.UUID,
        radius_km: float | None = 10.0,
        interest_hints: set[str] | None = None,
        target_user_ids: set[uuid.UUID] | None = None,
        limit: int = 10,
    ) -> BuddySearchResult:
        requester_geo = await self.geolocation_model.get_by_user_id(
            session, requester_id
        )
        center = (
            Coordinates(lat=requester_geo.lat, lon=requester_geo.lon)
            if requester_geo is not None
            else None
        )

        requester_interest_rows = await session.execute(
            select(UserInterest.interest_id).where(UserInterest.user_id == requester_id)
        )
        requester_interest_ids = set(requester_interest_rows.scalars().all())

        hints_norm = {
            normalize_interest_name(h) for h in (interest_hints or set()) if h
        }
        hints_norm.discard("")

        hint_interest_ids: set[uuid.UUID] = set()
        if hints_norm:
            interest_rows = await session.execute(select(Interest.id, Interest.name))
            for interest_id, name in interest_rows.all():
                if normalize_interest_name(name) in hints_norm:
                    hint_interest_ids.add(interest_id)

        query_interest_ids = requester_interest_ids | hint_interest_ids
        query_interest_count = len(query_interest_ids)
        hint_interest_count = len(hint_interest_ids)

        excluded_user_ids: set[uuid.UUID] = set()
        active_match_rows = await session.execute(
            select(Match.user_id, Match.target_user_id).where(
                Match.status == "active",
                (
                    (Match.user_id == requester_id)
                    | (Match.target_user_id == requester_id)
                ),
            )
        )
        for user_id, target_user_id in active_match_rows.all():
            excluded_user_ids.add(
                target_user_id if user_id == requester_id else user_id
            )

        outgoing_request_rows = await session.execute(
            select(MatchRequest.target_user_id).where(
                MatchRequest.requester_id == requester_id,
                MatchRequest.status.in_(("pending", "accepted")),
            )
        )
        excluded_user_ids.update(outgoing_request_rows.scalars().all())

        targeted_user_ids = {
            uuid.UUID(str(uid)) for uid in (target_user_ids or set()) if uid
        }

        candidate_geo = self.geolocation_model
        distance_expr = None
        if radius_km is not None and center is not None:
            req_lat = float(center.lat)
            req_lon = float(center.lon)
            lat1 = func.radians(req_lat)
            lon1 = func.radians(req_lon)
            lat2 = func.radians(candidate_geo.lat)
            lon2 = func.radians(candidate_geo.lon)
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = func.pow(func.sin(dlat / 2.0), 2) + func.cos(lat1) * func.cos(
                lat2
            ) * func.pow(func.sin(dlon / 2.0), 2)
            c = 2.0 * func.asin(func.sqrt(a))
            distance_expr = 6371.0 * c

        shared_query_expr = (
            func.count(
                func.distinct(
                    case(
                        (
                            UserInterest.interest_id.in_(list(query_interest_ids)),
                            UserInterest.interest_id,
                        ),
                        else_=None,
                    )
                )
            ).label("shared_interest_count")
            if query_interest_ids
            else sa.literal(0).label("shared_interest_count")
        )
        shared_hint_expr = (
            func.count(
                func.distinct(
                    case(
                        (
                            UserInterest.interest_id.in_(list(hint_interest_ids)),
                            UserInterest.interest_id,
                        ),
                        else_=None,
                    )
                )
            ).label("shared_hint_count")
            if hint_interest_ids
            else sa.literal(0).label("shared_hint_count")
        )
        interest_stats_sq = (
            select(
                UserInterest.user_id.label("user_id"),
                func.count(func.distinct(UserInterest.interest_id)).label(
                    "cand_interest_count"
                ),
                shared_query_expr,
                shared_hint_expr,
            )
            .group_by(UserInterest.user_id)
            .subquery("interest_stats")
        )

        cand_interest_count = func.coalesce(interest_stats_sq.c.cand_interest_count, 0)
        shared_interest_count = func.coalesce(
            interest_stats_sq.c.shared_interest_count, 0
        )
        shared_hint_count = func.coalesce(interest_stats_sq.c.shared_hint_count, 0)

        union_count = (
            cand_interest_count + query_interest_count
        ) - shared_interest_count
        interest_value = case(
            (
                union_count > 0,
                sa.cast(shared_interest_count, sa.Float)
                / sa.cast(union_count, sa.Float),
            ),
            else_=0.0,
        )

        prompt_value = case(
            (
                hint_interest_count > 0,
                sa.cast(shared_hint_count, sa.Float)
                / sa.cast(hint_interest_count, sa.Float),
            ),
            else_=0.0,
        )

        score_expr = prompt_value if hint_interest_ids else interest_value
        if distance_expr is not None:
            location_value = func.greatest(
                0.0, 1.0 - (distance_expr / float(radius_km))
            )
            score_expr = (score_expr + location_value) / 2.0

        base_query = (
            select(
                self.user_model.id.label("user_id"),
                self.user_model.full_name,
                self.user_model.profile_pic,
                self.user_model.bio,
                (distance_expr if distance_expr is not None else sa.null()).label(
                    "distance_km"
                ),
                score_expr.label("score"),
            )
            .outerjoin(candidate_geo, candidate_geo.user_id == self.user_model.id)
            .outerjoin(
                interest_stats_sq, interest_stats_sq.c.user_id == self.user_model.id
            )
            .where(
                self.user_model.id != requester_id, self.user_model.is_active.is_(True)
            )
            .order_by(
                (
                    sa.case(
                        (self.user_model.id.in_(list(targeted_user_ids)), 1),
                        else_=0,
                    ).desc()
                    if targeted_user_ids
                    else self.user_model.created_at.desc()
                ),
                score_expr.desc(),
                interest_value.desc(),
                self.user_model.created_at.desc(),
            )
        )
        if targeted_user_ids:
            base_query = base_query.where(
                self.user_model.id.in_(list(targeted_user_ids))
            )
        if excluded_user_ids:
            base_query = base_query.where(self.user_model.id.not_in(excluded_user_ids))

        if distance_expr is not None:
            base_query = base_query.where(
                candidate_geo.lat.is_not(None),
                candidate_geo.lon.is_not(None),
                distance_expr <= float(radius_km),
            )

        strict_query = base_query
        if hint_interest_ids:
            strict_query = strict_query.where(shared_hint_count > 0)

        used_reason = None
        rows = list((await session.execute(strict_query.limit(limit))).all())
        if hint_interest_ids and not rows:
            used_reason = "relaxed_interest_filter"
            rows = list((await session.execute(base_query.limit(limit))).all())

        user_ids = [r.user_id for r in rows]
        shared_by_user: dict[str, list[tuple[bool, str]]] = {}
        if user_ids and query_interest_ids:
            shared_rows = await session.execute(
                select(UserInterest.user_id, UserInterest.interest_id, Interest.name)
                .join(Interest, Interest.id == UserInterest.interest_id)
                .where(
                    UserInterest.user_id.in_(user_ids),
                    UserInterest.interest_id.in_(list(query_interest_ids)),
                )
            )
            for uid, interest_id, name in shared_rows.all():
                is_prompt = bool(hint_interest_ids and interest_id in hint_interest_ids)
                shared_by_user.setdefault(str(uid), []).append((is_prompt, name))

        all_by_user: dict[str, list[str]] = {}
        if user_ids:
            all_rows = await session.execute(
                select(UserInterest.user_id, Interest.name)
                .join(Interest, Interest.id == UserInterest.interest_id)
                .where(UserInterest.user_id.in_(user_ids))
            )
            for uid, name in all_rows.all():
                all_by_user.setdefault(str(uid), []).append(name)

        matches: list[BuddyMatch] = []
        for r in rows:
            dist = r.distance_km
            distance_val = round(float(dist), 2) if dist is not None else -1.0
            matches.append(
                BuddyMatch(
                    user_id=str(r.user_id),
                    full_name=r.full_name,
                    distance_km=distance_val,
                    profile_pic=r.profile_pic,
                    bio=r.bio,
                    score=round(float(r.score or 0.0), 4),
                    shared_interests=[
                        name
                        for _, name in sorted(
                            shared_by_user.get(str(r.user_id), []),
                            key=lambda x: (not x[0], x[1].lower()),
                        )
                    ],
                    candidate_interests=sorted(
                        set(all_by_user.get(str(r.user_id), [])), key=str.lower
                    ),
                )
            )

        return BuddySearchResult(
            status="ok", matches=matches[:limit], reason=used_reason
        )
