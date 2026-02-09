from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Company, Factor, FactorValue
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import defaultdict
from dateutil.relativedelta import relativedelta

class FactorService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_company_all_factors(self, company_symbol: str, end_date: str = None, num: int = 4):
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
                FactorValue.date,
                FactorValue.release_date,
                Factor.factor_name,
                FactorValue.factor_value,
            )
            .join(Factor, FactorValue.factor_id == Factor.id)
            .where(FactorValue.company_id == company.id)
            .where(FactorValue.release_date > end_date - relativedelta(months=num*3))
            .where(FactorValue.release_date <= end_date)
            .order_by(FactorValue.date.desc())
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
            factor_name = row[2]
            factor_value = row[3]

            # compute keys
            year_key = f"{date.year}"
            quarter_key = f"{date.year}Q{((date.month - 1) // 3 + 1)}"
            month_key = release_date.strftime("%Y/%m")

            if "year" in containers:
                containers["year"][factor_name][year_key].append(factor_value)
            if "quarter" in containers and factor_name not in ["MRYoY", "CRYoY"]:
                containers["quarter"][factor_name][quarter_key].append(factor_value)
            if "month" in containers and factor_name in ["MRYoY", "CRYoY"]:
                containers["month"][factor_name][month_key].append(factor_value)

        return containers

    async def get_company_factor_by_name(self, company_symbol: str, factor_name: str, end_date: str = None, num: int = 4):
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
                FactorValue.date,
                FactorValue.release_date,
                Factor.factor_name,
                FactorValue.factor_value,
            )
            .join(Factor, FactorValue.factor_id == Factor.id)
            .where(FactorValue.company_id == company.id)
            .where(Factor.factor_name == factor_name)
            .where(FactorValue.release_date > end_date - relativedelta(months=num*3))
            .where(FactorValue.release_date <= end_date)
            .order_by(FactorValue.date.desc())
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        if not rows:
            return {}
        
        groups = []
        if factor_name in ["MRYoY", "CRYoY"]:
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
        
        FactorList = ["ROE", "PM", "ATR", "ER"]
        stmt = (
            select(
                FactorValue.date,
                FactorValue.release_date,
                Factor.factor_name,
                FactorValue.factor_value,
            )
            .join(Factor, FactorValue.factor_id == Factor.id)
            .where(FactorValue.company_id == company.id)
            .where(Factor.factor_name.in_(FactorList))
            .where(FactorValue.release_date > end_date - relativedelta(months=num*3))
            .where(FactorValue.release_date <= end_date)
            .order_by(FactorValue.date.desc())
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        if not rows:
            return {}
        
        # 按日期和發布日期分組數據
        date_groups = defaultdict(lambda: {"date": None, "release_date": None, "factors": {}})
        
        for row in rows:
            date = row[0]
            release_date = row[1]
            factor_name = row[2]
            factor_value = row[3]
            
            # 使用季度鍵作為分組依據
            quarter_key = f"{date.year}Q{((date.month - 1) // 3 + 1)}"
            
            if date_groups[quarter_key]["date"] is None:
                date_groups[quarter_key]["date"] = date.isoformat()
                date_groups[quarter_key]["release_date"] = release_date.isoformat()
            
            # 儲存因子值
            if factor_name == "ROE":
                date_groups[quarter_key]["factors"]["ROE"] = factor_value
            elif factor_name == "PM":
                date_groups[quarter_key]["factors"]["PM"] = factor_value
            elif factor_name == "ATR":
                date_groups[quarter_key]["factors"]["ATR"] = factor_value / 100
            elif factor_name == "ER":
                date_groups[quarter_key]["factors"]["ER"] = factor_value / 100
        
        # 計算杜邦分析並格式化結果
        result_data = []
        for quarter_key in sorted(date_groups.keys(), reverse=True):
            group = date_groups[quarter_key]
            factors = group["factors"]
            
            # 確保所有所需因子都存在
            if all(k in factors for k in ["ROE", "PM", "ATR", "ER"]):
                roe_actual = factors["ROE"]
                pm = factors["PM"]
                atr = factors["ATR"]
                er = factors["ER"]
                
                
                result_data.append({
                    "period": quarter_key,
                    "formula": f"{roe_actual}% = {pm}% × {round(atr, 4)} × {round(er, 4)}",
                })
        
        return {"dupont_analysis": result_data}