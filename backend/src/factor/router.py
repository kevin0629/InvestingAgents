from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.factor.schemas import FactorResponse
from src.factor.service import FactorService
from typing import Optional

router = APIRouter(prefix="/factor", tags=["factor"])

@router.get("/{company_symbol}", response_model=FactorResponse)
async def get_company_factors(
    company_symbol: str, 
    end_date: Optional[str] = None, 
    num: int = 4, 
    db: AsyncSession = Depends(get_db)
):
    service = FactorService(db)
    data = await service.get_company_all_factors(company_symbol, end_date, num)

    if not data:
        raise HTTPException(status_code=404, detail="Can not find the company data")
    
    return FactorResponse(data=data)

@router.get("/{company_symbol}/{factor_name}", response_model=FactorResponse)
async def get_factor_by_name(
    company_symbol: str, 
    factor_name: str, 
    end_date: Optional[str] = None, 
    num: int = 4, 
    db: AsyncSession = Depends(get_db)
):
    service = FactorService(db)
    data = await service.get_company_factor_by_name(company_symbol, factor_name, end_date, num)
    
    if not data:
        raise HTTPException(status_code=404, detail="Can not find the company data")
    
    return FactorResponse(data=data)
