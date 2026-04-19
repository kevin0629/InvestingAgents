import sys
import warnings
import datetime
import numpy as np
import pandas as pd
from typing import Union, Optional
from pandas.tseries.offsets import DateOffset
from pandas.tseries.frequencies import to_offset
import plotly.graph_objs as go
from plotly.subplots import make_subplots

from src.backtest import report
from src.get_data import Data
from core.backtest_core import backtest_, get_trade_stocks
from core.backtest_core import mae_mfe as maemfe

def warning_resample(resample):

  if '+' not in resample and '-' not in resample:
      return

  if '-' in resample and not resample.split('-')[-1].isdigit():
      return

  if '+' in resample:
      r, o = resample.split('+')
  elif '-' in resample:
      r, o = resample.split('-')

  warnings.warn(f"The argument sim(..., resample = '{resample}') will no longer support after 0.1.37.dev1.\n"
                f"please use sim(..., resample='{r}', offset='{o}d')", DeprecationWarning)

def calc_essential_price(price, dates):

    dt = min(price.index.values[1:] - price.index.values[:-1])

    indexer = price.index.get_indexer(dates + dt)

    valid_idx = np.where(indexer == -1, np.searchsorted(price.index, dates, side='right'), indexer)
    valid_idx = np.where(valid_idx >= len(price), len(price) - 1, valid_idx)

    return price.iloc[valid_idx]

def arguments(price, high, low, open_, position, resample_dates=None, rolling_dates=None, fast_mode=False):

    resample_dates = price.index if resample_dates is None else resample_dates
    rolling_dates = price.index if rolling_dates is None else rolling_dates
    position = position.astype(float).fillna(0)

    if fast_mode:
        date_index = pd.to_datetime(resample_dates)
        position = position.reindex(date_index, method='ffill')
        price = calc_essential_price(price, date_index)
        high = calc_essential_price(high, date_index)
        low = calc_essential_price(low, date_index)
        open_ = calc_essential_price(open_, date_index)
    
    resample_dates = pd.Series(resample_dates).view(np.int64).values
    rolling_dates = pd.Series(rolling_dates).view(np.int64).values

    return [price.values,
            high.values,
            low.values,
            open_.values,
            price.index.view(np.int64),
            price.columns.astype(str).values,
            position.values,
            position.index.view(np.int64),
            position.columns.astype(str).values,
            resample_dates,
            rolling_dates
            ]

def rebase(prices, value=100):
    """
    Rebase all series to a given intial value.
    This makes comparing/plotting different series
    together easier.
    Args:
        * prices: Expects a price series
        * value (number): starting value for all series.
    """
    if isinstance(prices, pd.DataFrame):
        return prices.div(prices.iloc[0], axis=1) * value
    return prices / prices.iloc[0] * value


def _get_market_close_series(data: Data) -> pd.Series:
    """Load adjusted TAIEX close series (fallback to TAIEX close)."""
    market_df = data.get('adjustedtaiex:close')

    if isinstance(market_df, pd.Series):
        market_series = market_df
    elif 'close' in market_df.columns:
        market_series = market_df['close']

    market_series = market_series.dropna().copy()
    market_series.index = pd.to_datetime(market_series.index, errors='coerce')
    market_series = market_series[~market_series.index.isna()].sort_index()

    return market_series


def _get_next_trading_value(series: pd.Series, signal_date: Union[str, pd.Timestamp]) -> tuple:
    """Get the first trading day/value strictly after signal_date."""
    clean_series = series.dropna().copy()

    clean_series.index = pd.to_datetime(clean_series.index, errors='coerce')
    clean_series = clean_series[~clean_series.index.isna()].sort_index()

    signal_dt = pd.to_datetime(signal_date)
    target_index = clean_series.index.searchsorted(signal_dt, side='right')
    if target_index >= len(clean_series.index):
        raise ValueError(f'signal_date={signal_date} 後無可用交易日')

    trade_dt = clean_series.index[target_index]
    trade_price = float(clean_series.iloc[target_index])
    return trade_dt, trade_price


def _year_frac(start: pd.Timestamp, end: pd.Timestamp) -> float:
    if start > end:
        raise ValueError('start cannot be larger than end')
    return (end - start).total_seconds() / 31557600


def _calc_drawdown(price_series: pd.Series) -> pd.Series:
    drawdown = price_series.copy()
    drawdown[np.isnan(drawdown)] = -np.inf
    roll_max = np.maximum.accumulate(drawdown)
    return drawdown / roll_max - 1.0


