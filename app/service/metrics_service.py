from app.models import SubOrder, StoreMetrics, Store
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.utils.helper import build_date_filter
from typing import Tuple, Dict, Any

class MetricService:
    
    @staticmethod
    async def update_metrics(db: AsyncSession, store_id: str):

        data = await SubOrder.get_store_metrics(db, store_id)

        data['aov'] = (data['total_revenue'] / data['total_orders']) if data['total_orders'] > 0 and data['total_revenue']  > 0 else 0.0
        

        store_metrics = StoreMetrics.filter_by(store_id=store_id, db=db)
        if store_metrics is None:
            store_metrics = StoreMetrics()
        
            for key, value in data.items():
                if hasattr(store_metrics, key):
                    setattr(store_metrics, key, value)

            store_metrics.create(db)
            
        else:
            store_metrics = store_metrics[0] if store_metrics else None

            
            for key, value in data.items():
                if hasattr(store_metrics, key):
                    setattr(store_metrics, key, value)
                    
            store_metrics.save(db)
        
        return data
    
    
    @staticmethod
    async def calculate_all_stores(db: AsyncSession):
        
        stores = await Store.get_all(db)
        if stores is None:
            return []
        for store in stores:
            
            await MetricService.update_metrics(db, store_id=store.id)
            
    @staticmethod
    def _prev_window(start, end) -> Tuple[Any, Any]:
        """Return the previous window [start - (end-start), start)."""
        delta = end - start
        return start - delta, start

    @staticmethod
    def _pct_change(curr: float, prev: float) -> float:
        """Safe percentage change with good behavior at zero."""
        if prev in (None, 0):
            return 0.0 if curr in (None, 0) else 100.0
        return round(((curr - prev) / prev) * 100.0, 1)

    @staticmethod
    async def compute_overview_metrics(
        db: AsyncSession,
        store_id: str,
        date_range_type: str = "month",
        start_date=None,
        end_date=None,
    ) -> Dict[str, Any]:

        # current window from your helper
        cur_start, cur_end = build_date_filter(date_range_type, start_date, end_date)
        # previous window with identical duration
        prev_start, prev_end = MetricService._prev_window(cur_start, cur_end)

        current = await SubOrder.aggregate_suborders(db, store_id, cur_start, cur_end)
        previous = await SubOrder.aggregate_suborders(db, store_id, prev_start, prev_end)

        # % deltas (current vs previous)
        return {
            **current,
            "revenue_change_percentage":   MetricService._pct_change(current["total_revenue"],   previous["total_revenue"]),
            "orders_change_percentage":    MetricService._pct_change(current["total_orders"],    previous["total_orders"]),
            "customers_change_percentage": MetricService._pct_change(current["total_customers"], previous["total_customers"]),
            "aov":       MetricService._pct_change(current["aov"], previous["aov"]),
            "period": {"start": cur_start, "end": cur_end},
            "prev_period": {"start": prev_start, "end": prev_end},
        }
