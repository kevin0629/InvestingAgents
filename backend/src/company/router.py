from fastapi import APIRouter, HTTPException
from src.company.schemas import CompanyResponse, CompanyListResponse
from src.company.service import CompanyService
from src.utils import get_data_instance

router = APIRouter(prefix="/company", tags=["company"])

@router.get("/", response_model=CompanyListResponse)
async def get_companys():
    service = CompanyService(get_data_instance())
    data = service.get_all_companies()
    
    return CompanyListResponse(data=data)
    


@router.get("/{company_symbol}", response_model=CompanyResponse)
async def get_company(company_symbol: str):
    service = CompanyService(get_data_instance())
    data = service.get_company_by_symbol(company_symbol)
    if not data:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return CompanyResponse(**data)
