from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Company, SingleIndicator, FinancialReportIndicatorValue
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import defaultdict
from dateutil.relativedelta import relativedelta


class IndicatorService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_company_all_indicators(self, company_symbol: str, end_date: str = None, num: int = 4):
        if end_date is None:
            end_date = datetime.now(tz=ZoneInfo("Asia/Taipei")).date().isoformat()
        
        end_date = datetime.fromisoformat(end_date)
        stmt = select(Company).where(Company.symbol == company_symbol)
        result = await self.session.execute(stmt)
        company = result.scalars().first()
        
        if not company:
            return {}
        
        stmt = (
            select(
                FinancialReportIndicatorValue.date,
                FinancialReportIndicatorValue.release_date,
                SingleIndicator.tw_indicator,
                FinancialReportIndicatorValue.indicator_value,
            )
            .join(SingleIndicator, FinancialReportIndicatorValue.indicator_id == SingleIndicator.id)
            .where(FinancialReportIndicatorValue.company_id == company.id)
            .where(FinancialReportIndicatorValue.release_date > end_date - relativedelta(months=num*3))
            .where(FinancialReportIndicatorValue.release_date <= end_date)
            .order_by(FinancialReportIndicatorValue.date.desc())
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        data = await self.aggregated(rows, groups=["quarter", "month"])

        return data

    async def aggregated(self, rows: List, groups: Optional[List[str]] = None):
        """
        Aggregate rows into separate tables for year/quarter/month.

        Returns a dict with keys 'year', 'quarter', 'month'

        - `groups`: list choosing which groupings to produce (subset of ['year','quarter','month'])
        """
        if groups is None:
            groups = ["quarter", "month"]

        # prepare containers for each requested grouping
        containers = {}
        for g in groups:
            containers[g] = defaultdict(lambda: defaultdict(list))

        for row in rows:
            date = row[0]
            release_date = row[1]
            indicator_name = row[2]
            indicator_value = row[3]

            # compute keys
            year_key = f"{date.year}"
            quarter_key = f"{date.year}Q{((date.month - 1) // 3 + 1)}"
            month_key = release_date.strftime("%Y/%m")

            if "year" in containers:
                containers["year"][indicator_name][year_key].append(indicator_value)
            if "quarter" in containers and indicator_name != "當月營收":
                containers["quarter"][indicator_name][quarter_key].append(indicator_value)
            if "month" in containers and indicator_name == "當月營收":
                containers["month"][indicator_name][month_key].append(indicator_value)

        return containers

    async def get_company_indicator_by_name(self, company_symbol: str, indicator_name: str, end_date: str = None, num: int = 4):
        if end_date is None:
            end_date = datetime.now(tz=ZoneInfo("Asia/Taipei")).date().isoformat()
        
        end_date = datetime.fromisoformat(end_date)
        stmt = select(Company).where(Company.symbol == company_symbol)
        result = await self.session.execute(stmt)
        company = result.scalars().first()
        
        if not company:
            return {}
        
        stmt = (
            select(
                FinancialReportIndicatorValue.date,
                FinancialReportIndicatorValue.release_date,
                SingleIndicator.tw_indicator,
                FinancialReportIndicatorValue.indicator_value,
            )
            .join(SingleIndicator, FinancialReportIndicatorValue.indicator_id == SingleIndicator.id)
            .where(FinancialReportIndicatorValue.company_id == company.id)
            .where(SingleIndicator.tw_indicator == indicator_name)
            .where(FinancialReportIndicatorValue.release_date > end_date - relativedelta(months=num*3))
            .where(FinancialReportIndicatorValue.release_date <= end_date)
            .order_by(FinancialReportIndicatorValue.date.desc())
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        if not rows:
            return {}
        
        groups = []
        if indicator_name == "當月營收":
            groups = ["month"]
        else:
            groups = ["quarter"]
        
        data = await self.aggregated(rows, groups=groups)

        return data
    

    async def dupont_analysis(self, company_symbol: str, end_date: str = None, num: int = 4):
        if end_date is None:
            end_date = datetime.now(tz=ZoneInfo("Asia/Taipei")).date().isoformat()
        
        end_date = datetime.fromisoformat(end_date)
        stmt = select(Company).where(Company.symbol == company_symbol)
        result = await self.session.execute(stmt)
        company = result.scalars().first()

        if not company:
            return {}
        
        indicatorList = [""]
        stmt = (
            select(
                FinancialReportIndicatorValue.date,
                FinancialReportIndicatorValue.release_date,
                SingleIndicator.tw_indicator,
                FinancialReportIndicatorValue.indicator_value,
            )
            .join(SingleIndicator, FinancialReportIndicatorValue.indicator_id == SingleIndicator.id)
            .where(FinancialReportIndicatorValue.company_id == company.id)
            .where(SingleIndicator.tw_indicator == indicator_name)
            .where(FinancialReportIndicatorValue.release_date > end_date - relativedelta(months=num*3))
            .where(FinancialReportIndicatorValue.release_date <= end_date)
            .order_by(FinancialReportIndicatorValue.date.desc())
        )