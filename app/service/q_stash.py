from enum import Enum

from qstash import QStash, Receiver

from app.core.config import settings
from app.utils.exception import UnAuthorizedException


class AvailableJobs(Enum):
    BROADCAST_NEWSLETTER = "broadcast-newsletter"


qstash = QStash(token=settings.QSTASH_TOKEN)


def verify_qstash_request(*, signature: str | None, body: str) -> None:
    if not signature:
        raise UnAuthorizedException("Missing QStash signature")
    try:
        Receiver(
            current_signing_key=settings.QSTASH_CURRENT_SIGNING_KEY,
            next_signing_key=settings.QSTASH_NEXT_SIGNING_KEY,
        ).verify(signature=signature, body=body)
    except Exception as exc:
        raise UnAuthorizedException("Invalid QStash signature") from exc


def enqueue_job(payload: dict, type: AvailableJobs):

    url = f"{settings.BASE_URL}/api/v1/jobs/execute"

    if type == AvailableJobs.BROADCAST_NEWSLETTER:
        url = f"{url}/broadcast-newsletter"
    else:
        raise ValueError("Invalid job Type")

    res = qstash.message.publish_json(url=url, body=payload, retries=3, delay=0)
    print(res)