def _calc_sharpe_from_prices(price_series: pd.Series, nperiods: int = 252) -> float:
    daily_returns = price_series.pct_change().dropna()
    if len(daily_returns) < 2:
        return 0.0

    std = float(np.std(daily_returns, ddof=1))
    if std <= 0:
        return 0.0

    sharpe_ratio = float(daily_returns.mean()) / std * np.sqrt(nperiods)
    return round(sharpe_ratio, 2)


def calc_adjusted_taiex_interval_metrics(entry_sig_date: Union[str, pd.Timestamp],
                                         exit_sig_date: Union[str, pd.Timestamp],
                                         data: Optional[Data] = None) -> dict:
    """
    計算指定區間的 adjusted_taiex 年化報酬、最大回撤(MDD)、Sharpe。

    Args:
        entry_sig_date: 訊號進場日期，會取其後第一個交易日。
        exit_sig_date: 訊號出場日期，會取其後第一個交易日。
        data: 可選 Data 實例；未提供時自動建立。

    Returns:
        dict: {
            'entry_sig_date': str,
            'exit_sig_date': str,
            'entry_trade_date': str,
            'exit_trade_date': str,
            'annualized_return': float,
            'mdd': float,
            'sharpe': float,
            'annualized_return_pct': str,
            'mdd_pct': str
        }
    """
    if entry_sig_date is None:
        raise ValueError('entry_sig_date 不可為空')
    if exit_sig_date is None:
        raise ValueError('exit_sig_date 不可為空')

    entry_dt = pd.to_datetime(entry_sig_date)
    exit_dt = pd.to_datetime(exit_sig_date)
    if exit_dt <= entry_dt:
        raise ValueError('exit_sig_date 必須晚於 entry_sig_date')

    data = data if isinstance(data, Data) else Data()
    market_series = _get_market_close_series(data)

    entry_trade_dt, _ = _get_next_trading_value(market_series, entry_sig_date)
    exit_trade_dt, _ = _get_next_trading_value(market_series, exit_sig_date)

    period_prices = market_series.loc[(market_series.index >= entry_trade_dt) &
                                      (market_series.index <= exit_trade_dt)]
    if len(period_prices) < 2:
        raise ValueError('指定區間交易日不足，無法計算績效指標')

    start_price = float(period_prices.iloc[0])
    end_price = float(period_prices.iloc[-1])
    if start_price == 0:
        raise ValueError('區間起始價格不可為 0')

    yf = _year_frac(period_prices.index[0], period_prices.index[-1])
    if yf <= 0:
        raise ValueError('指定區間長度無效，無法計算年化報酬')

    annualized_return = (end_price / start_price) ** (1 / yf) - 1
    mdd = float(_calc_drawdown(period_prices).min())
    sharpe = _calc_sharpe_from_prices(period_prices, nperiods=252)

    return {
        'entry_trade_date': entry_trade_dt.strftime('%Y-%m-%d'),
        'exit_trade_date': exit_trade_dt.strftime('%Y-%m-%d'),
        'annualized_return': f"{round(annualized_return, 4)*100:.2f}%",
        'mdd': f"{round(mdd, 4)*100:.2f}%",
        'sharpe': f"{round(sharpe, 2)}",
    }

