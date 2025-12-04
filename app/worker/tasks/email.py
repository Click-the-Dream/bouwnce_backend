import asyncio

from app.core.config import settings
from app.utils.emails import generate_email_content, send_email
from app.worker.celery_app import celery_app


@celery_app.task(name="app.worker.tasks.email.send_email_using_worker")
def send_email_using_worker(
    email_to: str, subject: str, context: dict[str, str], template_name: str
):

    subject = f"{settings.PROJECT_NAME} - {subject}"
    email_data = generate_email_content(subject, template_name, context)
    asyncio.run(
        send_email(
            email_to=email_to, subject=subject, html_content=email_data.html_content
        )
    )
