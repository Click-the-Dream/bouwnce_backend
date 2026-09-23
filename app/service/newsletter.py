from datetime import UTC, datetime
from enum import Enum
from typing import Any

from fastapi import BackgroundTasks, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.newsletter import NewsLetter
from app.models.user import User
from app.models.waitlist import Waitlist
from app.service.q_stash import AvailableJobs, enqueue_job
from app.utils.emails import generate_email_content, send_email
from app.utils.exception import (
    BadRequestException,
    InternalServerErrorException,
    NotFoundException,
)
from app.utils.helper import is_valid_uuid
from app.utils.responses import response_builder


class NewsLetterStatusEnum(Enum):
    CREATED = "created"
    INITIATED = "initiated"
    SENDING = "sending"
    COMPLETED = "completed"


class NewsLetterService:
    @staticmethod
    def _parse_test_recipients(value: str) -> dict[str, str]:
        items: dict[str, str] = {}

        for raw in (value or "").split(","):
            chunk = raw.strip()
            if not chunk:
                continue

            if ":" in chunk:
                email, name = chunk.split(":", 1)
                email = email.strip()
                name = name.strip() or "there"
            else:
                email = chunk
                name = "there"

            if email and email not in items:
                items[email] = name

        return items

    @staticmethod
    def _display_name_for_user(user: User) -> str:
        name = (user.full_name or "").strip()
        if name:
            return name
        username = (user.username or "").strip()
        if username:
            return username
        return "there"

    async def create_newsletter(
        self, newsletter_data: dict[str, Any], db: AsyncSession
    ) -> dict[str, Any]:

        existing_newsletter = await NewsLetter.get_by_name(db, newsletter_data["name"])
        if existing_newsletter:
            raise BadRequestException(
                f"Newsletter with name {newsletter_data['name']} already exists"
            )

        newsletter_data["status"] = NewsLetterStatusEnum.CREATED.value

        newsletter = await NewsLetter.create(newsletter_data, db)

        return response_builder(
            status_code=status.HTTP_201_CREATED,
            message="Newsletter created successfully",
            data=newsletter.to_dict(),
        )

    async def get_newsletter_by_id(
        self, newsletter_id: str, db: AsyncSession
    ) -> dict[str, Any]:
        if not is_valid_uuid(newsletter_id):
            raise BadRequestException("Invalid newsletter Id")

        try:
            newsletter = await NewsLetter.get_by_id(newsletter_id, db)
        except ValueError:
            raise NotFoundException("Newsletter not found") from None

        return response_builder(
            status_code=status.HTTP_200_OK,
            message="Newsletter retrieved successfully",
            data=newsletter.to_dict(),
        )

    async def search_newsletters(
        self,
        db: AsyncSession,
        query: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> dict[str, Any]:
        if query:
            filter = {
                "name": f"%{query}%",
                "description": f"%{query}%",
                "subject": f"%{query}%",
                "content": f"%{query}%",
            }
        else:
            filter = None

        newsletters = await NewsLetter.get_by(
            db=db, filter=filter, page=page, page_size=page_size, order_by="-created_at"
        )

        newsletter_response = [n.to_dict() for n in newsletters["data"]]

        return response_builder(
            status_code=status.HTTP_200_OK,
            message="Newsletters retrieved successfully",
            data={
                "newsletters": newsletter_response,
                "page": page,
                "page_size": page_size,
                "total": newsletters["total"],
            },
        )

    async def initiate_newsletter_broadcast(
        self, newsletter_id: str, db: AsyncSession
    ) -> dict[str, Any]:
        if not is_valid_uuid(newsletter_id):
            raise BadRequestException("Invalid newsletter Id")

        try:
            newsletter = await NewsLetter.get_by_id(newsletter_id, db)

        except ValueError:
            raise NotFoundException("Newsletter not found") from None

        # send to qstash for broadcasting to subscribers
        try:
            enqueue_job(
                {"newsletter_id": str(newsletter.id)},
                type=AvailableJobs.BROADCAST_NEWSLETTER,
            )
        except ValueError:
            raise InternalServerErrorException(
                "Unable to start newsletter broadcast, please try again later"
            ) from None

        newsletter.status = NewsLetterStatusEnum.INITIATED.value
        await newsletter.save(db)

        return response_builder(
            status_code=status.HTTP_200_OK,
            message="Newsletter broadcast initiated successfully",
            data=newsletter.to_dict(),
        )

    async def send_newsletter(
        self,
        *,
        newsletter_id: str,
        db: AsyncSession,
        background_task: BackgroundTasks,
    ) -> dict[str, Any]:
        if not is_valid_uuid(newsletter_id):
            raise BadRequestException("Invalid newsletter Id")

        try:
            newsletter = await NewsLetter.get_by_id(newsletter_id, db)
        except ValueError:
            raise NotFoundException("Newsletter not found") from None

        if settings.NEWSLETTER_USE_TEST_RECIPIENTS:
            recipients = self._parse_test_recipients(
                settings.NEWSLETTER_TEST_RECIPIENTS
            )
            if not recipients:
                raise BadRequestException(
                    "NEWSLETTER_TEST_RECIPIENTS is empty but NEWSLETTER_USE_TEST_RECIPIENTS=true"
                )
        else:
            user_rows = await db.execute(
                select(User.email, User.full_name, User.username).where(
                    User.is_active.is_(True),
                    User.is_deleted.is_(False),
                )
            )
            user_recipients = {}
            for user_ in user_rows.all():
                email = user_.email.strip().lower() if user_.email else None
                full_name = (
                    user_.full_name.strip().split()[0] if user_.full_name else None
                )
                username = user_.username.strip() if user_.username else None
                if email:
                    name = full_name or username or "Dear"
                    user_recipients[email] = name

            waitlist_role = await db.execute(
                select(Waitlist.email, Waitlist.full_name).where(
                    Waitlist.is_active.is_(True),
                    Waitlist.is_deleted.is_(False),
                )
            )
            waitlist_recipients = {}
            for newsletter_ in waitlist_role.all():
                name = (
                    newsletter_.full_name.strip().split()[0]
                    if newsletter_.full_name
                    else "Dear"
                )
                waitlist_recipients = {newsletter_.email.strip().lower(): name}

            # User recipients take precedence if an email exists in both sources.
            recipients = waitlist_recipients | user_recipients

        newsletter.status = NewsLetterStatusEnum.SENDING.value
        await newsletter.save(db)

        for email, name in recipients.items():
            email_content = generate_email_content(
                subject=newsletter.subject,
                template_name="newsletter.html",
                context={
                    "subject": newsletter.subject,
                    "user_name": name,
                    "body": newsletter.content,
                    "year": str(datetime.now(UTC).year),
                },
            )
            background_task.add_task(
                send_email,
                email_to=email,
                subject=email_content.subject,
                html_content=email_content.html_content,
            )

        newsletter.status = NewsLetterStatusEnum.COMPLETED.value
        newsletter.is_sent = True
        newsletter.send_at = datetime.now(UTC)
        await newsletter.save(db)

        return response_builder(
            status_code=status.HTTP_200_OK,
            message="Newsletter queued successfully",
            data={"sent": len(recipients)},
        )

    async def broadcast_newsletter(
        self, newsletter_id: str, db: AsyncSession, background_task: BackgroundTasks
    ):
        return await self.send_newsletter(
            newsletter_id=newsletter_id,
            db=db,
            background_task=background_task,
        )

    async def update_newsletter(
        self, newsletter_id: str, newsletter_data: dict[str, Any], db: AsyncSession
    ):
        if not is_valid_uuid(newsletter_id):
            raise BadRequestException("Invalid newsletter id")

        try:
            newsletter = await NewsLetter.get_by_id(newsletter_id, db)
        except ValueError:
            raise NotFoundException("Newsletter not found") from None

        await newsletter.update(db, newsletter_data)

        return response_builder(
            status_code=status.HTTP_200_OK,
            message="Newsletter updated successfully",
            data=newsletter.to_dict(),
        )

    async def delete_newsletter(self, newsletter_id: str, db: AsyncSession):
        if not is_valid_uuid(newsletter_id):
            raise BadRequestException("Invalid newsletter id")

        try:
            newsletter = await NewsLetter.get_by_id(newsletter_id, db)
        except ValueError:
            raise NotFoundException("Newsletter not found") from None

        await newsletter.delete(db)

        return None


newsletter_service = NewsLetterService()
