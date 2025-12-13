from typing import Any

from fastapi import BackgroundTasks, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.waitlist import Waitlist
from app.schemas.waitlist import WaitlistResponse
from app.utils.emails import generate_waitlist_welcome_email, send_email
from app.utils.responses import response_builder


class WaistlistService:
    async def create(
        self, db: AsyncSession, data: dict[str, Any], background_tasks: BackgroundTasks
    ) -> WaitlistResponse:
        # Check if email already exist
        try:
            user = await Waitlist.get_one(db, {"email": data["email"]})
            if user:
                return response_builder(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    status="error",
                    message="User already in waitlist",
                )

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
            waitlistResponse = WaitlistResponse(**user_waitlist.to_dict())
            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Successfully created waitlist",
                data=waitlistResponse,
            )
        except Exception as e:
            print("Error occured while saving waitlist: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Internal server error",
            )

    async def get_waitlist(
        self,
        db: AsyncSession,
        filter: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> list[WaitlistResponse]:

        try:
            waitlists_list = await Waitlist.get_by(
                db, filter, page, page_size, order_by="-created_at"
            )

            waitlistResponse = [
                WaitlistResponse(**waitlist.to_dict())
                for waitlist in waitlists_list["data"]
            ]

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="successfully retrieved waitlist",
                data={
                    "data": waitlistResponse,
                    "page": waitlists_list["page"],
                    "page_size": waitlists_list["page_size"],
                    "total": waitlists_list["total"],
                },
            )
        except Exception as e:
            print("Error occured while fetching waitlist: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Internal server error",
            )

    async def get_today_count(self, db: AsyncSession) -> JSONResponse:

        try:
            today_count = await Waitlist.get_today_count(db)
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="successfully fetched today's count",
                data={"today_count": today_count},
            )
        except Exception as e:
            print("Error occured while fetching today's count: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Internal server error",
            )


waitlist_service = WaistlistService()
