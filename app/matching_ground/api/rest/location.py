from fastapi import APIRouter, status
from app.api.dependencies import CurrentUser, dbSessionDep
from app.matching_ground.model.user_geolocation import UserGeolocation
from app.matching_ground.schema.location import LocationResponse, LocationUpsertRequest


router = APIRouter(prefix="/location", tags=["User Location"])

@router.put(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Create or update the current user's location",
    response_model=LocationResponse,
)
async def upsert_my_location(
    payload: LocationUpsertRequest,
    session: dbSessionDep,
    current_user: CurrentUser,
):
    row = await UserGeolocation.upsert(
        session=session,
        user_id=current_user.id,
        lat=payload.lat,
        lon=payload.lon,
    )
    return LocationResponse(id=row.id, user_id=row.user_id, lat=row.lat, lon=row.lon)