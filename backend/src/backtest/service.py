from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from src.backtest.schemas import (
    StrategyInfo,
    StrategyListResponse,
    HoldingInfo,
    PerformanceMetrics,
    BacktestReportResponse
)
from src.backtest import backtest
from src.backtest.combinations import sim_conditions


class BacktestService:
    """回測服務類"""
    
    # 定義可用的策略
    AVAILABLE_STRATEGIES = {
        "monthly_revenue_growth_roe": {
            "name": "monthly_revenue_growth_roe",
            "description": "穩健營收動能策略: 篩選營收成長>24%、負債比<70%、自由現金流>0、流動比率>100%、EPS>0、ROE>0%的股票，並選取ROE最高的2檔",
            "parameters": {
                "mryoy_threshold": 24,
                "dbr_threshold": 70,
                "fcf_threshold": 0,
                "cr_threshold": 100,
                "eps_threshold": 0,
                "roe_threshold": 0,
                "top_n": 2
            }
        }
    }
    
    def __init__(self, data_instance, end_date: Optional[str] = None):
        """
        初始化回測服務
        
        Args:
            data_instance: 數據實例
            end_date: 結束日期
        """
        self.data = data_instance
        self.end_date = end_date
    
    def get_strategy_list(self) -> List[StrategyInfo]:
        """
        獲取所有可用策略列表
        
        Returns:
            策略資訊列表
        """
        strategies = []
        for strategy_key, strategy_data in self.AVAILABLE_STRATEGIES.items():
            strategies.append(StrategyInfo(
                name=strategy_data["name"],
                description=strategy_data["description"],
                parameters=strategy_data.get("parameters")
            ))
        return strategies
    
    def run_backtest(
        self,
        strategy_name: str,
        end_date: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> BacktestReportResponse:
        """
        執行回測
        
        Args:
            strategy_name: 策略名稱
            end_date: 結束日期
            parameters: 策略參數
            
        Returns:
            回測報告
        """
        # 驗證策略是否存在
        if strategy_name not in self.AVAILABLE_STRATEGIES:
            raise ValueError(f"策略 '{strategy_name}' 不存在")
        
        # 獲取策略配置
        strategy_config = self.AVAILABLE_STRATEGIES[strategy_name]
        strategy_params = parameters or strategy_config.get("parameters", {})
        
        # 設置日期範圍
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        # 根據策略名稱執行相應的策略
        if strategy_name == "monthly_revenue_growth_roe":
            strategy_signal = self._execute_monthly_revenue_growth_roe_strategy(strategy_params, end_date=end_date)
        else:
            raise ValueError(f"策略 '{strategy_name}' 尚未實現")
        
        # 執行回測
        report = backtest.sim(strategy_signal, resample=None, data=self.data)
        
        # 提取報告數據
        performance, current_holdings = self._extract_report_data(report)
        
        return BacktestReportResponse(
            strategy_name=strategy_name,
            strategy_description=strategy_config["description"],
            performance=performance,
            current_holdings=current_holdings,
            message=f"回測完成: 截止日 {end_date}"
        )
    
    def _execute_monthly_revenue_growth_roe_strategy(self, parameters: Dict[str, Any], end_date: Optional[str] = None) -> pd.DataFrame:
        """
        執行穩健營收動能策略
        
        Args:
            parameters: 策略參數
            end_date: 結束日期
        Returns:
            策略信號 DataFrame
        """
        # 提取參數
        mryoy_threshold = parameters.get("mryoy_threshold", 24)
        dbr_threshold = parameters.get("dbr_threshold", 70)
        fcf_threshold = parameters.get("fcf_threshold", 0)
        cr_threshold = parameters.get("cr_threshold", 100)
        eps_threshold = parameters.get("eps_threshold", 0)
        roe_threshold = parameters.get("roe_threshold", 0)
        top_n = parameters.get("top_n", 30)
        
        # 讀取資料
        mryoy = self.data.get("report:mryoy")
        roe = self.data.get("report:roe")
        eps = self.data.get("report:eps")
        dbr = self.data.get("report:dbr")
        fcf = self.data.get("report:fcf")
        cr = self.data.get("report:cr")
        
        # 濾網 1: 基本獲利能力與安全性
        basic_filter = (
            (dbr < dbr_threshold) & 
            (fcf > fcf_threshold) & 
            (cr > cr_threshold) & 
            (eps > eps_threshold) & 
            (roe > roe_threshold)
        )
        
        # 濾網 2: 營收成長優質區間
        mryoy_filter = (mryoy > mryoy_threshold)
        
        # 組合條件
        final_condition = basic_filter & mryoy_filter
        
        # 選股: 在符合條件的股票中，選 ROE 最高的 top_n 檔
        strategy_signal = roe[final_condition].is_largest(top_n)

        # end_date 處理
        if end_date:
            strategy_signal = strategy_signal[strategy_signal.index <= pd.to_datetime(end_date)]
        
        # 選擇每月 10 號的信號
        strategy_signal_monthly = self._select_monthly_10(strategy_signal)
        
        return strategy_signal_monthly
    
    def _select_monthly_10(self, position: pd.DataFrame, skip_monthday=(10, 10)) -> pd.DataFrame:
        """
        選擇每月 10 號（或之前最近的交易日）的信號
        
        Args:
            position: 持倉信號 DataFrame
            skip_monthday: 要跳過的月日（預設 (10, 10) 即 10 月 10 日）
            
        Returns:
            篩選後的信號 DataFrame
        """
        position = position.copy()
        if not isinstance(position.index, pd.DatetimeIndex):
            position.index = pd.to_datetime(position.index)
        
        tz = position.index.tz
        start, end = position.index[0], position.index[-1]
        dates_10 = pd.date_range(start=start, end=end, freq='MS', tz=tz) + pd.DateOffset(days=9)
        
        selected = []
        for d in dates_10:
            t = d
            # 如果目標日期是跳過日期，先往前一天
            if (t.month, t.day) == skip_monthday:
                t = t - pd.Timedelta(days=1)
            
            # 選擇最後一個 <= t 的索引
            candidates = position.index[position.index <= t]
            if len(candidates) == 0:
                continue
            sel = candidates[-1]
            
            # 如果選中的日期是跳過日期，繼續往前找
            while (sel.month, sel.day) == skip_monthday:
                candidates = position.index[position.index < sel]
                if len(candidates) == 0:
                    sel = None
                    break
                sel = candidates[-1]
            
            if sel is not None:
                selected.append(sel)
        
        # 去重並排序
        selected = pd.DatetimeIndex(sorted(dict.fromkeys(selected)))
        result = position.reindex(selected).dropna(how='all')
        
        return result
    
    def _extract_report_data(self, report) -> tuple:
        """
        從回測報告中提取數據
        
        Args:
            report: 回測報告對象
            
        Returns:
            (performance, current_holdings) 元組
        """
        # 獲取績效指標
        performance, recent_trades = report.display()
        performance_dict = performance.to_dict()
        
        # 輔助函數：提取並轉換數值
        def extract_value(val):
            """從格式如 {'': '33.29%'} 或 {'': '1.38'} 的字典中提取數值"""
            if val is None:
                return None
            if isinstance(val, dict):
                # 提取字典中的值
                val = val.get('', val.get(list(val.keys())[0] if val else ''))
            if isinstance(val, str):
                # 移除百分比符號並轉換為浮點數
                val = val.strip().rstrip('%')
                try:
                    return float(val)
                except (ValueError, AttributeError):
                    return None
            return val
        
        performance = PerformanceMetrics(
            annualized_rate_of_return=extract_value(performance_dict.get("annualized_rate_of_return")),
            sharpe=extract_value(performance_dict.get("sharpe")),
            alpha=extract_value(performance_dict.get("alpha")),
            beta=extract_value(performance_dict.get("beta")),
            max_drawdown=extract_value(performance_dict.get("max_drawdown")),
            avg_holdings=extract_value(performance_dict.get("avg_holdings")),
            max_holdings=int(extract_value(performance_dict.get("max_holdings"))) if extract_value(performance_dict.get("max_holdings")) else None,
            win_ratio=extract_value(performance_dict.get("win_ratio")),
        )
        
        # 獲取當前持股
        current_holdings = self._extract_current_holdings(recent_trades)
        
        
        return performance, current_holdings
    
    def _extract_current_holdings(self, report) -> List[HoldingInfo]:
        """從報告中提取當前持股"""
        holdings = []
        close = self.data.get("price:close")

        # 嘗試從報告中獲取最新持股資訊
        for idx, row in report.iterrows():
            exit_date = row.get('exit_date')
            if pd.notna(exit_date):
                continue

            stock_close = close[str(idx)]
            entry_index = row.get('entry_index')
            entry_price = stock_close.iloc[entry_index] if entry_index is not None else None

            holdings.append(HoldingInfo(
                stock_id=str(idx) if isinstance(idx, (str, int)) else None,
                position=float(round(row.get('position'), 4)) if pd.notna(row.get('position')) else None,
                entry_date=str(row.get('entry_date'))[:10] if pd.notna(row.get('entry_date')) else None,
                entry_price=float(entry_price) if entry_price is not None else None,
            ))
        
        return holdings