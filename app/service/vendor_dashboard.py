from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import SubOrder, User, Wallet, WalletTransaction, StoreMetrics
from app.models.products import product_domain
from app.schemas import (
    OverviewDashboardResponse,
    PaginatedCustomers,
    PaginatedOrders,
    RecentOrder,
    VendorCustomerItem,
    VendorCustomersDashboardResponse,
    VendorOrderItem,
    VendorOrdersDashboardResponse,
    WalletDashboardResponse,
    WithdrawalHistory,
)
from app.utils.responses import response_builder
from app.utils.helper import build_date_filter
from app.service.metrics_service import MetricService

router = APIRouter()


class VendorDashBoardService:
    
    @staticmethod
    def _pct_change(old_value: float, new_value: float) -> float:
        if old_value in (None, 0):
            return 0.0 if (new_value in (None, 0)) else 100.0
        return round(((new_value - old_value) / old_value) * 100.0, 1)
    

    @staticmethod
    async def get_vendor_overview(
        session, store_id: str, page: int = 1, page_size: int = 5, date_range_type: str = "month", start_date=None, end_date=None
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

            orders = pagination["items"]
            total_records = pagination["total"]
            total_pages = pagination["pages"]

            if not orders:
                return response_builder(
                    success=False,
                    message="No orders found",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            
            
            metrics = await MetricService.compute_overview_metrics(
                db=session,
                store_id=store_id,
                date_range_type=date_range_type,
                start_date=start_date,
                end_date=end_date,
            )

            recent_orders_data = (
                [
                    RecentOrder(
                        order_id=o.order_id,
                        customer_name=o.username,
                        amount=o.amount,
                        status=o.status,
                    )
                    for o in orders
                ],
            )
            
            top_products = await SubOrder.get_top_products_paginated(
                store_id=store_id, page=page, page_size=page_size, db=session
            )

            dashboard_data = OverviewDashboardResponse(
                total_revenue=metrics["total_revenue"],
                total_orders=metrics["total_orders"],
                total_customers=metrics["total_customers"],
                avg_order_value=metrics["aov"],
                revenue_change_percent=metrics["revenue_change_percentage"],
                orders_change_percent=metrics["orders_change_percentage"],
                customers_change_percent=metrics["customers_change_percentage"],
                recent_orders=recent_orders_data,
                top_products=top_products,
            )

            response_content = dashboard_data.model_dump()
            response_content.update(
                {
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total_pages": total_pages,
                        "total_records": total_records,
                    }
                }
            )
            return response_builder(
                success=True,
                message="Dashboard data fetched successfully.",
                data=response_content,
                status_code=status.HTTP_200_OK,
            )

        except Exception as e:
            return response_builder(
                success=False,
                message=f"Error fetching dashboard data: {str(e)}",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @staticmethod
    async def get_dashboard_wallet(
        session, current_user: User, page: int = 1, page_size: int = 10
    ) -> JSONResponse:

        try:
            wallet = await Wallet.filter_by(session, store_id=current_user.store_id)
            if not wallet:
                return response_builder(
                    success=False,
                    message="Wallet not found.",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            wallet = wallet[0] if isinstance(wallet, list) else wallet

            # 🔹 Paginated withdrawal history
            withdrawals_page = await WalletTransaction.get_by(
                db=session,
                filter={"wallet_id": wallet.id, "transaction_type": "withdrawal"},
                order_by="-created_at",
                page=page,
                page_size=page_size,
            )

            # 🔹 Format paginated data
            history = []
            for txn in withdrawals_page.items:
                history.append(
                    {
                        "id": txn.id,
                        "description": txn.transaction_type or "Withdrawal transaction",
                        "status": txn.status,
                        "amount": float(-abs(txn.amount or 0)),
                        "date": (
                            txn.created_at.strftime("%b %d, %Y, %I:%M%p")
                        ),
                    }
                )

            data = WalletDashboardResponse(
                available_balance=float(wallet.available_balance or 0),
                pending_balance=float(wallet.pending_balance or 0),
                withdrawable_balance=float(wallet.withdrawable_balance or 0),
                withdrawal_history=WithdrawalHistory(
                    items=history,
                    page=withdrawals_page.page,
                    page_size=withdrawals_page.page_size,
                    total=withdrawals_page.total,
                    total_pages=withdrawals_page.total_pages,
                ),
            ).model_dump()
            return response_builder(
                success=True,
                message="Dashboard wallet fetched successfully.",
                data=data,
                status_code=status.HTTP_200_OK,
            )

        except Exception as e:
            return response_builder(
                success=False,
                message=f"Error fetching wallet data: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @staticmethod
    async def get_vendor_orders(
        session: AsyncSession,
        current_user,
        page: int = 1,
        page_size: int = 10,
        search: str = None,
        order_by: str = "date",
        order_dir: str = "desc",
    ) -> JSONResponse:
        """
        Fetch vendor orders with pagination, search, and sorting.
        Uses model's .paginate() method.
        """

        try:
            filters = {
                "store_id": current_user.store_id
            }  # Should be pointing to store and not user

            if search:
                filters["buyer_name__icontains"] = search

            order_field_map = {
                "name": "buyer_name",
                "date": "created_at",
                "price": "amount",
            }

            order_field = order_field_map.get(order_by, "created_at")
            order_by_param = f"-{order_field}" if order_dir == "desc" else order_field

            orders_page = await SubOrder.get_by(
                db=session,
                filter=filters,
                order_by=order_by_param,
                page=page,
                page_size=page_size,
            )

            if not orders_page.items:
                return response_builder(
                    success=False,
                    message="No orders found",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            all_orders = await SubOrder.filter_by(store_id=current_user.store_id, db=session)
            total_orders = len(all_orders)
            completed_orders = sum(o.status == "completed" for o in all_orders)
            pending_orders = sum(o.status == "pending" for o in all_orders)
            processing_orders = sum(o.status == "processing" for o in all_orders)

            order_items = [
                VendorOrderItem(
                    id=f"ORD-{o.id:03}",
                    buyer_name=getattr(o, "username", "Unknown"),
                    date=o.created_at.strftime("%d-%m-%Y") if o.created_at else None,
                    amount=float(o.amount or 0),
                    status=o.status,
                )
                for o in orders_page.items
            ]

            data = VendorOrdersDashboardResponse(
                total_orders=total_orders,
                completed_orders=completed_orders,
                pending_orders=pending_orders,
                processing_orders=processing_orders,
                orders=PaginatedOrders(
                    items=order_items,
                    page=orders_page.page,
                    page_size=orders_page.page_size,
                    total=orders_page.total,
                    total_pages=orders_page.total_pages,
                ),
            )
            return response_builder(
                success=True,
                message="Orders fetched successfully",
                status_code=status.HTTP_200_OK,
                data=data,
            )

        except Exception as e:
            return response_builder(
                success=False,
                message="Error fetching vendor orders",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @staticmethod
    async def get_vendor_customers(
        session: AsyncSession, current_user, page: int = 1, page_size: int = 10
    ) -> JSONResponse:
        """
        Fetch vendor customers with pagination.
        """
        try:
            result = await SubOrder.get_by(db=session, filter={"store_id": current_user.store_id}, page=page, page_size=page_size)

            suborders = result["data"]

            if not suborders:
                return response_builder(
                    success=False,
                    message="No suborders found",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            customer_model_dump = {}
            for o in suborders:
                if o.username not in customer_model_dump:
                    customer_model_dump[o.username] = {
                        "name": o.username,
                        "total_orders": 0,
                        "total_spent": 0.0,
                    }
                customer_model_dump[o.username]["total_orders"] += 1
                customer_model_dump[o.username]["total_spent"] += float(o.amount or 0.0)

            customer_items = [VendorCustomerItem(**c) for c in customer_model_dump.values()]

            data = VendorCustomersDashboardResponse(
                customers=PaginatedCustomers(
                    items=customer_items,
                    page=page,
                    page_size=page_size,
                    total=suborders["total"],
                    total_pages=(suborders["total"] + page_size - 1) // page_size,
                )
            )

            return response_builder(
                success=True,
                message="Customers fetched successfully",
                status_code=status.HTTP_200_OK,
                data=data.model_dump(),
            )

        except Exception as e:
            return response_builder(
                success=False,
                message="Error fetching customer data",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
