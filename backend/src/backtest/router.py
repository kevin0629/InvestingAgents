from fastapi import APIRouter, HTTPException, Query
import json
from src.backtest.schemas import (
    BacktestReportResponse,
    StrategyListResponse,
    StrategyInfo,
    BacktestSimResponse,
    MarketReturnResponse,
)
from src.backtest.service import BacktestService
from typing import Optional, Dict, Any
from src.utils import get_data_instance

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.get("/report", response_model=BacktestReportResponse)
async def get_backtest_report(
    strategy_name: str = Query(..., description="策略名稱"),
    start_date: Optional[str] = Query(None, description="回測開始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="回測結束日期 (YYYY-MM-DD)"),
):
    """
    以指定的策略做回測，回傳策略績效報告、這一期持股、換股的清單
    
    - **strategy_name**: 策略名稱 (monthly_revenue_growth_roe, monthly_revenue_growth_roe_pullback)
    - **start_date**: 回測開始日期，格式: YYYY-MM-DD，不提供則為資料最早日期
    - **end_date**: 回測結束日期，格式: YYYY-MM-DD，不提供則為今天
    
    回傳內容包括：
    - 策略績效指標（年化報酬率、夏普比率、Alpha、Beta、最大回撤等）
    - 當前持股列表（股票代碼、名稱、股數）
    - 近期交易記錄（進出場日期、報酬率、最大不利偏移等詳細交易資訊）
    """
    try:
        data = get_data_instance()
        service = BacktestService(data)
        
        # 執行回測
        report = service.run_backtest(
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
        )
        
        return report
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(f"Error in get_backtest_report: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/strategy", response_model=StrategyListResponse)
async def get_strategy():
    """
    回傳所有已知的策略與其描述
    
    回傳所有可用的量化策略列表，包括：
    - 策略名稱
    - 策略描述
    - 預設參數
    """
    try:
        data = get_data_instance()
        service = BacktestService(data)
        strategies = service.get_strategy_list()
        
        return StrategyListResponse(strategies=strategies)
    
    except Exception as e:
        print(f"Error in get_strategy: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    

@router.get("/cal_performance", response_model=BacktestSimResponse)
async def calculate_performance(
    signal: str = Query(..., description="策略信號(JSON字串)，例如 {\"2330\": 0.5, \"2317\": 0.2}"),
    entry_sig_date: Optional[str] = Query(None, description="訊號開始日期 (YYYY-MM-DD)"),
    exit_sig_date: Optional[str] = Query(None, description="訊號結束日期 (YYYY-MM-DD)"),
):
    """
    以指定的股票和部位做回測，回傳策略績效報告
    
    - signal: 策略信號，格式為 { "2330": 0.5, "2317": 0.2 }，其中 key 是股票代碼，value 是部位
    - entry_sig_date: 訊號開始日期 (YYYY-MM-DD)
    - exit_sig_date: 訊號結束日期 (YYYY-MM-DD)
    
    回傳內容包括：
    - 策略績效指標（年化報酬率、夏普比率、Alpha、Beta、最大回撤等）
    - 當前持股列表（股票代碼、名稱、股數）
    - 交易記錄（進出場日期、報酬率、最大不利偏移等詳細交易資訊）
    """
    try:
        try:
            parsed_signal = json.loads(signal)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="signal 必須是合法 JSON 字串")

        if not isinstance(parsed_signal, dict):
            raise HTTPException(status_code=400, detail="signal 必須是 key 為股票代碼、value 為部位的 JSON 物件")

        normalized_signal = {}
        for stock_id, weight in parsed_signal.items():
            try:
                normalized_signal[str(stock_id)] = float(weight)
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail=f"signal 的部位必須是數字: {stock_id}")

        data = get_data_instance()
        service = BacktestService(data)
        
        # 執行回測
        report = service.backtest_sim(
            signal=normalized_signal,
            entry_sig_date=entry_sig_date,
            exit_sig_date=exit_sig_date
        )
        
        return report
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(f"Error in calculate_performance: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/cal_market_return", response_model=MarketReturnResponse)
async def calculate_market_return(
    entry_sig_date: Optional[str] = Query(None, description="訊號開始日期 (YYYY-MM-DD)"),
    exit_sig_date: Optional[str] = Query(None, description="訊號結束日期 (YYYY-MM-DD)"),
):
    """以訊號日期後的下一個交易日計算大盤報酬。"""
    try:
        data = get_data_instance()
        service = BacktestService(data)

        report = service.calculate_market_return(
            entry_sig_date=entry_sig_date,
            exit_sig_date=exit_sig_date,
        )

        return report

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(f"Error in calculate_market_return: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")



