from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Taiex, Stock, Company, Factor, FactorValue


class FinancialFactorService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_financial_factor_data(date: str):