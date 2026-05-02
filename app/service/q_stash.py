from qstash import QStash
from enum import Enum

from app.core.config import settings


class AvailableJobs(Enum):
    BROADCAST_NEWSLETTER = "broadcast-newsletter"

qstash = QStash(token=settings.QSTASH_TOKEN)

def enqueue_job(payload: dict, type: AvailableJobs):
    
    url = f"{settings.BASE_URL}/api/v1/jobs/execute"
    
    if type == AvailableJobs.BROADCAST_NEWSLETTER:
        url = f"{url}/broadcast-newsletter"
    else:
        raise ValueError("Invalid job Type")
    
    res = qstash.message.publish_json(
        url=url,
        body=payload,
        retries=3,
        delay=0
    )
    print(res)
    
