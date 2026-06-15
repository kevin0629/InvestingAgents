from langchain_core.tools import tool
import requests
from typing import Annotated, Dict, Any
import pandas as pd
import os
from .utils import bytes2image



BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")

def get_company_info(company_symbol: str) -> str:
    """
    獲取指定公司的基本資料
    
    Args:
        company_symbol: 股票代碼，例如 "2330"
        
    Returns:
        公司基本資料
        
    Raises:
        requests.HTTPError: If API request fails
    """
    url = f"{BASE_URL}/company/{company_symbol}"

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



@tool
def get_factors(
    symbol: Annotated[str, "stock symbol of the company"],
    end_date: Annotated[str, "end date for data retrieval, format YYYY-MM-DD"] = None,
) -> str:
    """
    Retrieve financial factors for a given stock symbol.

    Args:
        symbol (str): Stock symbol of the company, e.g. 2330, 2455, 3491
        end_date (str): End date for data retrieval, format YYYY-MM-DD
    Returns:
        str: A formatted report containing financial factors data
    """
    url = f"{BASE_URL}/factor/{symbol}"
    
    params = {}
    if end_date:
        params["end_date"] = end_date
    
    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json().get("data", {})
    converted = pd.DataFrame(data).T.to_csv(index_label='指標')
    header = f"## {symbol} 財務指標\n"
    
    return header + converted



@tool
def get_balance_sheet(
    symbol: Annotated[str, "stock symbol of the company"],
    end_date: Annotated[str, "end date for data retrieval, format YYYY-MM-DD"] = None,
) -> str:
    """
    Retrieve balance sheet data for a given stock symbol.

    Args:
        symbol (str): Stock symbol of the company, e.g. 2330, 2455, 3491
        end_date (str): End date for data retrieval, format YYYY-MM-DD
    Returns:
        str: A formatted report containing balance sheet data
    """
    url = f"{BASE_URL}/fundamental/{symbol}/balance_sheet"
    
    params = {}
    if end_date:
        params["end_date"] = end_date
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    data = response.json().get("data", {})
    converted = pd.DataFrame(data).T.to_csv(index_label='項目')
    header = f"## {symbol} 資產負債表\n"
    
    return header + converted



@tool
def get_income_statement(
    symbol: Annotated[str, "stock symbol of the company"],
    end_date: Annotated[str, "end date for data retrieval, format YYYY-MM-DD"] = None,
) -> str:
    """
    Retrieve income statement data for a given stock symbol.

    Args:
        symbol (str): Stock symbol of the company, e.g. 2330, 2455, 3491
        end_date (str): End date for data retrieval, format YYYY-MM-DD
        num (int): Number of quarters to retrieve
    Returns:
        str: A formatted report containing income statement data
    """
    url = f"{BASE_URL}/fundamental/{symbol}/income_statement"
    
    params = {}
    if end_date:
        params["end_date"] = end_date
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    data = response.json().get("data", {})
    converted = pd.DataFrame(data).T.to_csv(index_label='項目')
    header = f"## {symbol} 損益表\n"

    return header + converted



@tool
def get_cashflow(
    symbol: Annotated[str, "stock symbol of the company"],
    end_date: Annotated[str, "end date for data retrieval, format YYYY-MM-DD"] = None,
) -> str:
    """
    Retrieve cash flow statement data for a given stock symbol.

    Args:
        symbol (str): Stock symbol of the company, e.g. 2330, 2455, 3491
        end_date (str): End date for data retrieval, format YYYY-MM-DD
    Returns:
        str: A formatted report containing cash flow statement data
    """
    url = f"{BASE_URL}/fundamental/{symbol}/cash_flow_statement"
    
    params = {}
    if end_date:
        params["end_date"] = end_date
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    data = response.json().get("data", {})
    converted = pd.DataFrame(data).T.to_csv(index_label='項目')
    header = f"## {symbol} 現金流量表\n"
    
    return header + converted


@tool
def get_monthly_revenue(
    symbol: Annotated[str, "stock symbol of the company"],
    end_date: Annotated[str, "end date for data retrieval, format YYYY-MM-DD"] = None,
) -> str:
    """
    Retrieve monthly revenue data for a given stock symbol.

    Args:
        symbol (str): Stock symbol of the company, e.g. 2330, 2455, 3491
        end_date (str): End date for data retrieval, format YYYY-MM-DD
    Returns:
        str: A formatted report containing monthly revenue data
    """
    url = f"{BASE_URL}/fundamental/{symbol}/monthly_revenue"
    
    params = {}
    if end_date:
        params["end_date"] = end_date
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json().get("data", {})
    converted = pd.DataFrame(data).T.to_csv(index_label='項目')
    header = f"## {symbol} 月營收\n"
    
    return header + converted



@tool
def get_dupont_analysis(
    symbol: Annotated[str, "stock symbol of the company"],
    end_date: Annotated[str, "end date for data retrieval, format YYYY-MM-DD"] = None,
) -> Dict[str, Any]:
    """
    Retrieve DuPont analysis data for a given stock symbol.

    Args:
        symbol (str): Stock symbol of the company, e.g. 2330, 2455, 3491
        end_date (str): End date for data retrieval, format YYYY-MM-DD
    Returns:
        str: A formatted report containing DuPont analysis data
    """
    url = f"{BASE_URL}/factor/{symbol}/dupont"
    
    params = {}
    if end_date:
        params["end_date"] = end_date
    
    response = requests.get(url, params=params)
    response.raise_for_status()

    data  = response.json().get("dupont_analysis", [])
    header = f"## {symbol} 杜邦分析\n"

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



@tool
def get_river_chart(
    symbol: Annotated[str, "stock symbol of the company"],
    end_date: Annotated[str, "end date for data retrieval, format YYYY-MM-DD"] = None,
) -> list:
    """
    Retrieve river chart (PE band history) for a given stock symbol.

    Args:
        symbol (str): Stock symbol of the company, e.g. 2330, 2455, 3491
        end_date (str): End date for data retrieval, format YYYY-MM-DD
    Returns:
        list: Multimodal content block containing the river chart image for the LLM to interpret.
    """
    url = f"{BASE_URL}/stock/{symbol}/river"
    
    params = {}
    if end_date:
        params["end_date"] = end_date
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    return bytes2image(response.content)