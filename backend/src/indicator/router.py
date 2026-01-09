from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.indicator.schemas import IndicatorResponse, DuPontAnalysisResponse
from src.indicator.service import IndicatorService
from typing import Optional

router = APIRouter(prefix="/indicator", tags=["indicator"])

@router.get("/{company_symbol}", response_model=IndicatorResponse)
async def get_company_indicators(
    company_symbol: str, 
    end_date: Optional[str] = None, 
    num: int = 4, 
    db: AsyncSession = Depends(get_db)
):
    service = IndicatorService(db)
    data = await service.get_company_all_indicators(company_symbol, end_date, num)

    if not data:
        raise HTTPException(status_code=404, detail="Can not find the company data")
    
    return IndicatorResponse(data=data)

@router.get("/{company_symbol}/{indicator_name}", response_model=IndicatorResponse)
async def get_indicator_by_name(
    company_symbol: str, 
    indicator_name: str, 
    end_date: Optional[str] = None, 
    num: int = 4, 
    db: AsyncSession = Depends(get_db)
):
    service = IndicatorService(db)
    data = await service.get_company_indicator_by_name(company_symbol, indicator_name, end_date, num)

    if not data:
        raise HTTPException(status_code=404, detail="Can not find the company data")
   
    return IndicatorResponse(data=data)


@router.get("/{company_symbol}/dupont", response_model=DuPontAnalysisResponse)
async def dupont_analysis(
    company_symbol: str,  
    end_date: Optional[str] = None, 
    num: int = 4, 
    db: AsyncSession = Depends(get_db)
):
    service = IndicatorService(db)
    data = await service.get_company_all_indicators(company_symbol, end_date, num)

    if not data:
        raise HTTPException(status_code=404, detail="Can not find the company data")
   
    return DuPontAnalysisResponse(**data)