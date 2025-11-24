from fastapi import APIRouter, BackgroundTasks, Query, status

from app.api.dependencies import dbSessionDep
from app.schemas.waitlist import WaitlistCreate, WaitlistResponse
from app.service.waitlist import waitlist_service

router = APIRouter(prefix="/waitlist", tags=["Waitlist"])


@router.post(
    "/",
    summary="Add a user to the waitlist",
    response_model=WaitlistResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create(
    db: dbSessionDep, waitlist_schema: WaitlistCreate, background_tasks: BackgroundTasks
):
    return await waitlist_service.create(
        db, waitlist_schema.model_dump(), background_tasks
    )


@router.get(
    "/",
    summary="Get all the waitlist",
    response_model=list[WaitlistResponse],
    status_code=status.HTTP_200_OK,
)
async def get_all(
    db: dbSessionDep,
    name: str | None = Query(default=None, description="Search with name"),
    institution: str | None = Query(
        default=None, description="Search with institution"
    ),
    page: int | None = Query(default=1, gt=0, description="The page number to fetch"),
    page_size: int | None = Query(
        default=10, gt=0, description="Number of resource per page"
    ),
):
    filter = {}
    if name:
        filter["full_name"] = name

    if institution:
        filter["institution"] = institution

    return await waitlist_service.get_waitlist(db, filter, page, page_size)
