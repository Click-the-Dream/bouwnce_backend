import smtplib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema
from jinja2 import Template

from app.core.config import settings


@dataclass
class EmailData:
    html_content: str
    subject: str


conf = ConnectionConfig(
    MAIL_USERNAME=settings.SMTP_USER,
    MAIL_PASSWORD=settings.SMTP_PASSWORD,
    MAIL_FROM=settings.EMAILS_FROM_EMAIL,
    MAIL_FROM_NAME=settings.EMAILS_FROM_NAME,
    MAIL_PORT=settings.SMTP_PORT,
    MAIL_SERVER=settings.SMTP_HOST,
    MAIL_SSL_TLS=settings.SMTP_TLS,
    MAIL_STARTTLS=settings.SMTP_SSL,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)


def render_email_templates(*, template_name: str, context: dict[str, Any]) -> str:
    template_str = (
        Path(__file__).parent.parent / "email_templates" / "build" / template_name
    ).read_text()

    html_content = Template(template_str).render(context)
    return html_content


async def send_email(
    *, email_to: str, subject: str = "", html_content: str = ""
) -> bool:

    message = MessageSchema(
        subject=subject, recipients=[email_to], body=html_content, subtype="html"
    )
    fm = FastMail(conf)
    try:
        print("📧sending email to: ", email_to)
        await fm.send_message(message)
        print("✅email sent to: ", email_to)
        return True
    except smtplib.SMTPException as e:
        print("❌email not sent to: ", email_to)
        print("❌error: ", e)
        return False


def generate_test_email(email_to: str) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Test email"
    html_content = render_email_templates(
        template_name="test_email.html",
        context={"project_name": project_name, "email": email_to},
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_login_verification_email(username: str, code: str) -> EmailData:

    project_name = settings.PROJECT_NAME

    subject = f"{project_name} - Verification code"

    html_content = render_email_templates(
        template_name="login_verification_email.html",
        context={
            "user_name": username,
            "verification_code": code,
            "valid_minutes": settings.EMAIL_VERIFICATION_EXPIRE_MINUTES,
            "project_name": settings.PROJECT_NAME,
            "contact_link": f"mailto: {settings.EMAILS_FROM_EMAIL}",
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_new_account_email(email_to: str, username: str) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - New account for user {username}"
    html_content = render_email_templates(
        template_name="new_account.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "username": username,
            "eamil": email_to,
            "link": "#",
        },
    )
    return EmailData(html_content=html_content, subject=subject)
