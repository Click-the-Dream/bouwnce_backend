from sqlalchemy import Column, Float, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import BaseModel
from app.utils.helper import build_date_filter
from sqlalchemy import func, select


class StoreMetrics(BaseModel):
    __tablename__ = "store_metrics"

    store_id = Column(String, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    total_orders = Column(Integer, default=0)
    total_customers = Column(Integer, default=0)
    total_revenue = Column(Float, default=0.0)
    aov = Column(Float, default=0.0)

    
    store = relationship("Store", back_populates="metrics", uselist=False)


    async def recalculate_metrics(self, db: AsyncSession, date_range_type: str, start_date=None, end_date=None):
        start_date, end_date = build_date_filter(date_range_type, start_date, end_date)
        
        stmt = select(
            func.count(StoreMetrics.total_orders).label("total_orders"),
            func.count(StoreMetrics.total_customers).label("total_customers"),
            func.sum(StoreMetrics.total_revenue).label("total_revenue")
            
        ).where(
            StoreMetrics.store_id == self.store_id,
            StoreMetrics.created_at >= start_date,
            StoreMetrics.created_at <= end_date
        )
        
        result = await db.execute(stmt)
        metrics = result.fetchone()
        
        
        
