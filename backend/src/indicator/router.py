from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from factor.schemas import *
# from financial.service import financial

router = APIRouter(prefix="/financial", tags=["financial"])

@router.get("/factor", response_model=FinancialDataResponse)
async def get_factor():
    pass

@router.get("/factor/{factor_name}", response_model=FinancialDataResponse)
async def get_factor_by_name(factor_name: str):
    pass

@router.get("/{company_symbol}/factor", response_model=FinancialDataResponse)
async def get_company_factor(company_symbol: str):
    pass


@router.get("/dupont-analysis", response_model=DuPontAnalysisResponse)
async def get_dupont_analysis():
    pass