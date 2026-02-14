from pydantic import BaseModel, Field


class CompanyResponse(BaseModel):
    """公司資訊回應"""
    model_config = {"from_attributes": True}
    company_symbol: str = Field(..., description="股票代號")
    name: str = Field(..., description="公司名稱")
    industry: str = Field(..., description="產業")
    subindustry: str = Field(..., description="子產業")
    business1: str = Field(..., description="主要業務1")
    business2: str = Field(..., description="主要業務2")
    business3: str = Field(..., description="主要業務3")
    # main_product_proportion: Optional[str] = Field(None, description="主要產品比重")


class CompanyListResponse(BaseModel):
    """公司資訊列表回應"""
    companies_data: list[CompanyResponse] = Field(..., description="公司資訊資料列表")