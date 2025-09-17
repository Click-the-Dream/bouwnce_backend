from dataclasses import dataclass
from pathlib import Path
from typing import Any

import emails
from jinja2 import Template

from app.core.config import settings
from app.core.logging import logger


@dataclass
class EmailData:
    html_content: str
    subject: str


def render_email_templates(*, template_name: str, context: dict[str, Any]) -> str:
    template_str = (
        Path(__file__).parent / "email_templates" / "build" / template_name
    ).read_text()

    html_content = Template(template_str).render(context)
    return html_content


def send_email(*, email_to: str, subject: str = "", html_content: str = "") -> bool:

    message = emails.Message(
        subject=subject,
        html=html_content,
        mail_from=(settings.EMAILS_FROM_NAME, settings.EMAILS_FROM_EMAIL),
    )

    smtp_options = {
        "host": settings.SMTP_HOST,
        "port": settings.SMTP_PORT,
        "user": settings.SMTP_USER,
        "password": settings.SMTP_PASSWORD,
    }
    if settings.SMTP_TLS:
        smtp_options["tls"] = True
    elif settings.SMTP_SSL:
        smtp_options["ssl"] = True

    try:
        message.send(to=email_to, smtp=smtp_options)
        return True
    except Exception as e:
        logger.error("Failed sending email: ", e)
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
        template_name="login_verification_email",
        context={
            "user_name": username,
            "verification_code": code,
            "valid_minutes": settings.EmAIL_VERIFICATION_EXPIRE_MINUTES,
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
