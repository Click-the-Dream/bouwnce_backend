from fastapi import APIRouter, BackgroundTasks, Query, status

from app.api.dependencies import CurrentAdmin, dbSessionDep
from app.schemas.newsletter import (
    NewsLetterCreate,
    NewsLetterResponse,
    NewsLetterSendRequest,
    NewsLetterSendResponse,
    NewsLetterUpdate,
    PaginatedNewsLetterResponse,
)
from app.service.newsletter import newsletter_service

router = APIRouter(prefix="/newsletters", tags=["Newsletters"])


@router.post(
    "/", response_model=NewsLetterResponse, status_code=status.HTTP_201_CREATED
)
async def create_newsletter(
    newsletter_data: NewsLetterCreate, db: dbSessionDep, _: CurrentAdmin
):
    return await newsletter_service.create_newsletter(newsletter_data.model_dump(), db)


@router.get("/{newsletter_id}", response_model=NewsLetterResponse)
async def get_newsletter_by_id(newsletter_id: str, db: dbSessionDep, _: CurrentAdmin):
    return await newsletter_service.get_newsletter_by_id(newsletter_id, db)


@router.put("/{newsletter_id}", response_model=NewsLetterResponse)
async def update_newsletter(
    newsletter_id: str,
    newsletter_data: NewsLetterUpdate,
    db: dbSessionDep,
    _: CurrentAdmin,
):
    return await newsletter_service.update_newsletter(
        newsletter_id, newsletter_data.model_dump(exclude_unset=True), db
    )


@router.get("/", response_model=PaginatedNewsLetterResponse)
async def list_newsletters(
    db: dbSessionDep,
    _: CurrentAdmin,
    page: int = Query(default=1, gt=0, description="The page number to fetch"),
    per_page: int = Query(
        default=10, gt=0, description="The number of newsletters per page to fetch"
    ),
    query: str | None = Query(
        default=None,
        description="Search query to filter newsletters by name, description, subject or content",
    ),
):
    return await newsletter_service.search_newsletters(db, query, page, per_page)


@router.post("/{newsletter_id}/broadcast", status_code=status.HTTP_200_OK)
async def initiate_broadcast(newsletter_id: str, db: dbSessionDep, _: CurrentAdmin):
    return await newsletter_service.initiate_newsletter_broadcast(newsletter_id, db)

@router.post(
    "/{newsletter_id}/send",
    response_model=NewsLetterSendResponse,
    status_code=status.HTTP_200_OK,
)
async def send_newsletter(
    newsletter_id: str,
    payload: NewsLetterSendRequest,
    background_tasks: BackgroundTasks,
    db: dbSessionDep,
    _: CurrentAdmin,
    all_users: bool = Query(
        True, description="If true, send to all active users (ignores emails)"
    ),
):
    return await newsletter_service.send_newsletter(
        newsletter_id=newsletter_id,
        db=db,
        background_task=background_tasks,
        all_users=all_users,
        emails=[str(e) for e in payload.emails],
    )


@router.delete("/{newsletter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_newsletter(newsletter_id: str, db: dbSessionDep, _: CurrentAdmin):
    return await newsletter_service.delete_newsletter(newsletter_id, db)
