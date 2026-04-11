import requests
import json
from typing import Optional, Dict, Any
from .utils import get_backend_base_url
import pandas as pd


def get_backtest_report(
    strategy_name: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    獲取回測報告

    Args:
        strategy_name: 策略名稱，例如 "monthly_revenue_growth_roe"
        start_date: 回測開始日期 (YYYY-MM-DD format), 如果為 None 則使用最早資料
        end_date: 回測結束日期 (YYYY-MM-DD format), 如果為 None 則使用最新資料

    Returns:
        回測報告的字典格式資料

    Raises:
        requests.HTTPError: If API request fails
    """
    base_url = get_backend_base_url()
    url = f"{base_url}/backtest/report"
    
    params = {"strategy_name": strategy_name}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    
    response = requests.get(url, params=params)
    response.raise_for_status()

    return response.json()


def get_strategy() -> Dict[str, str]:
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
    data = response.json()

    return data


def get_backtest_sim(
    signal: Dict[str, Any],
    entry_sig_date: str,
    exit_sig_date: Optional[str] = None,
) -> Dict[str, Any]:
    """呼叫 /backtest/cal_performance 取得持股績效明細。"""
    base_url = get_backend_base_url()
    url = f"{base_url}/backtest/cal_performance"

    params: Dict[str, Any] = {
        "signal": json.dumps(signal, ensure_ascii=False),
        "entry_sig_date": entry_sig_date,
    }
    if exit_sig_date:
        params["exit_sig_date"] = exit_sig_date

    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def get_market_return(
    start_date: str,
    end_date: str,
) -> Dict[str, Any]:
    """呼叫 /backtest/cal_market_return 取得大盤績效"""
    base_url = get_backend_base_url()
    url = f"{base_url}/backtest/cal_market_return"

    params: Dict[str, Any] = {
        "entry_sig_date": start_date,
        "exit_sig_date": end_date,
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    return response.json()


if __name__ == "__main__":
    print(get_backtest_report("monthly_revenue_growth_roe", '2025-11-21'))