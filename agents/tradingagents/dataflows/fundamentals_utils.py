import requests
from typing import Optional, Dict, Any
import pandas as pd
from .utils import get_backend_base_url



def get_company_by_symbol(company_symbol: str) -> str:
    """
    獲取指定公司的基本資料
    
    Args:
        company_symbol: 股票代碼，例如 "2330"
        
    Returns:
        公司基本資料
        
    Raises:
        requests.HTTPError: If API request fails
    """
    base_url = get_backend_base_url()
    url = f"{base_url}/company/{company_symbol}"
    
    response = requests.get(url)
    response.raise_for_status()

    data = response.json()
    data.pop("company_symbol", None)  # Remove company_symbol from data as it's already in the header
    info_str = f"## {company_symbol} 基本資料\n"
    mapping = {
        "name": "公司名稱",
        "industry": "產業別",
        "subindustry": "子產業別",
        "business1": "主要經營業務1",
        "business2": "主要經營業務2",
        "business3": "主要經營業務3",
    }

    for key, value in data.items():
        translated_key = mapping.get(key, key)
        
        info_str += f"{translated_key}: {value}\n"

    return info_str

def get_company_factors(
    company_symbol: str,
    end_date: Optional[str] = None,
    num: int = 4
) -> str:
    """
    獲取公司所有財務指標
    
    Args:
        company_symbol: 股票代碼，例如 "2330"
        end_date: 結束日期 (YYYY-MM-DD format), 如果為 None 則使用最新資料
        num: 返回的季節數量，預設為 4
        
    Returns:
        包含所有財務指標
        
    Raises:
        requests.HTTPError: If API request fails
    """
    base_url = get_backend_base_url()
    url = f"{base_url}/factor/{company_symbol}"
    
    params = {"num": num}
    if end_date:
        params["end_date"] = end_date
    
    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json().get("data", {})
    converted = pd.DataFrame(data).T.to_csv(index_label='指標')
    header = f"## {company_symbol} 財務指標\n"
    
    return header + converted


def get_company_balance_sheet(
    company_symbol: str,
    end_date: Optional[str] = None,
    num: int = 4
) -> str:
    """
    獲取公司資產負債表資料
    
    Args:
        company_symbol: 股票代碼，例如 "2330"
        end_date: 結束日期 (YYYY-MM-DD format), 如果為 None 則使用最新資料
        num: 返回的季節數量，預設為 4
        
    Returns:
        包含所有資產負債表資料
    Raises:
        requests.HTTPError: If API request fails
    """
    base_url = get_backend_base_url()
    url = f"{base_url}/fundamental/{company_symbol}/balance_sheet"
    
    params = {"num": num}
    if end_date:
        params["end_date"] = end_date
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    data = response.json().get("data", {})
    converted = pd.DataFrame(data).T.to_csv(index_label='項目')
    header = f"## {company_symbol} 資產負債表\n"
    
    return header + converted

def get_company_income_statement(
    company_symbol: str,
    end_date: Optional[str] = None,
    num: int = 4
) -> str:
    """
    獲取公司損益表資料
    
    Args:
        company_symbol: 股票代碼，例如 "2330"
        end_date: 結束日期 (YYYY-MM-DD format), 如果為 None 則使用最新資料
        num: 返回的季節數量，預設為 4
        
    Returns:
        包含所有損益表資料
        
    Raises:
        requests.HTTPError: If API request fails
    """
    base_url = get_backend_base_url()
    url = f"{base_url}/fundamental/{company_symbol}/income_statement"
    
    params = {"num": num}
    if end_date:
        params["end_date"] = end_date
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    data = response.json().get("data", {})
    converted = pd.DataFrame(data).T.to_csv(index_label='項目')
    header = f"## {company_symbol} 損益表\n"

    return header + converted

