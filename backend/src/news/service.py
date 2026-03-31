from datetime import date, datetime, timedelta
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
        try:
            date_only = date.fromisoformat(end_date)
        except ValueError:
            return datetime.fromisoformat(end_date)
        return datetime.combine(date_only, datetime.max.time())

    def _get_end_datetime(self, end_date: Optional[str]) -> datetime:
        return self._normalize_end_date(end_date) or datetime.combine(date.today(), datetime.max.time())

    def _get_start_datetime_for_months(self, end_datetime: datetime, look_back_months: int) -> datetime:
        days = max(look_back_months, 1) * 30
        return end_datetime - timedelta(days=days)

    def _get_start_datetime_for_days(self, end_datetime: datetime, look_back_days: int) -> datetime:
        days = max(look_back_days, 1)
        return end_datetime - timedelta(days=days)

    async def get_company_news(self, company_symbol: str, end_date: Optional[str] = None, look_back_months: int = 1, limit: int = 10) -> List[dict]:
        end_datetime = self._get_end_datetime(end_date)
        target_limit = max(limit, 10)
        start_datetime = self._get_start_datetime_for_months(end_datetime, look_back_months)

        base_stmt = (
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
        )

        def _build_stmt(window_start: datetime, window_end: datetime) -> object:
            return (
                base_stmt
                .where(CompanyNews.published_at >= window_start)
                .where(CompanyNews.published_at <= window_end)
                .limit(target_limit)
            )
        async with self.db.async_session() as session:
            result = await session.execute(_build_stmt(start_datetime, end_datetime))
            rows = [dict(row) for row in result.mappings().all()]

            if len(rows) <= 1:
                earliest_start = end_datetime - timedelta(days=365)
                last_count = len(rows)

                while start_datetime > earliest_start:
                    start_datetime = max(
                        earliest_start,
                        self._get_start_datetime_for_months(start_datetime, look_back_months),
                    )
                    expanded_result = await session.execute(_build_stmt(start_datetime, end_datetime))
                    rows = [dict(row) for row in expanded_result.mappings().all()]
                    if len(rows) == last_count:
                        break
                    last_count = len(rows)
                    if last_count >= target_limit:
                        break

            return rows[:limit]

    async def get_macro_news(self, end_date: Optional[str] = None, look_back_days: int = 7, limit: int = 50) -> List[dict]:
        end_datetime = self._get_end_datetime(end_date)
        start_datetime = self._get_start_datetime_for_days(end_datetime, look_back_days)

        stmt = (
            select(
                MacroNews.id,
                MacroNews.title,
                MacroNews.content,
                MacroNews.published_at,
                MacroNews.link,
            )
            .select_from(MacroNews)
            .where(MacroNews.published_at >= start_datetime)
            .where(MacroNews.published_at <= end_datetime)
            .order_by(MacroNews.published_at.desc())
            .limit(limit)
        )

        async with self.db.async_session() as session:
            result = await session.execute(stmt)
            rows = result.mappings().all()
            return [dict(row) for row in rows]