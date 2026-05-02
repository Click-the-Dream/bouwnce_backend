from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any
from enum import Enum
from fastapi import BackgroundTasks
from datetime import datetime, timezone

from app.models.newsletter import NewsLetter
from app.models.waitlist import Waitlist
from app.schemas.newsletter import (
    NewsLetterCreate,
    NewsLetterUpdate,
)
from app.utils.exception import (
    BadRequestException,
    NotFoundException,
    InternalServerErrorException
)
from app.service.q_stash import enqueue_job, AvailableJobs
from app.utils.responses import response_builder
from app.utils.helper import is_valid_uuid
from app.utils.emails import generate_email_content, send_email
from app.core.config import settings


class NewsLetterStatusEnum(Enum):
    CREATED = "created"
    INITIATED = "initiated"
    SENDING = "sending"
    COMPLETED = "completed"

class NewsLetterService:
    
    async def create_newsletter(
        self, newsletter_data: dict[str, Any], db: AsyncSession
    ) -> dict[str, Any]:
        
        existing_newsletter = await NewsLetter.get_by_name(db, newsletter_data["name"])
        if existing_newsletter:
            raise BadRequestException(f"Newsletter with name {newsletter_data['name']} already exists")
        
        
        newsletter_data["status"] = NewsLetterStatusEnum.CREATED.value
        
        newsletter = await NewsLetter.create(newsletter_data, db)
        
        return response_builder(
            status_code=status.HTTP_201_CREATED,
            message="Newsletter created successfully",
            data=newsletter.to_dict()
        )
        
    async def get_newsletter_by_id(self, newsletter_id: str, db: AsyncSession) -> dict[str, Any]:
        if not is_valid_uuid(newsletter_id):
            raise BadRequestException("Invalid newsletter Id")
        
        try:
            newsletter = await NewsLetter.get_by_id(newsletter_id, db)
        except ValueError as e:
            raise NotFoundException("Newsletter not found") from None
        
        return response_builder(
            status_code=status.HTTP_200_OK,
            message="Newsletter retrieved successfully",
            data=newsletter.to_dict()
        )
        
    async def search_newsletters(
        self, 
        db: AsyncSession, 
        query: str | None = None, 
        page: int = 1, 
        page_size: int  = 10
    ) -> dict[str, Any]:
        if query:
            filter = {
                "name": f"%{query}%",
                "description": f"%{query}%",
                "subject": f"%{query}%",
                "content": f"%{query}%"
            }
        else:
            filter = None
        
        newsletters = await NewsLetter.get_by(
            db=db, 
            filter=filter, 
            page=page, 
            page_size=page_size, 
            order_by="-created_at"
        )
        
        
        newsletter_response = [n.to_dict() for n in newsletters["data"]]
        
        return response_builder(
            status_code=status.HTTP_200_OK,
            message="Newsletters retrieved successfully",
            data={
                "newsletters": newsletter_response,
                "page": page,
                "page_size": page_size,
                "total": newsletters["total"]
            }
        )
        
    async def initiate_newsletter_broadcast(self, newsletter_id: str, db: AsyncSession)  -> dict[str, Any]:
        if not is_valid_uuid(newsletter_id):
            raise BadRequestException("Invalid newsletter Id")
        
        try:
            newsletter = await NewsLetter.get_by_id(newsletter_id, db)
            
        except ValueError as e:
            raise NotFoundException("Newsletter not found") from None
        
        # send to qstash for broadcasting to subscribers
        try:
            enqueue_job({"newsletter_id": str(newsletter.id)}, type=AvailableJobs.BROADCAST_NEWSLETTER)
        except ValueError:
            raise InternalServerErrorException("Unable to start newsletter broadcast, please try again later")
        
        newsletter.status = NewsLetterStatusEnum.INITIATED.value
        await newsletter.save(db)
        
        return response_builder(
            status_code=status.HTTP_200_OK,
            message="Newsletter broadcast initiated successfully",
            data=newsletter.to_dict()
        )
        
        
    async def broadcast_newsletter(self, newsletter_id: str, db: AsyncSession, background_task: BackgroundTasks):
        if not is_valid_uuid(newsletter_id):
            raise BadRequestException("Invalid newsletter Id")
        
        try:
            newsletter = await NewsLetter.get_by_id(newsletter_id, db)
        except ValueError as e:
            raise NotFoundException("Newsletter not found") from None
        
        # users_in_waitlist = await Waitlist.get_by(db, all=True)
        # user_emails_and_name = [(user.email, user.name) for user in users_in_waitlist["data"]]
        
        user_emails_and_name = [
            ("znwajei@gmail.com", "Zion"),
            ("theregalelegida@gmail.com", "Elegida"),
            ("techforme247@gmail.com", "Khalid"),
            ("ogunyemivictor738@gmail.com", "Victor"),
            ("codenuel2000@gmail.com", "CodeNuel"),
            ("ajayihabeeb977@gmail.com", "Habeeb"),
            ("ajadii228@gmail.com", "Ajadi"),
            ("afolabimubarak18@gmail.com", "Mubarak"),
            ("bariudebayo@gmail.com", "Bariu")
        ]
        
        newsletter.status = NewsLetterStatusEnum.SENDING.value
        await newsletter.save(db)
        
        for email, name in user_emails_and_name:
            email_content = generate_email_content(
                subject=newsletter.subject,
                template_name="newsletter.html",
                context={
                        "subject": newsletter.subject,
                        "user_name": name,
                        "body": newsletter.content,
                        "year": datetime.now(timezone.utc).year,
                    }
                )
            background_task.add_task(
                send_email,
                email_to=email,
                subject=email_content.subject,
                html_content=email_content.html_content
            )
            
        newsletter.status = NewsLetterStatusEnum.COMPLETED.value
        newsletter.is_sent = True
        newsletter.send_at = datetime.now(timezone.utc)
        await newsletter.save(db)
        
        return response_builder(
            status_code=status.HTTP_200_OK,
            message="Newsletter broadcasted successfully",
            data=newsletter.to_dict()
        )
        
        
    async def update_newsletter(self, newsletter_id: str, newsletter_data: dict[str, Any], db: AsyncSession):
        if not is_valid_uuid(newsletter_id):
            raise BadRequestException("Invalid newsletter id")
        
        try:
            newsletter = await NewsLetter.get_by_id(newsletter_id, db)
        except ValueError as e:
            raise NotFoundException("Newsletter not found") from None
        
        await newsletter.update(db, newsletter_data)
        
        return response_builder(
            status_code=status.HTTP_200_OK,
            message="Newsletter updated successfully",
            data=newsletter.to_dict()
        )
        
        
    async def delete_newsletter(self, newsletter_id: str, db: AsyncSession):
        if not is_valid_uuid(newsletter_id):
            raise BadRequestException("Invalid newsletter id")
        
        try:
            newsletter = await NewsLetter.get_by_id(newsletter_id, db)
        except ValueError as e:
            raise NotFoundException("Newsletter not found") from None
        
        await newsletter.delete(db)
        
        return None
        
        
newsletter_service = NewsLetterService()