def get_company_cash_flow_statement(
    company_symbol: str,
    end_date: Optional[str] = None,
    num: int = 4
) -> str:
    """
    獲取公司現金流量表資料
    
    Args:
        company_symbol: 股票代碼，例如 "2330"
        end_date: 結束日期 (YYYY-MM-DD format), 如果為 None 則使用最新資料
        num: 返回的資料季節數量，預設為 4
        
    Returns:
        包含所有現金流量表資料的字典
        
    Raises:
        requests.HTTPError: If API request fails
    """
    base_url = get_backend_base_url()
    url = f"{base_url}/fundamental/{company_symbol}/cash_flow_statement"
    
    params = {"num": num}
    if end_date:
        params["end_date"] = end_date
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    data = response.json().get("data", {})
    converted = pd.DataFrame(data).T.to_csv(index_label='項目')
    header = f"## {company_symbol} 現金流量表\n"
    
    return header + converted

def get_company_monthly_revenue(
    company_symbol: str,
    end_date: Optional[str] = None,
    num: int = 4
) -> str:
    """
    獲取公司月營收資料
    
    Args:
        company_symbol: 股票代碼，例如 "2330"
        end_date: 結束日期 (YYYY-MM-DD format), 如果為 None 則使用最新資料
        num: 返回的季節數量，預設為 4
        
    Returns:
        包含所有月營收的字典
        
    Raises:
        requests.HTTPError: If API request fails
    """
    base_url = get_backend_base_url()
    url = f"{base_url}/fundamental/{company_symbol}/monthly_revenue"
    
    params = {"num": num}
    if end_date:
        params["end_date"] = end_date
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json().get("data", {})
    converted = pd.DataFrame(data).T.to_csv(index_label='項目')
    header = f"## {company_symbol} 月營收\n"
    
    return header + converted


def get_dupont_analysis(
    company_symbol: str,
    end_date: Optional[str] = None,
    num: int = 4
) -> Dict[str, Any]:
    """
    獲取公司的杜邦分析數據
    
    杜邦公式：ROE = 淨利率(PM) × 總資產周轉率(ATR) × 權益乘數(ER)
    
    Args:
        company_symbol: 股票代碼，例如 "2330"
        end_date: 結束日期 (YYYY-MM-DD format), 如果為 None 則使用最新資料
        num: 返回的季節數量，預設為 4
        
    Returns:
        包含杜邦分析數據的字典
        
    Raises:
        requests.HTTPError: If API request fails
    """
    base_url = get_backend_base_url()
    url = f"{base_url}/factor/{company_symbol}/dupont"
    
    params = {"num": num}
    if end_date:
        params["end_date"] = end_date
    
    response = requests.get(url, params=params)
    response.raise_for_status()

    data  = response.json().get("dupont_analysis", [])
    header = f"## {company_symbol} 杜邦分析\n"

    contents = ""
    for item in data:
        content = ""
        for key, value in item.items():
            if key == "period":
                content += f"{value}: "
            else:
                content += f"{value}\n"
        contents += content

    return header + contents


def get_stock_river_chart(
    company_symbol: str,
    end_date: Optional[str] = None
) -> bytes:
    """
    獲取股票本益比河流圖
    
    Args:
        company_symbol: 股票代碼，例如 "2330"
        end_date: 結束日期 (YYYY-MM-DD format), 如果為 None 則使用最新資料
        
    Returns:
        PNG image bytes
        
    Raises:
        requests.HTTPError: If API request fails
    """
    base_url = get_backend_base_url()
    url = f"{base_url}/stock/{company_symbol}/river"
    
    params = {}
    if end_date:
        params["end_date"] = end_date
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    return response.content


if __name__ == "__main__":
    # Example usage
    company_symbol = "3491"
    print(get_company_by_symbol(company_symbol))
    # print(get_company_all_factors(company_symbol))
    # print(get_factor_by_name(company_symbol, "ROE"))
    # print(get_company_balance_sheet(company_symbol))
    # print(get_company_income_statement(company_symbol))
    # print(get_company_cash_flow_statement(company_symbol))
    # print(get_company_monthly_revenue(company_symbol, '2025-11-21'))
    # print(get_dupont_analysis(company_symbol, '2025-11-21', 6))
    
