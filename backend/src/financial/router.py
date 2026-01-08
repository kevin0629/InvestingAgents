from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from financial.schemas import *

router = APIRouter(prefix="/financial", tags=["financial"])

@router.get("/financial-data", response_model=FinancialDataResponse)
async def get_financial_data():
    

@router.get("/dupont-analysis", response_model=DuPontAnalysisResponse)
async def get_dupont_analysis():
    pass