from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.company.schemas import CompanyResponse, CompanyListResponse
from src.company.service import CompanyService
from src.database import get_db

router = APIRouter(prefix="/company", tags=["company"])

def get_company_service(session: AsyncSession = Depends(get_db)) -> CompanyService:
    return CompanyService(session)

@router.get("/", response_model=CompanyListResponse)
async def get_companys(service: CompanyService = Depends(get_company_service)):
    data = await service.get_all_companies()
    
    return CompanyListResponse(companies_data=data)


@router.get("/{company_symbol}", response_model=CompanyResponse)
async def get_company(company_symbol: str, service: CompanyService = Depends(get_company_service)):
    data = await service.get_company_by_symbol(company_symbol)
    if not data:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return data
