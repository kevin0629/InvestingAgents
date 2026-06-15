from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from src.backtest.schemas import (
    StrategyInfo,
    HoldingInfo,
    PerformanceMetrics,
    BacktestReportResponse,
    BacktestSimResponse,
    MarketReturnResponse,
)
from src.backtest import backtest
from src.dataframe import CustomDataFrame


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
        },
        "monthly_revenue_growth_roe_pullback": {
            "name": "monthly_revenue_growth_roe_pullback",
            "description": "穩健營收動能策略: 篩選營收成長>20%、負債比<70%、自由現金流>0、流動比率>100%、EPS>0、ROE>0%的股票，並選取ROE最高的20檔，做拉回買的動作",
            "parameters": {
                "mryoy_threshold": 20,
                "dbr_threshold": 70,
                "fcf_threshold": 0,
                "cr_threshold": 100,
                "eps_threshold": 0,
                "roe_threshold": 0,
                "top_n": 20
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
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> BacktestReportResponse:
        """
        執行回測
        
        Args:
            strategy_name: 策略名稱
            start_date: 開始日期
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
        strategy_params = strategy_config.get("parameters", {})
        
        # 設置日期範圍
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        # 根據策略名稱執行相應的策略
        if strategy_name == "monthly_revenue_growth_roe":
            strategy_signal = self._execute_monthly_revenue_growth_roe_strategy(strategy_params, start_date=start_date, end_date=end_date)
        elif strategy_name == "monthly_revenue_growth_roe_pullback":
            strategy_signal = self._execute_monthly_revenue_growth_roe_pullback_strategy(strategy_params, start_date=start_date, end_date=end_date)
        else:
            raise ValueError(f"策略 '{strategy_name}' 尚未實現")
        
        # 執行回測
        report = backtest.sim(strategy_signal, resample=None, data=self.data)
        
        # 提取報告數據
        performance, current_holdings, recent_trades = self._extract_report_data(report)
        previous_period_return = self._calculate_previous_period_return(
            recent_trades=recent_trades,
            end_date=end_date,
        )
        
        return BacktestReportResponse(
            strategy_name=strategy_name,
            strategy_description=strategy_config["description"],
            performance=performance,
            previous_period_return=str(previous_period_return)+"%",
            current_holdings=current_holdings,
            message=f"回測完成: 截止日 {end_date}"
        )
    
    def _execute_monthly_revenue_growth_roe_strategy(self, parameters: Dict[str, Any], start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """
        執行穩健營收動能策略
        
        Args:
            parameters: 策略參數
            start_date: 開始日期
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
        top_n = parameters.get("top_n", 20)
        
        # 讀取資料
        mryoy = self.data.get("report:mryoy")
        roe = self.data.get("report:roe")
        eps = self.data.get("report:eps")
        dbr = self.data.get("report:dbr")
        fcf = self.data.get("report:fcf")
        cr = self.data.get("report:cr")
        close = self.data.get("price:close")
        
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

        # 濾網 3: 確保有價格資料(避免有些會有財報但沒股價的情況)
        price_filter = close.notna()
        
        # 組合條件
        final_condition = basic_filter & mryoy_filter & price_filter
        
        # 選股: 在符合條件的股票中，選 ROE 最高的 top_n 檔
        strategy_signal = roe[final_condition].is_largest(top_n)

        strategy_signal.index = pd.to_datetime(strategy_signal.index)

        # start_date 處理
        if start_date:
            strategy_signal = strategy_signal[strategy_signal.index >= pd.to_datetime(start_date)]

        # end_date 處理
        if end_date:
            strategy_signal = strategy_signal[strategy_signal.index <= pd.to_datetime(end_date)]
        
        # 選擇每月 10 號的信號
        strategy_signal_monthly = self._select_monthly_10(strategy_signal)
        
        return strategy_signal_monthly
    
    def _execute_monthly_revenue_growth_roe_pullback_strategy(self, parameters: Dict[str, Any], start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """
        執行穩健營收動能策略（拉回買）

        Args:
            parameters: 策略參數
            start_date: 開始日期
            end_date: 結束日期
        Returns:
            策略信號 DataFrame
        """
        # 提取參數
        mryoy_threshold = parameters.get("mryoy_threshold", 20)
        dbr_threshold = parameters.get("dbr_threshold", 70)
        fcf_threshold = parameters.get("fcf_threshold", 0)
        cr_threshold = parameters.get("cr_threshold", 100)
        eps_threshold = parameters.get("eps_threshold", 0)
        roe_threshold = parameters.get("roe_threshold", 0)
        top_n = parameters.get("top_n", 20)
        
        # 讀取資料
        mryoy = self.data.get("report:mryoy")
        roe = self.data.get("report:roe")
        eps = self.data.get("report:eps")
        dbr = self.data.get("report:dbr")
        fcf = self.data.get("report:fcf")
        cr = self.data.get("report:cr")
        close = self.data.get("price:close")
        
        ma20 = self.data.indicator("SMA", timeperiod=20)
        ma60 = self.data.indicator("SMA", timeperiod=60)

        basic_filter = (dbr < dbr_threshold) & (fcf > fcf_threshold) & (cr > cr_threshold) & (eps > eps_threshold) & (roe > roe_threshold)
        mryoy_filter = (mryoy > mryoy_threshold)
        price_filter = close.notna()
        daily_pullback = (close.shift(1) < ma20.shift(1)) & (close > ma20) & (close > close.shift(1))
        recent_pullback = daily_pullback.rolling(window=10).max() > 0
        trend_filter = (close > ma60) & (ma60.diff() > 0) & (close > ma20)

        final_condition = basic_filter & recent_pullback & trend_filter & price_filter & mryoy_filter
        
        # 選股: 在符合條件的股票中，選 ROE 最高的 top_n 檔
        strategy_signal = roe[final_condition].is_largest(top_n)

        strategy_signal.index = pd.to_datetime(strategy_signal.index)

        # start_date 處理
        if start_date:
            strategy_signal = strategy_signal[strategy_signal.index >= pd.to_datetime(start_date)]

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
        # Use month-starts then add 9 days to get the 10th of each month.
        # Start from the first day of the start-month so that if `start` is on the
        # 10th (or later) the month's 10th is still considered and later filtered.
        range_start = start.replace(day=1)
        dates_10 = pd.date_range(start=range_start, end=end, freq='MS', tz=tz) + pd.DateOffset(days=9)
        
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
        performance = self._build_performance_metrics(performance)
        
        # 獲取當前持股
        current_holdings = self._extract_current_holdings(recent_trades)
        
        
        return performance, current_holdings, recent_trades

    def _calculate_previous_period_return(
        self,
        recent_trades: pd.DataFrame,
        end_date: str,
    ) -> float:
        """計算上一期加權報酬：sum(position * return)。"""

        entry_sig_dates = pd.to_datetime(recent_trades["entry_sig_date"], errors="coerce")
        exit_sig_dates = pd.to_datetime(recent_trades["exit_sig_date"], errors="coerce")

        mask1 = (exit_sig_dates.isna()) | (exit_sig_dates >= end_date)
        previous_period_mask = mask1 & (entry_sig_dates < end_date)

        positions = pd.to_numeric(recent_trades["position"], errors="coerce").fillna(0.0)
        returns = pd.to_numeric(recent_trades["return"], errors="coerce").fillna(0.0)

        weighted_returns = positions * returns
        sum  = weighted_returns[previous_period_mask].sum()

        return round(sum * 100, 4)

    @staticmethod
    def _extract_value(val):
        """從格式如 {'': '33.29%'} 或 {'': '1.38'} 的字典中提取數值"""
        if val is None:
            return None
        if isinstance(val, dict):
            val = val.get("", val.get(list(val.keys())[0] if val else ""))
        if isinstance(val, str):
            val = val.strip().rstrip("%")
            try:
                return float(val)
            except (ValueError, AttributeError):
                return None
        return val

    def _build_performance_metrics(self, performance_df: pd.DataFrame) -> PerformanceMetrics:
        performance_dict = performance_df.to_dict()

        max_holdings_value = self._extract_value(performance_dict.get("max_holdings"))

        return PerformanceMetrics(
            annualized_rate_of_return=self._extract_value(
                performance_dict.get("annualized_rate_of_return")
            ),
            sharpe=self._extract_value(performance_dict.get("sharpe")),
            alpha=self._extract_value(performance_dict.get("alpha")),
            beta=self._extract_value(performance_dict.get("beta")),
            max_drawdown=self._extract_value(performance_dict.get("max_drawdown")),
            avg_holdings=self._extract_value(performance_dict.get("avg_holdings")),
            max_holdings=int(max_holdings_value) if max_holdings_value is not None else None,
            win_ratio=self._extract_value(performance_dict.get("win_ratio")),
        )

    @staticmethod
    def _normalize_datetime(value):
        if pd.isna(value):
            return None
        if isinstance(value, (pd.Timestamp, datetime)):
            return value.strftime("%Y-%m-%d")
        return str(value)[:10]

    @staticmethod
    def _normalize_number(value, cast_type=float):
        if pd.isna(value):
            return None
        try:
            return cast_type(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _get_next_trading_value(series: pd.Series, signal_date: str) -> tuple:
        """取 signal_date 之後第一個交易日的價格。"""
        clean_series = series.dropna().copy()
        if clean_series.empty:
            raise ValueError("找不到可用的大盤價格資料")

        clean_series.index = pd.to_datetime(clean_series.index, errors="coerce")
        clean_series = clean_series[~clean_series.index.isna()].sort_index()
        if clean_series.empty:
            raise ValueError("大盤價格索引格式錯誤")

        signal_dt = pd.to_datetime(signal_date)
        target_index = clean_series.index.searchsorted(signal_dt, side="right")
        if target_index >= len(clean_series.index):
            # 若沒有 strictly after 的交易日，fallback 去找 <= signal_date 的最近交易日
            prior_idx = clean_series.index[clean_series.index <= signal_dt]
            if len(prior_idx) == 0:
                raise ValueError(f'signal_date={signal_date} 後無可用交易日，且之前也無可用交易日')

            trade_dt = prior_idx[-1]
            trade_price = float(clean_series.loc[trade_dt])
            return trade_dt.strftime("%Y-%m-%d"), trade_price

        trade_dt = clean_series.index[target_index]
        trade_price = float(clean_series.iloc[target_index])
        return trade_dt.strftime("%Y-%m-%d"), trade_price

    def calculate_market_return(
        self,
        entry_sig_date: Optional[str] = None,
        exit_sig_date: Optional[str] = None,
    ) -> MarketReturnResponse:
        """以訊號日期後第一個交易日的大盤價格計算報酬。"""
        if not entry_sig_date:
            raise ValueError("entry_sig_date 不可為空")

        if not exit_sig_date:
            raise ValueError("exit_sig_date 不可為空")

        entry_dt = pd.to_datetime(entry_sig_date)
        exit_dt = pd.to_datetime(exit_sig_date)
        if exit_dt <= entry_dt:
            raise ValueError("exit_sig_date 必須晚於 entry_sig_date")

        market_df = self.data.get("adjustedtaiex:close")
        if market_df is None or market_df.empty:
            market_df = self.data.get("taiex:close")
        if market_df is None or market_df.empty:
            raise ValueError("找不到可用的大盤資料")

        if isinstance(market_df, pd.Series):
            market_series = market_df
        elif "close" in market_df.columns:
            market_series = market_df["close"]
        elif market_df.shape[1] >= 1:
            market_series = market_df.iloc[:, 0]
        else:
            raise ValueError("大盤資料欄位不足")

        entry_trade_date, entry_price = self._get_next_trading_value(market_series, entry_sig_date)
        exit_trade_date, exit_price = self._get_next_trading_value(market_series, exit_sig_date)

        if entry_price == 0:
            raise ValueError("進場價格不可為 0")

        market_return = float((exit_price - entry_price) / entry_price)
        market_return = market_return - 0.00585  # 扣除交易成本: 交易稅 0.3% + 交易手續費 0.285%
        market_return = round(market_return * 100, 4)

        return MarketReturnResponse(
            entry_sig_date=entry_sig_date,
            exit_sig_date=exit_sig_date,
            entry_trade_date=entry_trade_date,
            exit_trade_date=exit_trade_date,
            entry_price=entry_price,
            exit_price=exit_price,
            market_return=str(market_return)+"%",
            message="回測完成: 大盤績效模擬",
        )

    def _get_trade_price_by_index(self, stock_id: str, trade_index: Any) -> Optional[float]:
        """依照回測主索引（price:close）抓取該股票交易價格。"""
        if trade_index is None or pd.isna(trade_index):
            return None

        try:
            idx = int(trade_index)
        except (TypeError, ValueError):
            return None

        if idx < 0:
            return None

        close_df = self.data.get("price:close")
        if close_df is None or close_df.empty:
            return None

        stock_col = str(stock_id)
        if stock_col not in close_df.columns:
            return None

        if idx >= len(close_df.index):
            return None

        price = close_df[stock_col].iloc[idx]
        if pd.isna(price):
            return None

        return float(price)

    def backtest_sim(
        self,
        signal: Dict[str, Any],
        entry_sig_date: Optional[str] = None,
        exit_sig_date: Optional[str] = None,
    ) -> BacktestSimResponse:
        """以自定義持股與時間點執行回測，回傳整體績效與持股績效明細。"""
        if not signal:
            raise ValueError("signal 不可為空")

        if not entry_sig_date:
            raise ValueError("entry_sig_date 不可為空")

        entry_dt = pd.to_datetime(entry_sig_date)
        exit_dt = pd.to_datetime(exit_sig_date) if exit_sig_date else None

        if exit_dt is not None and exit_dt <= entry_dt:
            raise ValueError("exit_sig_date 必須晚於 entry_sig_date")

        stock_ids = list(signal.keys())
        entry_weights = [float(signal[sid]) for sid in stock_ids]

        rows = [
            {
                "company_symbol": entry_dt,
                **{sid: w for sid, w in zip(stock_ids, entry_weights)},
            }
        ]

        # backtest.sim 需要至少兩個日期點，因此即便未提供 exit_sig_date 也建立第二筆訊號。
        if exit_dt is None:
            exit_dt = entry_dt + timedelta(days=30)

        rows.append(
            {
                "company_symbol": exit_dt,
                **{sid: 0.0 for sid in stock_ids},
            }
        )

        df = pd.DataFrame(rows)
        df = df.set_index("company_symbol")
        df.index = pd.to_datetime(df.index)
        df = CustomDataFrame(df)

        report = backtest.sim(df, resample=None, data=self.data)
        performance_df, pivot_table = report.display()

        performance = self._build_performance_metrics(performance_df)

        expected_columns = [
            "entry_date",
            "exit_date",
            "entry_sig_date",
            "exit_sig_date",
            "position",
            "period",
            "entry_index",
            "exit_index",
            "return",
            "mae",
            "gmfe",
            "bmfe",
            "mdd",
            "pdays",
            "weight",
            "next_weights",
        ]

        holdings_performance: List[Dict[str, Any]] = []
        pivot_table = pivot_table.copy()
        for col in expected_columns:
            if col not in pivot_table.columns:
                pivot_table[col] = np.nan

        for stock_id, row in pivot_table[expected_columns].iterrows():
            holdings_performance.append(
                {
                    "stock_id": str(stock_id),
                    "entry_date": self._normalize_datetime(row.get("entry_date")),
                    "exit_date": self._normalize_datetime(row.get("exit_date")),
                    "entry_sig_date": self._normalize_datetime(row.get("entry_sig_date")),
                    "exit_sig_date": self._normalize_datetime(row.get("exit_sig_date")),
                    "position": self._normalize_number(row.get("position"), float),
                    "period": self._normalize_number(row.get("period"), int),
                    "entry_price": self._get_trade_price_by_index(str(stock_id), row.get("entry_index")),
                    "exit_price": self._get_trade_price_by_index(str(stock_id), row.get("exit_index")),
                    "return": self._normalize_number(row.get("return"), float),
                    "mae": self._normalize_number(row.get("mae"), float),
                    "gmfe": self._normalize_number(row.get("gmfe"), float),
                    "bmfe": self._normalize_number(row.get("bmfe"), float),
                    "mdd": self._normalize_number(row.get("mdd"), float),
                    "pdays": self._normalize_number(row.get("pdays"), float),
                    "weight": self._normalize_number(row.get("weight"), float),
                    "next_weights": self._normalize_number(row.get("next_weights"), float),
                }
            )

        return BacktestSimResponse(
            performance=performance,
            holdings_performance=holdings_performance,
            message="回測完成: 自定義持股模擬",
        )
    
    def _extract_current_holdings(self, report) -> List[HoldingInfo]:
        """從報告中提取當前持股"""
        holdings = []
        print(report["exit_sig_date"])

        # 嘗試從報告中獲取最新持股資訊
        for idx, row in report[report['exit_sig_date'].isna()].iterrows():
            holdings.append(HoldingInfo(
                stock_id=str(idx) if isinstance(idx, (str, int)) else "",
                position=float(round(row.get('position'), 4)) if pd.notna(row.get('position')) else None,
                entry_sig_date=str(row.get('entry_sig_date'))[:10] if pd.notna(row.get('entry_sig_date')) else None,
            ))
        
        return holdings