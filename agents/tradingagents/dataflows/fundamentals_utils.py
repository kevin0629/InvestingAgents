import requests
import os
from typing import Optional, Dict, Any, List


def get_backend_base_url() -> str:
    """Get the backend base URL from environment or default."""
    return os.getenv("BACKEND_API_URL", "http://localhost:8000")


def get_all_companies() -> List[Dict[str, Any]]:
    """
    獲取所有公司基本資料列表
    
    Returns:
        包含所有公司資料的列表
        
    Raises:
        requests.HTTPError: If API request fails
    """
    base_url = get_backend_base_url()
    url = f"{base_url}/company/"
    
    response = requests.get(url)
    response.raise_for_status()
    
    data = response.json()
    return data.get("companies_data", [])


def get_company_by_symbol(company_symbol: str) -> Dict[str, Any]:
    """
    獲取指定公司的基本資料
    
    Args:
        company_symbol: 股票代碼，例如 "2330"
        
    Returns:
        公司基本資料字典
        
    Raises:
        requests.HTTPError: If API request fails
    """
    base_url = get_backend_base_url()
    url = f"{base_url}/company/{company_symbol}"
    
    response = requests.get(url)
    response.raise_for_status()
    
    return response.json()


def get_company_all_factors(
    company_symbol: str,
    end_date: Optional[str] = None,
    num: int = 4
) -> Dict[str, Any]:
    """
    獲取公司所有財務比率
    
    Args:
        company_symbol: 股票代碼，例如 "2330"
        end_date: 結束日期 (YYYY-MM-DD format), 如果為 None 則使用最新資料
        num: 返回的資料筆數，預設為 4
        
    Returns:
        包含所有財務比率的字典
        
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
    
    return response.json()


def get_factor_by_name(
    company_symbol: str,
    factor_name: str,
    end_date: Optional[str] = None,
    num: int = 4
) -> Dict[str, Any]:
    """
    獲取指定財務比率
    
    Args:
        company_symbol: 股票代碼，例如 "2330"
        factor_name: 財務比率名稱，例如 "ROE", "ROA", "負債比率"
        end_date: 結束日期 (YYYY-MM-DD format), 如果為 None 則使用最新資料
        num: 返回的資料筆數，預設為 4
        
    Returns:
        包含指定財務比率的字典
        
    Raises:
        requests.HTTPError: If API request fails
    """
    base_url = get_backend_base_url()
    url = f"{base_url}/factor/{company_symbol}/{factor_name}"
    
    params = {"num": num}
    if end_date:
        params["end_date"] = end_date
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    return response.json()


def get_company_indicators(
    company_symbol: str,
    end_date: Optional[str] = None,
    num: int = 4
) -> Dict[str, Any]:
    """
    獲取公司所有財務指標
    
    Args:
        company_symbol: 股票代碼，例如 "2330"
        end_date: 結束日期 (YYYY-MM-DD format), 如果為 None 則使用最新資料
        num: 返回的資料筆數，預設為 4
        
    Returns:
        包含所有財務指標的字典
        
    Raises:
        requests.HTTPError: If API request fails
    """
    base_url = get_backend_base_url()
    url = f"{base_url}/indicator/{company_symbol}"
    
    params = {"num": num}
    if end_date:
        params["end_date"] = end_date
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    return response.json()


def get_indicator_by_name(
    company_symbol: str,
    indicator_name: str,
    end_date: Optional[str] = None,
    num: int = 4
) -> Dict[str, Any]:
    """
    獲取指定財務指標
    
    Args:
        company_symbol: 股票代碼，例如 "2330"
        indicator_name: 指標名稱，例如 "現金及約當現金", "短期投資", "長期投資"
        end_date: 結束日期 (YYYY-MM-DD format), 如果為 None 則使用最新資料
        num: 返回的資料筆數，預設為 4
        
    Returns:
        包含指定財務指標的字典
        
    Raises:
        requests.HTTPError: If API request fails
    """
    base_url = get_backend_base_url()
    url = f"{base_url}/indicator/{company_symbol}/{indicator_name}"
    
    params = {"num": num}
    if end_date:
        params["end_date"] = end_date
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    return response.json()


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
        num: 返回的資料筆數，預設為 4
        
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
    
    return response.json()


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
    company_symbol = "2330"
    # print(get_company_by_symbol(company_symbol))
    # print(get_company_all_factors(company_symbol))
    # print(get_factor_by_name(company_symbol, "ROE"))
    # print(get_company_indicators(company_symbol))
    # print(get_indicator_by_name(company_symbol, "現金及約當現金"))
    # print(get_dupont_analysis(company_symbol))
    
