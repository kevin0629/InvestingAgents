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

    def _get_start_datetime_for_days(self, end_datetime: datetime, look_back_days: int) -> datetime:
        days = max(look_back_days, 1)
        return end_datetime - timedelta(days=days)

    def _extract_first_paragraph(self, content: Optional[str]) -> str:
        text = (content or "").strip()
        if not text:
            return ""

        # News sources often separate paragraphs with a single newline, not blank lines.
        # Take the first non-empty line as the first paragraph/sentence block.
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if lines:
            return lines[0]

        return text

    async def get_company_news(self, company_symbol: str, end_date: Optional[str] = None, look_back_days: Optional[int] = None, limit: int = 10) -> List[dict]:
        end_datetime = self._get_end_datetime(end_date)
        start_datetime = (
            self._get_start_datetime_for_days(end_datetime, look_back_days)
            if look_back_days is not None
            else None
        )

        base_stmt = (
            select(
                CompanyNews.id,
                CompanyNews.title,
                CompanyNewsRelation.related_content.label("content"),
                CompanyNews.published_at,
                CompanyNews.link,
                Company.symbol.label("company_symbol"),
            )
            .select_from(CompanyNews)
            .join(CompanyNewsRelation, CompanyNewsRelation.news_id == CompanyNews.id)
            .join(Company, Company.id == CompanyNewsRelation.company_id)
            .where(Company.symbol == company_symbol)
            .where(CompanyNews.published_at <= end_datetime)
            .order_by(CompanyNews.published_at.desc())
            .limit(limit)
        )

        stmt = base_stmt
        if start_datetime is not None:
            stmt = stmt.where(CompanyNews.published_at >= start_datetime)

        async with self.db.async_session() as session:
            result = await session.execute(stmt)
            rows = [dict(row) for row in result.mappings().all()]
            processed = []
            for row in rows:
                item = dict(row)
                pa = item.get("published_at")
                if isinstance(pa, datetime):
                    item["published_at"] = pa.strftime("%Y-%m-%d")
                else:
                    # fallback to str slice
                    try:
                        item["published_at"] = str(pa)[:10]
                    except Exception:
                        item["published_at"] = None
                processed.append(item)
            return processed

    async def get_macro_news(self, end_date: Optional[str] = None, look_back_days: int = 7, limit: int = 100) -> List[dict]:
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
            processed_rows = []
            for row in rows:
                item = dict(row)
                item["content"] = self._extract_first_paragraph(item.get("content"))
                pa = item.get("published_at")
                if isinstance(pa, datetime):
                    item["published_at"] = pa.strftime("%Y-%m-%d")
                else:
                    try:
                        item["published_at"] = str(pa)[:10]
                    except Exception:
                        item["published_at"] = None
                processed_rows.append(item)
            return processed_rows