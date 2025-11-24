from fastapi import APIRouter, Query, status
from fastapi import APIRouter, Query, status
from fastapi.responses import JSONResponse

from app.api.dependencies import CurrentStore, dbSessionDep

from app.api.dependencies import CurrentStore, dbSessionDep
from app.schemas import (
    OverviewDashboardResponse,
    VendorCustomersDashboardResponse,
    VendorCustomersDashboardResponse,
    VendorOrdersDashboardResponse,
    WalletDashboardResponse,
    WalletDashboardResponse,
)
from app.service import VendorDashBoardService

router = APIRouter(tags=["Dashboard Information"])


@router.get(
    "/overview",
    status_code=status.HTTP_200_OK,
    "/overview",
    status_code=status.HTTP_200_OK,
    summary="Get vendor dashboard overview",
    response_model=OverviewDashboardResponse,
    response_model=OverviewDashboardResponse,
)
async def get_vendor_dashboard_overview(
    session: dbSessionDep,
    current_user: CurrentStore,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    date_range: str = Query(None, description="Date range for the overview"),
    start_date: str = Query(None, description="Start date for the overview"),
    end_date: str = Query(None, description="End date for the overview"),
) -> JSONResponse:
    return await VendorDashBoardService.get_vendor_overview(
        session=session, store_id=current_user.id, page=page, page_size=page_size, date_range_type=date_range, start_date=start_date, end_date=end_date
    )




@router.get(
    "/wallet",
    status_code=status.HTTP_200_OK,
    "/wallet",
    status_code=status.HTTP_200_OK,
    summary="Get wallet summary and withdrawal history",
    response_model=WalletDashboardResponse,
    response_model=WalletDashboardResponse,
)
async def get_wallet_dashboard(
    session: dbSessionDep,
    current_user: CurrentStore,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    page_size: int = Query(10, ge=1, le=100),
) -> JSONResponse:
    return await VendorDashBoardService.get_dashboard_wallet(
        session=session, current_user=current_user, page=page, page_size=page_size
        session=session, current_user=current_user, page=page, page_size=page_size
    )



@router.get(
    "/orders",
    response_model=VendorOrdersDashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch vendor orders with pagination, filtering, and sorting.",
    summary="Fetch vendor orders with pagination, filtering, and sorting.",
)
async def fetch_vendor_orders(
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
    order_by: str = Query(
        "date", regex="^(name|date|price)$", description="Sort field"
    ),
    order_dir: str = Query(
        "desc", regex="^(asc|desc)$", description="Sort direction (asc/desc)"
    ),
) -> JSONResponse:
    return await VendorDashBoardService.get_vendor_orders(
        session=session,
        current_user=current_user,
        page=page,
        page_size=page_size,
        search=search,
        order_by=order_by,
        order_dir=order_dir,
        order_dir=order_dir,
    )




@router.get(
    "/dashboard",
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
    page_size: int = Query(
        10, ge=1, le=100, description="Number of customers per page"
    ),
):
    return await VendorDashBoardService.get_vendor_customers(
        session, current_user, page, page_size
    )

    return await VendorDashBoardService.get_vendor_customers(
        session, current_user, page, page_size
    )
