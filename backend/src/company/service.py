from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Company


class CompanyService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_companies(self) -> List[Company]:
        stmt = select(Company)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_company_by_symbol(self, company_symbol: str) -> Optional[Company]:
        stmt = select(Company).where(Company.symbol == company_symbol)
        result = await self.session.execute(stmt)
        return result.scalars().first()
