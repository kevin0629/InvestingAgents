import asyncio
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api", tags=["backtest"])



@router.get("/dupont-analysis", response_model=)
async def get_dupont_analysis():
