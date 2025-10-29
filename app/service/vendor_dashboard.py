from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OrderItem, SubOrder, User, Wallet, WalletTransaction
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

router = APIRouter()


class VendorDashBoardService:

    @staticmethod
    async def get_vendor_overview(
        session, store_id: str, page: int = 1, page_size: int = 5
    ) -> JSONResponse:
        """
        Gather summary metrics from SubOrder model.
        Paginate recent orders using SubOrder.paginate().
        """
        try:
            pagination = await SubOrder.get_by(
                db=session,
                filter={"store_id": store_id, "status": "delivered"},
                page=page,
                page_size=page_size,
                order_by="-created_at",
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

            total_revenue = sum(o.amount for o in orders)
            total_orders = total_records
            total_customers = len(set(o.username for o in orders))

            revenue_change_percent = 12.5
            orders_change_percent = 8.2
            customers_change_percent = 15.3

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

            suboder_ids = [o.id for o in orders]
            order_items = await OrderItem.get_by_suborder_ids(
                db=session, suborder_ids=suboder_ids
            )

            product_counts = {}
            for item in order_items:
                if item.product_id not in product_counts:
                    product_counts[item.product_id] = 0

                product_counts[item.product_id] += item.quantity

            product_id_list = product_counts.keys()
            products = await product_domain.get_products_by_ids(product_id_list)

            # to be commented out since its still in wip
            print(products)
            product_sales = {}
            for o in orders:
                product_sales[o.product_name] = (
                    product_sales.get(o.product_name, 0) + o.amount
                )

            top_products = [
                # TopProduct(name=k, sales=44, revenue=v)
                # for k, v in sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:3]
            ]

            # ___ up on to this point ___

            dashboard_data = OverviewDashboardResponse(
                total_revenue=total_revenue,
                total_orders=total_orders,
                total_customers=total_customers,
                revenue_change_percent=revenue_change_percent,
                orders_change_percent=orders_change_percent,
                customers_change_percent=customers_change_percent,
                recent_orders=recent_orders_data,
                top_products=top_products,
            )

            response_content = dashboard_data.dict()
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

            return JSONResponse(
                status_code=status.HTTP_200_OK, content=response_content
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
        """
        Fetch wallet summary + paginated withdrawal history for vendor dashboard.
        """
        try:
            wallet = await Wallet.filter_by(session, user_id=current_user.id)
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
                filter={"wallet_id": wallet.id, "type": "withdrawal"},
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
                        "description": txn.description or "Withdrawal transaction",
                        "status": txn.status,
                        "amount": float(-abs(txn.amount or 0)),
                        "date": (
                            txn.created_at.strftime("%b %d, %Y, %I:%M%p")
                            if txn.created_at
                            else None
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
            ).dict()

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

        # except Exception as e:
        #     return response_builder(
        #         success=False,
        #         message=f"Error fetching dashboard wallet: {str(e)}",
        #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        #     )

        # except Exception as e:
        #     return response_builder(
        #         success=False,
        #         message="Error fetching dashboard data.",
        #         errors=str(e),
        #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        #    )

    # ---- suspend for now ------
    @staticmethod
    async def get_vendor_orders(
        session: AsyncSession,
        current_user,
        page: int = 1,
        page_size: int = 10,
        search: str = None,
        order_by: str = "date",  # name | date | price
        order_dir: str = "desc",  # asc | desc
    ) -> JSONResponse:
        """
        Fetch vendor orders with pagination, search, and sorting.
        Uses model's .paginate() method.
        """

        try:
            filters = {"user_id": current_user.id}

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

            all_orders = await SubOrder.filter_by(user_id=current_user.id, db=session)
            total_orders = len(all_orders)
            completed_orders = sum(o.status == "completed" for o in all_orders)
            pending_orders = sum(o.status == "pending" for o in all_orders)
            processing_orders = sum(o.status == "processing" for o in all_orders)

            order_items = [
                VendorOrderItem(
                    id=f"ORD-{o.id:03}",
                    buyer_name=getattr(o, "buyer_name", "Unknown"),
                    date=o.created_at.strftime("%d-%m-%Y") if o.created_at else None,
                    amount=float(o.amount or 0),
                    status=o.status,
                    status_color=(
                        "green"
                        if o.status == "completed"
                        else "blue" if o.status == "processing" else "orange"
                    ),
                    currency_symbol="₦",
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

    # ----- To this point ------

    @staticmethod
    async def get_vendor_customers(
        session: AsyncSession, current_user, page: int = 1, page_size: int = 10
    ) -> JSONResponse:
        """
        Fetch vendor customers with pagination.
        """
        try:
            orders = await SubOrder.filter_by(user_id=current_user.id, db=session)
            if not orders:
                return response_builder(
                    success=False,
                    message="No orders found",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            # Build unique customer records
            customer_dict = {}
            for o in orders:
                if o.username not in customer_dict:
                    customer_dict[o.username] = {
                        "name": o.username,
                        "email": getattr(o, "buyer_email", "Unknown"),
                        "total_orders": 0,
                        "total_spent": 0.0,
                    }
                customer_dict[o.username]["total_orders"] += 1
                customer_dict[o.username]["total_spent"] += float(o.amount or 0.0)

            customers = list(customer_dict.values())
            total_customers = len(customers)

            # ✅ Manual pagination using your .paginate() pattern
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_items = customers[start_idx:end_idx]
            total_pages = (total_customers + page_size - 1) // page_size

            customer_items = [VendorCustomerItem(**c) for c in paginated_items]

            data = VendorCustomersDashboardResponse(
                customers=PaginatedCustomers(
                    items=customer_items,
                    page=page,
                    page_size=page_size,
                    total=total_customers,
                    total_pages=total_pages,
                )
            )

            return response_builder(
                success=True,
                message="Customers fetched successfully",
                status_code=status.HTTP_200_OK,
                data=data.dict(),
            )

        except Exception as e:
            return response_builder(
                success=False,
                message="Error fetching customer data",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
