from fastapi import APIRouter, Query, status
from fastapi.responses import JSONResponse

from app.api.dependencies import CurrentStore, dbSessionDep
from app.schemas import (
    OverviewDashboardResponse,
    VendorCustomersDashboardResponse,
    VendorOrdersDashboardResponse,
    WalletDashboardResponse,
)
from app.service import VendorDashBoardService

router = APIRouter(tags=["Dashboard Information"], prefix="/dashboard")


@router.get(
    "/overview",
    status_code=status.HTTP_200_OK,
    summary="Get vendor dashboard overview if date range is not provided, the current month will be used",
    response_model=OverviewDashboardResponse,
)
async def get_vendor_dashboard_overview(
    session: dbSessionDep,
    current_store: CurrentStore,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    date_range: str = Query(
        "this_month",
        description="Date range for the overview",
        regex="^(today|yesterday|last_7_days|last_30_days|this_month|custom)$",
    ),
    start_date: str = Query(
        None, description="Start date for the overview", example="2023-01-01"
    ),
    end_date: str = Query(
        None, description="End date for the overview", example="2023-01-31"
    ),
):

    if date_range == "custom":
        if not start_date or not end_date:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "start_date and end_date are required for custom date range"
                },
            )

    return await VendorDashBoardService.get_vendor_overview(
        session=session,
        store_id=current_store.id,
        page=page,
        page_size=page_size,
        date_range_type=date_range,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/wallet",
    status_code=status.HTTP_200_OK,
    summary="Get wallet summary and withdrawal history",
    response_model=WalletDashboardResponse,
)
async def get_wallet_dashboard(
    session: dbSessionDep,
    current_store: CurrentStore,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    return await VendorDashBoardService.get_dashboard_wallet(
        session=session, current_store=current_store, page=page, page_size=page_size
    )


@router.get(
    "/orders",
    response_model=VendorOrdersDashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch vendor orders with pagination, filtering, and sorting.",
)
async def vendor_orders_dashboard(
    session: dbSessionDep,
    current_user: CurrentStore,
    page: int = Query(1, ge=1, description="Page number for pagination"),
    page_size: int = Query(10, ge=1, le=100, description="Number of orders per page"),
    search: str = Query(None, description="Search orders by buyer name"),
    order_by: str = Query(
        "date", regex="^(name|date|price)$", description="Sort field"
    ),
    order_dir: str = Query(
        "desc", regex="^(asc|desc)$", description="Sort direction (asc/desc)"
    ),
):
    return await VendorDashBoardService.get_vendor_orders(
        session=session,
        store_id=current_user.id,
        page=page,
        page_size=page_size,
        search=search,
        order_by=order_by,
        order_dir=order_dir,
    )


@router.get(
    "/customers",
    response_model=VendorCustomersDashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch paginated list of vendor customers",
)
async def vendor_customers_dashboard(
    session: dbSessionDep,
    current_user: CurrentStore,
    page: int = Query(1, ge=1, description="Page number for pagination"),
    page_size: int = Query(
        10, ge=1, le=100, description="Number of customers per page"
    ),
):
    return await VendorDashBoardService.get_vendor_customers(
        session=session, store_id=current_user.id, page=page, page_size=page_size
    )
