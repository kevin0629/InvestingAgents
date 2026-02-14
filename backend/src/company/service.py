from typing import List, Optional


class CompanyService:
    def __init__(self, data_instance):
        self.data = data_instance

    def get_all_companies(self):
        data = self.data.get("company_info")
        return list(data.to_dict(orient="records"))


    def get_company_by_symbol(self, company_symbol: str):
        data = self.data.get("company_info")
        company_data = data[data["company_symbol"] == company_symbol]
        if company_data.empty:
            return None
        return company_data.iloc[0].to_dict()