def sim(position: Union[pd.DataFrame, pd.Series],
        resample:Union[str, None]=None, resample_offset:Union[str, None] = None,
        position_limit:float=1, fee_ratio:float=1.425/1000,
        tax_ratio: float=3/1000, stop_loss: Union[float, None]=None,
        
        # 跟rooling相關參數
        rolling_ratio:float=1.0, rolling_freq:Union[str, None]=None,
        rolling_take_profit: Union[float, None]=None, rolling_stop_loss:Union[float, None]=None, 
        profit_rolling_ratio:float=1.0, loss_rolling_ratio:float=1.0,

        take_profit: Union[float, None]=None, trail_stop: Union[float, None]=None, touched_exit: bool=False,
        retain_cost_when_rebalance: bool=False, stop_trading_next_period: bool=True, live_performance_start:Union[str, None]=None,
        mae_mfe_window:int=0, mae_mfe_window_step:int=1, fast_mode=False, data=None):


     # check type of position
    if not isinstance(position.index, pd.DatetimeIndex):
        raise TypeError("Expected the dataframe to have a DatetimeIndex")
    
    #########
    #測試用的#
    #########
    # price = pd.read_csv('../Data/verify_rolling/stock_price.csv').set_index('date').astype('float64')


    if isinstance(data, Data):
        price = data.get('price:close')
    else:
        data=Data()
        price = data.get('price:close')

    high = price
    low = price
    open_ = price
    if touched_exit:
        high = data.get('price:high').reindex_like(price)
        low =data.get('price:low').reindex_like(price)
        open_ = data.get('price:open').reindex_like(price) 

    if not isinstance(price.index[0], pd.DatetimeIndex):
        price.index = pd.to_datetime(price.index)
        high.index = pd.to_datetime(high.index)
        low.index = pd.to_datetime(low.index)
        open_.index = pd.to_datetime(open_.index)

    assert len(position.shape) >= 2
    # delta_time_rebalance = position.index[-1] - position.index[-3]

    if len(position.index) >= 3:
        delta_time_rebalance = position.index[-1] - position.index[-3]
    elif len(position.index) == 2:
        delta_time_rebalance = position.index[-1] - position.index[0]
    else:
        raise ValueError("`position` needs at least 2 dates for backtesting")

    backtest_to_end = position.index[-1] + \
        delta_time_rebalance > price.index[-1]

    tz = position.index.tz
    now = datetime.datetime.now(tz=tz)

    position = position[(position.index <= price.index[-1]) | (position.index <= now)]
    backtest_end_date = price.index[-1] if backtest_to_end else position.index[-1]

    # resample dates
    dates = None
    next_trading_date = position.index[-1]
    if isinstance(resample, str):

        warning_resample(resample)

        # add additional day offset
        offset_days = 0
        if '+' in resample:
            offset_days = int(resample.split('+')[-1])
            resample = resample.split('+')[0]
        if '-' in resample and resample.split('-')[-1].isdigit():
            offset_days = -int(resample.split('-')[-1])
            resample = resample.split('-')[0]

        # generate rebalance dates
        alldates = pd.date_range(
            position.index[0], 
            position.index[-1] + datetime.timedelta(days=720), 
            freq=resample, tz=tz)

        alldates += DateOffset(days=offset_days)

        if resample_offset is not None:
            alldates += to_offset(resample_offset)

        dates = [d for d in alldates if position.index[0]
                 <= d and d <= position.index[-1]]

        # calculate the latest trading date
        next_trading_date = min(
           set(alldates) - set(dates))

        if dates[-1] != position.index[-1]:
            dates += [next_trading_date]

    if rolling_freq is None and resample is not None:
        rolling_freq = resample

    # rolling dates
    rolling_dates = None
    next_rolling_date = position.index[-1]
    if isinstance(rolling_freq, str):

        warning_resample(rolling_freq)

        # add additional day offset
        offset_days = 0
        if '+' in rolling_freq:
            offset_days = int(rolling_freq.split('+')[-1])
            rolling_freq = rolling_freq.split('+')[0]
        if '-' in rolling_freq and rolling_freq.split('-')[-1].isdigit():
            offset_days = -int(resample.split('-')[-1])
            rolling_freq = rolling_freq.split('-')[0]

        # generate rebalance dates
        alldates = pd.date_range(
            position.index[0], 
            position.index[-1] + datetime.timedelta(days=720), 
            freq=rolling_freq, tz=tz)
        
        rolling_dates = [d for d in alldates if position.index[0]
                 <= d and d <= position.index[-1]]

        # calculate the latest trading date
        next_rolling_date = min(
           set(alldates) - set(rolling_dates))

        if rolling_dates[-1] != position.index[-1]:
            rolling_dates += [next_rolling_date]

    if rolling_take_profit is None or rolling_take_profit == 0:
        rolling_take_profit = np.inf

    if rolling_stop_loss is None or rolling_stop_loss == 0:
        rolling_stop_loss = -np.inf

    if stop_loss is None or stop_loss == 0:
        stop_loss = 1

    if take_profit is None or take_profit == 0:
        take_profit = np.inf

    if trail_stop is None or trail_stop == 0:
        trail_stop = np.inf

    if dates is not None:
        position = position.reindex(dates, method='ffill')

    args = arguments(price, high, low, open_, position, dates, rolling_dates, fast_mode=fast_mode)

    creturn_value = backtest_(*args,
                              fee_ratio=fee_ratio, tax_ratio=tax_ratio, 
                              rolling_ratio=rolling_ratio,profit_rolling_ratio=profit_rolling_ratio,
                              loss_rolling_ratio=loss_rolling_ratio,rolling_take_profit=rolling_take_profit,
                              rolling_stop_loss=rolling_stop_loss,
                              stop_loss=stop_loss, take_profit=take_profit, trail_stop=trail_stop,
                              touched_exit=touched_exit, position_limit=position_limit,
                              retain_cost_when_rebalance=retain_cost_when_rebalance,
                              stop_trading_next_period=stop_trading_next_period,
                              mae_mfe_window=mae_mfe_window, mae_mfe_window_step=mae_mfe_window_step)
    
    total_weight = position.abs().sum(axis=1)

    position = position.div(total_weight.where(total_weight!=0, np.nan), axis=0).fillna(0)\
                       .clip(-abs(position_limit), abs(position_limit))
    
    creturn_dates = dates if dates and fast_mode else price.index

    creturn = (pd.Series(creturn_value, creturn_dates)
                # remove the begining of creturn since there is no pct change
                .pipe(lambda df: df[(df != 1).cumsum().shift(-1, fill_value=1) != 0])
                # remove the tail of creturn for verification
                .loc[:backtest_end_date]
                # replace creturn to 1 if creturn is None
                .pipe(lambda df: df if len(df) != 0 else pd.Series(1, position.index)))
    
    position = position.loc[creturn.index[0]:]

    price_index = args[4]
    position_columns = args[8]
    trades, operation_and_weight = get_trade_stocks(position_columns, 
                                                    price_index, touched_exit=touched_exit)

    ####################################
    # refine mae mfe dataframe
    ####################################
    def refine_mae_mfe():
        if len(maemfe.mae_mfe) == 0:
            return pd.DataFrame()

        m = pd.DataFrame(maemfe.mae_mfe)
        nsets = int((m.shape[1]-1) / 6)

        metrics = ['mae', 'gmfe', 'bmfe', 'mdd', 'pdays', 'return']

        tuples = sum([[(n, metric) if n == 'exit' else (n * mae_mfe_window_step, metric)
                       for metric in metrics] for n in list(range(nsets)) + ['exit']], [])

        m.columns = pd.MultiIndex.from_tuples(
            tuples, names=["window", "metric"])
        m.index.name = 'trade_index'
        m[m == -1] = np.nan

        exit = m.exit.copy()

        if touched_exit and len(m) > 0 and 'exit' in m.columns:
            m['exit'] = (exit
                .assign(gmfe=exit.gmfe.clip(-abs(stop_loss), abs(take_profit)))
                .assign(bmfe=exit.bmfe.clip(-abs(stop_loss), abs(take_profit)))
                .assign(mae=exit.mae.clip(-abs(stop_loss), abs(take_profit)))
                .assign(mdd=exit.mdd.clip(-abs(stop_loss), abs(take_profit))))

        return m
    
    m = refine_mae_mfe()

     ####################################
    # refine trades dataframe
    ####################################
    def convert_datetime_series(df):
        cols = ['entry_date', 'exit_date', 'entry_sig_date', 'exit_sig_date']
        df[cols] = df[cols].apply(lambda s: pd.to_datetime(s).dt.tz_localize(tz))
        return df

    def assign_exit_nat(df):
        cols = ['exit_date', 'exit_sig_date']
        df[cols] = df[cols].loc[df.exit_index != -1]
        return df

    trades = (pd.DataFrame(trades, 
                           columns=['stock_id', 'entry_date', 'exit_date',
                                    'entry_sig_date', 'exit_sig_date', 'position', 
                                    'period', 'entry_index', 'exit_index'])
              .rename_axis('trade_index')
              .pipe(convert_datetime_series)
              .pipe(assign_exit_nat)
              )

    def compute_trade_return(row):
        stock_id = str(row.get('stock_id'))
        if stock_id not in price.columns:
            return np.nan

        try:
            entry_idx = int(row.get('entry_index'))
        except (TypeError, ValueError):
            return np.nan

        if entry_idx < 0 or entry_idx >= len(price.index):
            return np.nan

        try:
            exit_idx = int(row.get('exit_index'))
        except (TypeError, ValueError):
            exit_idx = -1

        if exit_idx < 0:
            end_pos = int(price.index.searchsorted(backtest_end_date, side='right') - 1)
            exit_idx = min(max(end_pos, 0), len(price.index) - 1)
        elif exit_idx >= len(price.index):
            exit_idx = len(price.index) - 1

        entry_price = price.iloc[entry_idx].get(stock_id)
        exit_price = price.iloc[exit_idx].get(stock_id)

        if pd.isna(entry_price) or pd.isna(exit_price) or float(entry_price) == 0:
            return np.nan

        gross_return = float(exit_price) / float(entry_price) - 1.0
        return gross_return - 2 * fee_ratio - tax_ratio
    
    if len(trades) != 0:
        trades = trades.assign(**{'return': trades.apply(compute_trade_return, axis=1)})

    if touched_exit:
        trades['return'] = trades['return'].clip(-abs(stop_loss), abs(take_profit))

    # trades = trades.drop(['entry_index', 'exit_index'], axis=1)

    
    daily_creturn = rebase(creturn.resample('1d').last().dropna().ffill())
    
    stock_data = pd.DataFrame(index = creturn.index)
    stock_data['portfolio_returns'] = daily_creturn
    stock_data['cum_returns'] = creturn
    stock_data['company_count'] = (position != 0).sum(axis=1)

    r = report.Report(stock_data, position, data)
    r.mae_mfe = m
    r.trades = trades
    
    # calculate weights
    if len(operation_and_weight['weights']) != 0:
        r.weights = pd.Series(operation_and_weight['weights'])
        r.weights.index = r.position.columns[r.weights.index]
    else:
        r.weights = pd.Series(dtype='float64')


    # calculate next weights
    if len(operation_and_weight['next_weights']) != 0:
        r.next_weights = pd.Series(operation_and_weight['next_weights'])
        r.next_weights.index = r.position.columns[r.next_weights.index]
    else:
        r.next_weights = pd.Series(dtype='float64')


    # calculate actions    
    if len(operation_and_weight['actions']) != 0:
        # find selling and buying stocks
        r.actions = pd.Series(operation_and_weight['actions'])
        r.actions.index = r.position.columns[r.actions.index]
    else:
        r.actions = pd.Series(dtype=object)

    if len(r.actions) != 0:

        actions = r.actions

        sell_sids = actions[actions == 'exit'].index
        sell_instant_sids = actions[(actions == 'sl') | (actions == 'tp')].index
        buy_sids = actions[actions == 'enter'].index

        if len(trades):
            # check if the sell stocks are in the current position
            # assert len(set(sell_sids) - set(trades.stock_id[trades.exit_sig_date.isnull()])) == 0

            # fill exit_sig_date and exit_date
            temp = trades.loc[trades.stock_id.isin(sell_sids), 'exit_sig_date'].fillna(r.position.index[-1])
            trades.loc[trades.stock_id.isin(sell_sids), 'exit_sig_date'] = temp

            temp = trades.loc[trades.stock_id.isin(sell_instant_sids), 'exit_sig_date'].fillna(price.index[-1])
            trades.loc[trades.stock_id.isin(sell_instant_sids), 'exit_sig_date'] = temp

            r.trades = pd.concat([r.trades, pd.DataFrame({
              'stock_id': buy_sids,
              'entry_date': pd.NaT,
              'entry_sig_date': r.position.index[-1],
              'exit_date': pd.NaT,
              'exit_sig_date': pd.NaT,
            })], ignore_index=True)

            r.trades['exit_sig_date'] = pd.to_datetime(r.trades.exit_sig_date)

    if len(trades) != 0:
        trades = r.trades
        mae_mfe = r.mae_mfe
        exit_mae_mfe = mae_mfe['exit'].copy()
        exit_mae_mfe = exit_mae_mfe.drop(columns=['return'])
        r.trades = pd.concat([trades, exit_mae_mfe], axis=1)
        r.trades.index.name = 'trade_index'

        # calculate r.current_trades
        # find trade without end or end today
        maxday = max(r.trades.entry_sig_date.max(), r.trades.exit_sig_date.max())
        latest_entry_day = r.trades.entry_sig_date[r.trades.entry_date.notna()].max()
        r.current_trades = r.trades[
                (r.trades.entry_sig_date == maxday )
                | (r.trades.exit_sig_date == maxday)
                | (r.trades.exit_sig_date > latest_entry_day)
                | (r.trades.entry_sig_date == latest_entry_day)
                | (r.trades.exit_sig_date.isnull())
                ].set_index('stock_id')

        r.next_trading_date = max(r.current_trades.entry_sig_date.max(), r.current_trades.exit_sig_date.max())

        r.current_trades['weight'] = 0
        if len(r.weights) != 0:
            r.current_trades['weight'] = r.weights.reindex(r.current_trades.index).fillna(0)

        r.current_trades['next_weights'] = 0
        if len(r.next_weights) != 0:
            r.current_trades['next_weights'] = r.next_weights.reindex(r.current_trades.index).fillna(0)
    
    r.trades = r.trades.drop(['entry_index', 'exit_index'], axis=1)

    return r