from fastapi import APIRouter, HTTPException
from src.fundamental.schemas import IndicatorResponse
from src.fundamental.service import IndicatorService
from typing import Optional
from src.utils import get_data_instance

router = APIRouter(prefix="/fundmental", tags=["fundmental"])

@router.get("/{company_symbol}/balance_sheet", response_model=IndicatorResponse)
async def get_company_balance_sheet(
    company_symbol: str, 
    end_date: Optional[str] = None, 
    num: int = 4,
):
    service = IndicatorService(get_data_instance())
    data = service.get_company_balance_sheet(company_symbol, end_date, num)

    if not data:
        raise HTTPException(status_code=404, detail="Can not find the company data")
    
    return IndicatorResponse(data=data)

@router.get("/{company_symbol}/income_statement", response_model=IndicatorResponse)
async def get_company_income_statement(
    company_symbol: str, 
    end_date: Optional[str] = None, 
    num: int = 4,
):
    service = IndicatorService(get_data_instance())
    data = service.get_company_income_statement(company_symbol, end_date, num)

    if not data:
        raise HTTPException(status_code=404, detail="Can not find the company data")
    
    return IndicatorResponse(data=data)

@router.get("/{company_symbol}/cash_flow_statement", response_model=IndicatorResponse)
async def get_company_cash_flow_statement(
    company_symbol: str, 
    end_date: Optional[str] = None, 
    num: int = 4,
):
    service = IndicatorService(get_data_instance())
    data = service.get_company_cash_flow_statement(company_symbol, end_date, num)

    if not data:
        raise HTTPException(status_code=404, detail="Can not find the company data")
    
    return IndicatorResponse(data=data)

@router.get("/{company_symbol}/monthly_revenue", response_model=IndicatorResponse)
async def get_company_monthly_revenue(
    company_symbol: str, 
    end_date: Optional[str] = None, 
    num: int = 4,
):
    service = IndicatorService(get_data_instance())
    data = service.get_company_monthly_revenue(company_symbol, end_date, num)

    if not data:
        raise HTTPException(status_code=404, detail="Can not find the company data")
    
    return IndicatorResponse(data=data)