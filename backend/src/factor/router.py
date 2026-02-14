from fastapi import APIRouter, HTTPException
from src.factor.schemas import FactorResponse, DuPontAnalysisResponse
from src.factor.service import FactorService
from typing import Optional
from src.utils import get_data_instance

router = APIRouter(prefix="/factor", tags=["factor"])

@router.get("/{company_symbol}", response_model=FactorResponse)
async def get_company_factors(
    company_symbol: str, 
    end_date: Optional[str] = None, 
    num: int = 4
):
    service = FactorService(get_data_instance())
    data = service.get_company_all_factors(company_symbol, end_date, num)

    if not data:
        raise HTTPException(status_code=404, detail="Can not find the company data")
    
    return FactorResponse(data=data)

@router.get("/{company_symbol}/dupont", response_model=DuPontAnalysisResponse)
async def dupont_analysis(
    company_symbol: str,  
    end_date: Optional[str] = None, 
    num: int = 4
):
    """
    獲取公司的杜邦分析數據
    
    杜邦公式：ROE = 淨利率(PM) × 總資產周轉率(ATR) × 權益乘數(ER)
    """
    service = FactorService(get_data_instance())
    data = service.dupont_analysis(company_symbol, end_date, num)

    if not data:
        raise HTTPException(status_code=404, detail="Can not find the company data")
   
    return data

@router.get("/{company_symbol}/{factor_name}", response_model=FactorResponse)
async def get_factor_by_name(
    company_symbol: str, 
    factor_name: str, 
    end_date: Optional[str] = None, 
    num: int = 4, 
):
    service = FactorService(get_data_instance())
    data = service.get_company_factor_by_name(company_symbol, factor_name, end_date, num)
    
    if not data:
        raise HTTPException(status_code=404, detail="Can not find the company data")
    
    return FactorResponse(data=data)
