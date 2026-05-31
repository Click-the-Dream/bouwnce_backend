import smtplib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import resend
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema
from jinja2 import Template

from app.core.config import settings


@dataclass
class EmailData:
    html_content: str
    subject: str


def _get_valid_mail_from() -> str:
    mail_from = (getattr(settings, "EMAILS_FROM_EMAIL", "") or "").strip()
    if mail_from:
        return mail_from

    for candidate in (
        (getattr(settings, "PROJECT_EMAIL", "") or "").strip(),
        (getattr(settings, "SMTP_USER", "") or "").strip(),
    ):
        if candidate and "@" in candidate:
            return candidate

    raise ValueError(
        "SMTP email is enabled (FASTAPI_ENV=dev) but no valid sender email is configured. "
        "Set `EMAILS_FROM_EMAIL` (recommended) or `PROJECT_EMAIL` in `Backend/.env`."
    )


def _get_smtp_conf() -> ConnectionConfig:
    return ConnectionConfig(
        MAIL_USERNAME=(getattr(settings, "SMTP_USER", "") or "").strip(),
        MAIL_PASSWORD=(getattr(settings, "SMTP_PASSWORD", "") or "").strip(),
        MAIL_FROM=_get_valid_mail_from(),
        MAIL_FROM_NAME=(getattr(settings, "EMAILS_FROM_NAME", "") or "").strip(),
        MAIL_PORT=getattr(settings, "SMTP_PORT", 465),
        MAIL_SERVER=(getattr(settings, "SMTP_HOST", "") or "").strip(),
        # FastAPI-Mail expects SSL/TLS and STARTTLS booleans
        MAIL_SSL_TLS=getattr(settings, "SMTP_SSL", False),
        MAIL_STARTTLS=getattr(settings, "SMTP_TLS", True),
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
    )


# Setting up email service depending on the environment
if settings.FASTAPI_ENV == "staging":
    resend.api_key = settings.RESEND_API_KEY


def render_email_templates(*, template_name: str, context: dict[str, Any]) -> str:
    templates_dir = Path(__file__).parent.parent / "email_templates"
    build_path = templates_dir / "build" / template_name
    src_path = templates_dir / "src" / template_name

    if build_path.exists():
        template_str = build_path.read_text()
    elif src_path.exists():
        template_str = src_path.read_text()
    else:
        raise FileNotFoundError(
            f"Email template not found in build/ or src/: {template_name}"
        )

    html_content = Template(template_str).render(context)
    return html_content


async def send_email_using_resend(
    *, email_to: str, subject: str = "", html_content: str = ""
) -> bool:

    params: resend.Emails.SendParams = {
        "from": f"{settings.PROJECT_NAME} <{settings.RESEND_EMAIL}>",
        "to": email_to,
        "subject": subject,
        "html": html_content,
    }

    try:
        print("📧sending email to: ", email_to)
        email = resend.Emails.send(params)
        print("✅email sent to: ", email_to)
        print(email)
        return True
    except Exception as e:
        print("❌email not sent to: ", email_to)
        print("❌error: ", e)
        return False


async def send_email_using_smtp(
    *, email_to: str, subject: str = "", html_content: str = ""
) -> bool:

    message = MessageSchema(
        subject=subject, recipients=[email_to], body=html_content, subtype="html"
    )
    try:
        conf = _get_smtp_conf()
    except Exception as e:
        print("❌SMTP is not configured; email not sent.")
        print("❌error: ", e)
        return False

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


# Dynamically send email using different service depending on the environment
async def send_email(
    *, email_to: str, subject: str = "", html_content: str = ""
) -> bool:

    if settings.FASTAPI_ENV == "staging":
        return await send_email_using_resend(
            email_to=email_to, subject=subject, html_content=html_content
        )
    elif settings.FASTAPI_ENV == "dev":
        return await send_email_using_smtp(
            email_to=email_to, subject=subject, html_content=html_content
        )
    else:
        print("No email service configured for production yet.")
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
            "contact_link": f"mailto: {settings.PROJECT_EMAIL}",
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_waitlist_welcome_email(full_name: str):
    project_name = settings.PROJECT_NAME

    subject = f"{project_name} - Welcome"

    html_content = render_email_templates(
        template_name="waitlist_welcome.html",
        context={
            "user_name": full_name,
            "project_name": project_name,
            "contact_link": settings.PROJECT_EMAIL,
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


def generate_email_content(subject: str, template_name: str, context: dict[str, str]):
    project_name = settings.PROJECT_NAME

    context["project_name"] = project_name
    html_content = render_email_templates(template_name=template_name, context=context)

    return EmailData(html_content=html_content, subject=subject)
