from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SubOrder, WalletTransaction
from app.schemas import (
    OverviewDashboardResponse,
    PaginatedCustomers,
    PaginatedOrders,
    RecentOrder,
    TopProduct,
    VendorCustomerItem,
    VendorCustomersDashboardResponse,
    VendorOrderItem,
    VendorOrdersDashboardResponse,
    WalletDashboardResponse,
    WithdrawalHistory,
)
from app.service.metrics_service import MetricService
from app.utils.helper import build_date_filter
from app.utils.responses import response_builder



class VendorDashBoardService:

    @staticmethod
    async def get_vendor_overview(
        session: AsyncSession,
        store_id: str,
        page: int = 1,
        page_size: int = 5,
        date_range_type: str = "month",
        start_date=None,
        end_date=None,
    ) -> JSONResponse:

        start_date, end_date = build_date_filter(date_range_type, start_date, end_date)

        try:
            pagination = await SubOrder.get_by(
                db=session,
                filter={"store_id": store_id, "status": "delivered"},
                page=page,
                page_size=page_size,
                order_by="created_at",
            )

            orders = pagination.get("data", [])
            total_records = pagination.get("total", 0)
            total_pages = pagination.get("total_pages", 1)

            metrics = await MetricService.compute_overview_metrics(
                db=session,
                store_id=store_id,
                date_range_type=date_range_type,
                start_date=start_date,
                end_date=end_date,
            )

            recent_orders = [
                RecentOrder(
                    order_id=o.order_id,
                    customer_name=o.username,
                    amount=float(o.amount or 0),
                    status=o.status,
                )
                for o in orders
            ]

            top_products = await SubOrder.get_top_products_paginated(
                store_id=store_id,
                page=page,
                page_size=page_size,
                db=session,
            )

            top_products = [TopProduct(**item) for item in top_products["items"]]

            dashboard = OverviewDashboardResponse(
                total_revenue=metrics["total_revenue"],
                total_orders=metrics["total_orders"],
                total_customers=metrics["total_customers"],
                avg_order_value=metrics["aov"],
                revenue_change_percent=metrics["revenue_change_percentage"],
                orders_change_percent=metrics["orders_change_percentage"],
                customers_change_percent=metrics["customers_change_percentage"],
                recent_orders=recent_orders,
                top_products=top_products,
            ).model_dump()

            dashboard["pagination"] = {
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "total_records": total_records,
            }

            return response_builder(
                status="Success",
                message="Dashboard data fetched successfully.",
                data=dashboard,
                status_code=status.HTTP_200_OK,
            )

        except Exception as e:
            return response_builder(
                status="error",
                message=f"Error fetching dashboard data: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @staticmethod
    async def get_dashboard_wallet(
        session: AsyncSession,
        current_user,
        page: int = 1,
        page_size: int = 10,
    ) -> JSONResponse:
        
        
        try:
            wallet = current_user.wallets

            withdrawals_page = await WalletTransaction.get_by(
                db=session,
                filter={"wallet_id": wallet.id, "transaction_type": "withdrawal"},
                order_by="-created_at",
                page=page,
                page_size=page_size,
            )

            items = []
            
            for txn in withdrawals_page.get("data", []):
                items.append(
                    {
                        "id": txn.id,
                        "description": txn.transaction_type,
                        "status": txn.status,
                        "amount": float(-abs(txn.amount or 0)),
                        "date": txn.created_at.strftime("%b %d, %Y, %I:%M%p"),
                    }
                )
            data = WalletDashboardResponse(
                available_balance=float(wallet.available_balance or 0),
                pending_balance=float(wallet.pending_balance or 0),
                withdrawable_balance=float(wallet.withdrawable_balance or 0),
                withdrawal_history=WithdrawalHistory(
                    items=items,
                    page=withdrawals_page.get("page", 1),
                    page_size=withdrawals_page.get("page_size", page_size),
                    total=withdrawals_page.get("total", 0),
                    total_pages=withdrawals_page.get("total_pages", 1),
                ),
            ).model_dump()

            return response_builder(
                status="Success",
                message="Dashboard wallet fetched successfully.",
                data=data,
                status_code=status.HTTP_200_OK,
            )

        except Exception as e:
            return response_builder(
                status="Failed",
                message=f"Error fetching wallet data: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @staticmethod
    async def get_vendor_orders(
        session: AsyncSession,
        store_id: str,
        page: int = 1,
        page_size: int = 10,
        search: str = None,
        order_by: str = "date",
        order_dir: str = "desc",
    ) -> JSONResponse:

        try:
            filters = {"store_id": store_id}

            if search:
                filters["buyer_name__icontains"] = search

            order_map = {
                "name": "buyer_name",
                "date": "created_at",
                "price": "amount",
            }

            field = order_map.get(order_by, "created_at")
            ordering = f"-{field}" if order_dir == "desc" else field

            page_result = await SubOrder.get_by(
                db=session,
                filter=filters,
                order_by=ordering,
                page=page,
                page_size=page_size,
            )

            orders = page_result.get("data", [])

            order_items = [
                VendorOrderItem(
                    id=str(o.id),
                    buyer_name=getattr(o, "username", "Unknown"),
                    date=o.created_at.strftime("%d-%m-%Y") if o.created_at else None,
                    amount=float(o.amount or 0),
                    status=o.status,
                )
                for o in orders
            ]

            data = VendorOrdersDashboardResponse(
                total_orders=page_result.get("total", 0),
                completed_orders=sum(o.status == "completed" for o in orders),
                pending_orders=sum(o.status == "pending" for o in orders),
                processing_orders=sum(o.status == "processing" for o in orders),
                orders=PaginatedOrders(
                    items=order_items,
                    page=page_result.get("page", 1),
                    page_size=page_result.get("page_size", page_size),
                    total=page_result.get("total", 0),
                    total_pages=page_result.get("total_pages", 1),
                ),
            )

            return response_builder(
                status="Success",
                message="Orders fetched successfully",
                data=data,
                status_code=status.HTTP_200_OK,
            )

        except Exception as e:
            return response_builder(
                status="Failed",
                message=f"Error fetching vendor orders {e}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @staticmethod
    async def get_vendor_customers(
        session: AsyncSession,
        store_id: str,
        page: int = 1,
        page_size: int = 10,
    ) -> JSONResponse:
        """
        Fetch vendor customers with pagination using schemas.
        """
        try:

            result = await SubOrder.get_by(
                db=session,
                filter={"store_id": store_id},
                page=page,
                page_size=page_size,
            )

            items = result.get("items", [])
            total_count = result.get("total", len(items))

            customer_model_dump = {}
            for sub in items:
                if sub.username not in customer_model_dump:
                    customer_model_dump[sub.username] = {
                        "name": sub.username,
                        "total_orders": 0,
                        "total_spent": 0.0,
                    }
                customer_model_dump[sub.username]["total_orders"] += 1
                customer_model_dump[sub.username]["total_spent"] += float(
                    sub.amount or 0.0
                )

            customer_items = [
                VendorCustomerItem(**c) for c in customer_model_dump.values()
            ]

            data = VendorCustomersDashboardResponse(
                customers=PaginatedCustomers(
                    items=customer_items,
                    page=page,
                    page_size=page_size,
                    total=total_count,
                    total_pages=(total_count + page_size - 1) // page_size,
                )
            )

            return response_builder(
                status="Success",
                message="Customers fetched successfully",
                status_code=status.HTTP_200_OK,
                data=data.model_dump(),
            )

        except Exception as e:
            return response_builder(
                status="Failed",
                message=f"Error fetching customer data: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
