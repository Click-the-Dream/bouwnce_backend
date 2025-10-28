from typing import Annotated, Optional, List
from pydantic import BaseModel, EmailStr, Field

class OverviewDashboardResponse(BaseModel):
    total_revenue: Annotated[float, Field(examples=[15000.75])]
    total_orders: Annotated[int, Field(examples=[120])]
    total_customers: Annotated[int, Field(examples=[85])]
    revenue_change_percent: Annotated[float, Field(examples=[12.5])]
    orders_change_percent: Annotated[float, Field(examples=[8.2])]
    customers_change_percent: Annotated[float, Field(examples=[15.3])]
    recent_orders: Annotated[list, Field()]
    top_products: Annotated[list, Field()]

class RecentOrder(BaseModel):
    order_id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    customer_name: Annotated[str, Field(examples=["John Doe"])]
    amount: Annotated[float, Field(examples=[250.50])]
    status: Annotated[str, Field(examples=["delivered"])]

class TopProduct(BaseModel):
    name: Annotated[str, Field(examples=["Product A"])]
    sales: Annotated[int, Field(examples=[44])]
    revenue: Annotated[float, Field(examples=[4400.00])]
    

class WithdrawalItem(BaseModel):

    id: Annotated[int, Field(description="Unique transaction ID")]
    description: Annotated[str, Field(description="Description or label for the withdrawal")]
    status: Annotated[str, Field(description="Transaction status (e.g., completed, pending, failed)")]
    amount: Annotated[float, Field(description="Negative value representing amount withdrawn")]
    date: Annotated[Optional[str], Field(None, description="Formatted date/time of the transaction")]


class WithdrawalHistory(BaseModel):

    items: Annotated[List[WithdrawalItem], Field(description="List of withdrawal transaction records")]
    page: Annotated[int, Field(description="Current page number in pagination")]
    page_size: Annotated[int, Field(description="Number of records returned per page")]
    total: Annotated[int, Field(description="Total number of withdrawal transactions available")]
    total_pages: Annotated[int, Field(description="Total number of pages available")]


class WalletDashboardResponse(BaseModel):

    available_balance: Annotated[float, Field(description="Funds currently available for use")]
    pending_balance: Annotated[float, Field(description="Funds awaiting clearance or processing")]
    withdrawable_balance: Annotated[float, Field(description="Funds that can be withdrawn immediately")]
    withdrawal_history: Annotated[WithdrawalHistory, Field(description="Paginated withdrawal transaction history")]
    
    
from typing import List, Optional
from pydantic import BaseModel, Field
from typing_extensions import Annotated

class VendorOrderItem(BaseModel):
    id: Annotated[str, Field(description="Order ID formatted like ORD-001")]
    buyer_name: Annotated[str, Field(description="Name of the buyer")]
    date: Annotated[Optional[str], Field(None, description="Date of order (dd-mm-yyyy)")]
    amount: Annotated[float, Field(description="Order amount in Naira")]
    status: Annotated[str, Field(description="Current status of the order")]
    status_color: Annotated[str, Field(description="Color code representing the status")]
    currency_symbol: Annotated[str, Field(description="Currency symbol (₦)")]


class PaginatedOrders(BaseModel):
    items: Annotated[List[VendorOrderItem], Field(description="List of paginated orders")]
    page: Annotated[int, Field(description="Current page number")]
    page_size: Annotated[int, Field(description="Number of orders per page")]
    total: Annotated[int, Field(description="Total number of orders available")]
    total_pages: Annotated[int, Field(description="Total number of pages available")]


class VendorOrdersDashboardResponse(BaseModel):
    total_orders: Annotated[int, Field(description="Total vendor orders")]
    completed_orders: Annotated[int, Field(description="Number of completed orders")]
    pending_orders: Annotated[int, Field(description="Number of pending orders")]
    processing_orders: Annotated[int, Field(description="Number of orders being processed")]
    orders: Annotated[PaginatedOrders, Field(description="Paginated order data")]


from typing import List
from pydantic import BaseModel, Field
from typing_extensions import Annotated


class VendorCustomerItem(BaseModel):
    name: Annotated[str, Field(description="Customer's name")]
    email: Annotated[str, Field(description="Customer's email address")]
    total_orders: Annotated[int, Field(description="Total number of orders by this customer")]
    total_spent: Annotated[float, Field(description="Total amount spent by this customer")]


class PaginatedCustomers(BaseModel):
    items: Annotated[List[VendorCustomerItem], Field(description="List of paginated customers")]
    page: Annotated[int, Field(description="Current page number")]
    page_size: Annotated[int, Field(description="Number of records per page")]
    total: Annotated[int, Field(description="Total number of customers")]
    total_pages: Annotated[int, Field(description="Total pages available")]


class VendorCustomersDashboardResponse(BaseModel):
    customers: Annotated[PaginatedCustomers, Field(description="Paginated customer data")]
