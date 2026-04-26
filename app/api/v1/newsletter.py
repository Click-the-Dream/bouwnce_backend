from fastapi import APIRouter, BackgroundTasks, status, Query
from typing import Annotated

from app.service.newsletter import newsletter_service
from app.schemas.newsletter import (
    NewsLetterCreate,
    NewsLetterUpdate,
    NewsLetterResponse,
    PaginatedNewsLetterResponse
)
from app.api.dependencies import CurrentAdmin, dbSessionDep


router = APIRouter(prefix="/newsletters", tags=["Newsletters"])


@router.post("/", response_model=NewsLetterResponse, status_code=status.HTTP_201_CREATED)
async def create_newsletter(
    newsletter_data: NewsLetterCreate,
    db: dbSessionDep,
    _: CurrentAdmin
):
    return await newsletter_service.create_newsletter(newsletter_data.model_dump(), db)

@router.get("/{newsletter_id}", response_model=NewsLetterResponse)
async def get_newsletter_by_id(
    newsletter_id: str,
    db: dbSessionDep,
    _: CurrentAdmin
):
    return await newsletter_service.get_newsletter_by_id(newsletter_id, db)

@router.put("/{newsletter_id}", response_model=NewsLetterResponse)
async def update_newsletter(
    newsletter_id: str,
    newsletter_data: NewsLetterUpdate,
    db: dbSessionDep,
    _: CurrentAdmin
):
    return await newsletter_service.update_newsletter(newsletter_id, newsletter_data.model_dump(exclude_unset=True), db)

@router.get("/", response_model=PaginatedNewsLetterResponse)
async def list_newsletters(
    db: dbSessionDep,
    _: CurrentAdmin,
    page: int = Query(default=1, gt=0, description="The page number to fetch"),
    per_page: int  = Query(
        default=10, gt=0, description="The number of newsletters per page to fetch"
    ),
    query: str | None = Query(default=None, description="Search query to filter newsletters by name, description, subject or content")
):
    return await newsletter_service.search_newsletters(db, query, page, per_page)

@router.post("/{newletter_id}/broadcast", status_code=status.HTTP_200_OK)
async def initiate_broadcast(
    newsletter_id: str,
    db: dbSessionDep,
    _: CurrentAdmin
):
    return await newsletter_service.initiate_newsletter_broadcast(newsletter_id, db)


@router.delete("/{newsletter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_newsletter(
    newsletter_id: str,
    db: dbSessionDep,
    _: CurrentAdmin
):
    return await newsletter_service.delete_newsletter(newsletter_id, db)


@router.post("/{newsletter_id}/job/execute/broadcasting", status_code=status.HTTP_200_OK)
async def broadcast_newsletter(
    newsletter_id: str,
    db: dbSessionDep,
    background_task: BackgroundTasks
):
    return await newsletter_service.broadcast_newsletter(newsletter_id, db, background_task)