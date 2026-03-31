from datetime import date, datetime
from typing import Optional, List

from sqlalchemy import select

from src.database import Database
from src.models import Company, CompanyNews, CompanyNewsRelation, MacroNews


class NewsService:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()

    def _normalize_end_date(self, end_date: Optional[str]) -> Optional[datetime]:
        if end_date is None:
            return None
        if isinstance(end_date, datetime):
            return end_date
        if isinstance(end_date, date):
            return datetime.combine(end_date, datetime.max.time())
        return datetime.fromisoformat(end_date)

    async def get_company_news(self, company_symbol: str, end_date: Optional[str] = None, limit: int = 10) -> List[dict]:
        end_datetime = self._normalize_end_date(end_date)

        stmt = (
            select(
                CompanyNews.id,
                CompanyNews.title,
                CompanyNews.content,
                CompanyNews.published_at,
                CompanyNews.link,
                Company.symbol.label("company_symbol"),
            )
            .select_from(CompanyNews)
            .join(CompanyNewsRelation, CompanyNewsRelation.news_id == CompanyNews.id)
            .join(Company, Company.id == CompanyNewsRelation.company_id)
            .where(Company.symbol == company_symbol)
            .order_by(CompanyNews.published_at.desc())
            .limit(limit)
        )

        if end_datetime is not None:
            stmt = stmt.where(CompanyNews.published_at <= end_datetime)

        async with self.db.async_session() as session:
            result = await session.execute(stmt)
            rows = result.mappings().all()
            return [dict(row) for row in rows]

    async def get_macro_news(self, end_date: Optional[str] = None, limit: int = 50) -> List[dict]:
        end_datetime = self._normalize_end_date(end_date)

        stmt = (
            select(
                MacroNews.id,
                MacroNews.title,
                MacroNews.content,
                MacroNews.published_at,
                MacroNews.link,
            )
            .select_from(MacroNews)
            .order_by(MacroNews.published_at.desc())
            .limit(limit)
        )

        if end_datetime is not None:
            stmt = stmt.where(MacroNews.published_at <= end_datetime)

        async with self.db.async_session() as session:
            result = await session.execute(stmt)
            rows = result.mappings().all()
            return [dict(row) for row in rows]