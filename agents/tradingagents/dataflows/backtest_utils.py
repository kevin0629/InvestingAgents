import requests
from typing import Optional, Dict, Any
from .utils import get_backend_base_url
import pandas as pd


def get_backtest_report(
    strategy_name: str,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    獲取回測報告

    Args:
        strategy_name: 策略名稱，例如 "monthly_revenue_growth_roe"
        end_date: 回測結束日期 (YYYY-MM-DD format), 如果為 None 則使用最新資料

    Returns:
        回測報告的字典格式資料

    Raises:
        requests.HTTPError: If API request fails
    """
    base_url = get_backend_base_url()
    url = f"{base_url}/backtest/report"
    
    params = {"strategy_name": strategy_name}
    if end_date:
        params["end_date"] = end_date
    
    response = requests.get(url, params=params)
    response.raise_for_status()

    performance = response.json().get("performance", {})
    next_holdings = response.json().get("current_holdings", [])

    header = f"## 策略回測報告: {strategy_name}\n\n"

    content = "### 策略歷史績效(自2005年起)\n"
    for key, value in performance.items():
        content += f"{key}: {value}, "

    for holding in next_holdings:
        if isinstance(holding, dict):
            holding.pop("entry_price", None)
            holding.pop("entry_date", None)
            
    content += "\n### 下期交易訊號\n"
    content += pd.DataFrame(next_holdings).to_csv(index=False)

    return header + content


def get_strategy() -> str:
    """
    獲取所有已知的策略與其描述
    
    Args:
        
    Returns:
        包含所有策略與其描述
        
    Raises:
        requests.HTTPError: If API request fails
    """
    base_url = get_backend_base_url()
    url = f"{base_url}/backtest/strategy"

    response = requests.get(url)
    response.raise_for_status()
    data = response.json().get("strategies", [])

    header = "## 可用策略列表\n"

    content = ""
    for strategy in data:
        for key, value in strategy.items():
            if key == "name":
                content += value
            elif key == "description":
                content += f", {key}: {value}\n"
                break

    return header + content


if __name__ == "__main__":
    print(get_backtest_report("monthly_revenue_growth_roe", '2025-11-21'))