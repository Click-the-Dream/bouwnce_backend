from typing import Any

from fastapi import BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.waitlist import Waitlist
from app.utils.emails import generate_waitlist_welcome_email, send_email
from app.utils.exception import BadRequestException
from app.utils.responses import response_builder


class WaistlistService:
    async def create(
        self, db: AsyncSession, data: dict[str, Any], background_tasks: BackgroundTasks
    ) -> dict[str, Any]:
        # Check if email already exist

        user = await Waitlist.get_one(db, {"email": data["email"]})
        if user:
            raise BadRequestException(message="User already in waitlist")

        # create waitlist
        user_waitlist = await Waitlist.create(data, db)

        # Send email
        email_data = generate_waitlist_welcome_email(user_waitlist.full_name)
        background_tasks.add_task(
            send_email,
            email_to=user_waitlist.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )

        # return response
        return response_builder(
            status_code=status.HTTP_201_CREATED,
            status="success",
            message="Successfully created waitlist",
            data=user_waitlist.to_dict(),
        )

    async def get_waitlist(
        self,
        db: AsyncSession,
        filter: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> dict[str, Any]:

        waitlists_list = await Waitlist.get_by(
            db, filter, page, page_size, order_by="-created_at"
        )

        waitlistResponse = [waitlist.to_dict() for waitlist in waitlists_list["data"]]

        today_count = await Waitlist.get_today_count(db)

        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="successfully retrieved waitlist",
            data={
                "waitlists": waitlistResponse,
                "today_count": today_count,
                "page": waitlists_list["page"],
                "page_size": waitlists_list["page_size"],
                "total": waitlists_list["total"],
            },
        )

    async def get_today_count(self, db: AsyncSession) -> dict[str, Any]:

        today_count = await Waitlist.get_today_count(db)
        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="successfully fetched today's count",
            data={"today_count": today_count},
        )

    async def get_intitution_count(
        self, db: AsyncSession, page: int = 1, page_size: int = 10
    ) -> dict[str, Any]:

        all_intitution = await Waitlist.group_by_institution(db, page, page_size)

        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="successfully fetched all institution count",
            data=all_intitution,
        )


waitlist_service = WaistlistService()
