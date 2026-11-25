import io
import matplotlib
matplotlib.use('Agg') # Set non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import mplfinance as mpf
import pandas as pd
import talib
from datetime import datetime
from src.format_data import get_each_company_daily_price, get_taiex_daily
from src.stock.schemas import StockChartQueryParams

class StockService:
    def __init__(self, data_instance):
        self.data = data_instance
        self.colors  = {
        'MA5': '#1f77b4',
        'MA10': '#ff7f0e',
        'MA20': "#d5e219",
        'MA60': '#2ca02c',
        'MA240': '#ac2f2f',
        'BB_Upper': 'gray',
        'BB_Lower': 'gray',
        'MACD': '#d62728',
        'Signal': '#1f77b4',
        'MACD_Hist_Positive': '#d62728',
        'MACD_Hist_Negative': '#2ca02c',
        'RSI_Overbought': 'red',
        'RSI_Oversold': 'green',
        'RSI': '#9467bd'
    }

    def add_header_labels(self, ax, labels_info):
        """
        labels_info: list of dict {'label': 'Name', 'value': 123.45, 'color': 'red'}
        """
        x_pos = 0.0 # 起始位置 (左側)
        y_pos = 0.8 # 放在圖表上方一點點 (調低一點，避免太高)
        
        for item in labels_info:
            text = f"{item['label']} {item['value']:,.2f}  " # 名稱 + 數值 + 空格
            
            # 使用 axes 座標系 (0~1)，這樣縮放都不會跑掉
            t = ax.text(
                x_pos, y_pos, text, 
                color=item['color'], 
                transform=ax.transAxes, 
                fontsize=10, 
                fontweight='bold',
                verticalalignment='bottom'
            )
            
            # 這裡用一個簡單的估算來移動 x_pos，避免文字重疊
            char_width_approx = 0.0045
            x_pos += len(text) * char_width_approx


    def process_stock_data(self, symbol: str, params: StockChartQueryParams, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            raise ValueError(f"No data found for {symbol}")
        
        # Ensure index is Datetime
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()

        if not params.end_date:
            params.end_date = datetime.now().date()  # Default to today if not provided

        df = df[df.index >= "2000-01-01"]  # Filter out any data before 2000-01-01
        df = df[df.index <= pd.to_datetime(params.end_date)]  # Filter up to end_date
        
        if params.timeframe in ["W", "M"]:
            try:
                agg_logic = {
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }
        
                # Only use columns that exist
                active_agg = {k: v for k, v in agg_logic.items() if k in df.columns}
        
                # Resample
                df = df.resample(params.timeframe).agg(active_agg)
        
                # Drop empty bins
                df = df.dropna(how='all')
        
            except Exception as e:
                # Add debugging context to the error
                error_msg = f"Resample failed. Shape: {df.shape}, Dtypes: {df.dtypes.to_dict()}. Error: {str(e)}"
                raise RuntimeError(error_msg)
            
        return df



    def get_taiex_data(self, params: StockChartQueryParams) -> pd.DataFrame:
        df = get_taiex_daily(self.data.raw_taiex_data).copy()

        return self.process_stock_data("TAIEX", params, df).reset_index().to_dict(orient="records")

    


    def get_stock_data(self, company_symbol: str, params: StockChartQueryParams) -> pd.DataFrame:
        df = get_each_company_daily_price(self.data.raw_price_data, company_symbol).copy()
    
        return self.process_stock_data(company_symbol, params, df).reset_index().to_dict(orient="records")

    

    def get_stock_chart(self, company_symbol: str, params: StockChartQueryParams) -> io.BytesIO:
        """
        Generate stock chart using mplfinance
        """
        # 1. Get raw data (Full History)
        df = get_each_company_daily_price(self.data.raw_price_data, company_symbol)
        
        if df.empty:
            raise ValueError(f"No data found for symbol {company_symbol}")

        # Ensure index is Datetime
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()

        # Determine strict end date once and use it consistently.
        if params.end_date:
            display_end_ts = pd.to_datetime(params.end_date).normalize()
        else:
            display_end_ts = pd.Timestamp(datetime.now().date())

        essential_cols = ['open', 'high', 'low', 'close', 'volume']

        # Keep only valid columns
        df = df[essential_cols].copy()
        df = df.dropna(subset=essential_cols)
        
        if df.empty:
            raise ValueError(f"No valid numeric data found for symbol {company_symbol} after cleaning")

        if params.timeframe in ["W", "M"]:
            try:
                agg_logic = {
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }
                # Only use columns that exist
                active_agg = {k: v for k, v in agg_logic.items() if k in df.columns}
                
                # Resample
                df = df.resample(params.timeframe).agg(active_agg)
                
                # Filter out empty bins (where Close is NaN)
                if 'close' in df.columns:
                    df = df.dropna(subset=['close'])
                else:
                    df = df.dropna(how='all')
                    
            except Exception as e:
                # Add debugging context to the error
                error_msg = f"Resample failed. Shape: {df.shape}, Dtypes: {df.dtypes.to_dict()}. Error: {str(e)}"
                raise RuntimeError(error_msg)

        # Rename columns for mplfinance / calculation
        df = df.rename(columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume"
        })

        close = df["Close"].values
        data_len = len(close)
        
        try:
            # Panel 0: MAs - Only calculate if enough data
            if data_len >= 20:
                df["MA20"] = talib.SMA(close, timeperiod=20)
            if data_len >= 60:
                df["MA60"] = talib.SMA(close, timeperiod=60)
            if data_len >= 240:
                df["MA240"] = talib.SMA(close, timeperiod=240)

            # Panel 1: BBands - Only if enough data
            if data_len >= 20:
                upper, middle, lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=talib.MA_Type.SMA)
                df["BB_Upper"] = upper
                df["BB_Middle"] = middle
                df["BB_Lower"] = lower

            # Panel 2: MACD - Need at least 26+9=35 bars
            if data_len >= 35:
                macd, signal, hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
                df["MACD"] = macd
                df["MACD_Signal"] = signal
                df["MACD_Hist"] = hist

            # Panel 3: RSI - Need at least 14 bars
            if data_len >= 14:
                df["RSI"] = talib.RSI(close, timeperiod=14)
            
        except Exception as e:
            error_msg = f"TALib calculation failed. Data length: {data_len}, Close dtype: {close.dtype}, Error: {str(e)}"
            raise RuntimeError(error_msg)

        # Filter Date Range for Display
        # For resampled data, include the bucket that contains end_date (e.g. week/month end label).
        if params.timeframe in ["W", "M"]:
            display_cutoff = display_end_ts.to_period(params.timeframe).end_time.normalize()

        # Slice data up to end_date
        # We also need a start point. If not provided, show last N bars (e.g. 240)
        df_display = df[df.index <= display_cutoff]
        
        if len(df_display) > 240:
            df_display = df_display.iloc[-240:]

        if len(df_display) == 0:
            raise ValueError("Not enough data to plot chart for the selected range")

        # mplfinance may render a distorted candle/volume bar when only one bar is present.
        # Add one empty period on each side so the real bar has visible horizontal context.
        plot_df = df_display
        if len(df_display) == 1:
            single_date = df_display.index[0]
            if params.timeframe == "W":
                pad_offset = pd.offsets.Week(1)
            elif params.timeframe == "M":
                pad_offset = pd.offsets.MonthEnd(1)
            else:
                pad_offset = pd.offsets.BDay(1)

            padding_index = pd.DatetimeIndex([single_date - pad_offset, single_date + pad_offset])
            padding_index = padding_index[padding_index != single_date].drop_duplicates()
            if len(padding_index) == 0:
                padding_index = pd.DatetimeIndex([single_date - pd.Timedelta(days=1), single_date + pd.Timedelta(days=1)])

            padding_df = pd.DataFrame(index=padding_index, columns=df_display.columns, dtype=float)
            plot_df = pd.concat([df_display, padding_df]).sort_index()

        # 4. Construct AddPlots
        apds = []
    
        idx_main = 0
        idx_vol = 1
        
        current_idx = 1
        
        idx_macd = current_idx + 1
        idx_rsi = current_idx + 2

        macd_series = plot_df['MACD'] if 'MACD' in plot_df.columns else pd.Series(np.nan, index=plot_df.index)
        macd_signal_series = plot_df['MACD_Signal'] if 'MACD_Signal' in plot_df.columns else pd.Series(np.nan, index=plot_df.index)
        macd_hist_series = plot_df['MACD_Hist'] if 'MACD_Hist' in plot_df.columns else pd.Series(np.nan, index=plot_df.index)
        rsi_series = plot_df['RSI'] if 'RSI' in plot_df.columns else pd.Series(np.nan, index=plot_df.index)
        
        # MAs (explicitly set secondary_y=False to use primary y-axis) - Only plot if exists
        if 'MA20' in plot_df.columns:
            apds.append(mpf.make_addplot(plot_df['MA20'], panel=idx_main, color=self.colors['MA20'], width=1.0, secondary_y=False))
        if 'MA60' in plot_df.columns:
            apds.append(mpf.make_addplot(plot_df['MA60'], panel=idx_main, color=self.colors['MA60'], width=1.0, secondary_y=False))
        if 'MA240' in plot_df.columns:
            apds.append(mpf.make_addplot(plot_df['MA240'], panel=idx_main, color=self.colors['MA240'], width=1.0, secondary_y=False))
        
        # BBands (畫在主圖，因為需要跟 K 線對照) - Only plot if exists
        # 使用 linestyle='--' 區隔 BB 和 MA，並加上填充色
        if 'BB_Upper' in plot_df.columns and 'BB_Lower' in plot_df.columns:
            apds.append(mpf.make_addplot(plot_df['BB_Upper'], panel=idx_main, color=self.colors['BB_Upper'], alpha=0.5, width=0.8, linestyle='--', secondary_y=False))
            apds.append(mpf.make_addplot(plot_df['BB_Lower'], panel=idx_main, color=self.colors['BB_Lower'], alpha=0.5, width=0.8, linestyle='--', secondary_y=False))
        # 這裡我們可以選擇是否畫中軌，因為中軌其實就是 MA20，避免重複可以不畫，或是畫細一點

        # -- Panel: MACD -- Always render panel, even if indicator values are all NaN.
        apds.append(mpf.make_addplot(macd_series, panel=idx_macd, color=self.colors['MACD'], width=1.0, ylabel='MACD', secondary_y=False))
        apds.append(mpf.make_addplot(macd_signal_series, panel=idx_macd, color=self.colors['Signal'], width=1.0, secondary_y=False))
        apds.append(mpf.make_addplot(pd.Series(0.0, index=plot_df.index), panel=idx_macd, color='gray', width=0.8, alpha=0.6, secondary_y=False))
        macd_hist_colors = [
            self.colors['MACD_Hist_Positive'] if pd.notna(v) and v >= 0
            else self.colors['MACD_Hist_Negative'] if pd.notna(v)
            else 'gray'
            for v in macd_hist_series
        ]
        apds.append(mpf.make_addplot(macd_hist_series, type='bar', panel=idx_macd, color=macd_hist_colors, alpha=0.5, secondary_y=False))

        # -- Panel: RSI -- Always render panel, even if indicator values are all NaN.
        apds.append(mpf.make_addplot(rsi_series, panel=idx_rsi, color=self.colors['RSI'], width=1.0, ylabel='RSI', secondary_y=False))
        apds.append(mpf.make_addplot(pd.Series(70, index=plot_df.index), panel=idx_rsi, color=self.colors['RSI_Overbought'], width=0.8, linestyle='--', secondary_y=False))
        apds.append(mpf.make_addplot(pd.Series(50, index=plot_df.index), panel=idx_rsi, color='gray', width=0.7, linestyle=':', alpha=0.7, secondary_y=False))
        apds.append(mpf.make_addplot(pd.Series(30, index=plot_df.index), panel=idx_rsi, color=self.colors['RSI_Oversold'], width=0.8, linestyle='--', secondary_y=False))

        # 5. Visual Configuration
        
        # Panel Ratios (高度比例)
        # 主圖通常最大，副圖較小
        # 例如：主圖 4份，成交量 1份，MACD 1份，RSI 1份
        panel_ratios = [4]
        panel_ratios.append(1) # Volume
        panel_ratios.append(1) # MACD
        panel_ratios.append(1) # RSI

        # Style
        # 使用適合螢幕閱讀的樣式
        my_colors = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='inherit')
        my_style = mpf.make_mpf_style(
            base_mpf_style='yahoo', # yahoo 風格背景比較乾淨
            rc={
                'font.family': 'Microsoft JhengHei',
                'axes.unicode_minus': False,
                'axes.labelsize': 10,
                'axes.titlesize': 20
            }, 
            marketcolors=my_colors
        )

        # 尺寸設定：19.2 x 10.8 英吋 (即 1920x1080 像素效果)
        fig_size = (19.2, 10.8)

        buf = io.BytesIO()
        
        try:
            if params.timeframe == "M":
                datetime_format = '%Y-%m'
            else:
                datetime_format = '%Y-%m-%d'

            # Plotting
            fig, axes = mpf.plot(
                plot_df,
                type='candle',
                style=my_style,
                addplot=apds,
                volume=True,
                volume_panel=idx_vol, # 指定成交量面板
                panel_ratios=panel_ratios,
                title=f"{self.company_symbol} Technical Analysis ({params.timeframe})",
                figsize=fig_size,
                returnfig=True,
                tight_layout=True,
                scale_padding={'left': 0.5, 'top': 3, 'right': 1.5, 'bottom': 0.5}, # 留白給標籤
                datetime_format=datetime_format,
                xrotation=15,
            )

            # Single-bar charts can produce duplicate auto tick labels; force deterministic labels.
            if len(df_display) == 1:
                tick_positions = np.arange(len(plot_df))
                tick_labels = [d.strftime(datetime_format) for d in plot_df.index]
                bottom_ax = axes[idx_rsi * 2]
                bottom_ax.set_xticks(tick_positions)
                bottom_ax.set_xticklabels(tick_labels, rotation=15, ha='right')

            # -- 準備 Panel 0 (主圖) 的標籤資料 --
            # 取最後一筆非 NaN 的值
            last_idx = -1 
            
            main_labels = []
            # Only add labels for indicators that exist and have valid values
            if 'MA20' in df_display.columns and not pd.isna(df_display['MA20'].iloc[last_idx]):
                main_labels.append({'label': 'SMA20', 'value': df_display['MA20'].iloc[last_idx], 'color': self.colors['MA20']})
            if 'MA60' in df_display.columns and not pd.isna(df_display['MA60'].iloc[last_idx]):
                main_labels.append({'label': 'SMA60', 'value': df_display['MA60'].iloc[last_idx], 'color': self.colors['MA60']})
            if 'MA240' in df_display.columns and not pd.isna(df_display['MA240'].iloc[last_idx]):
                main_labels.append({'label': 'SMA240', 'value': df_display['MA240'].iloc[last_idx], 'color': self.colors['MA240']})
            if 'BB_Upper' in df_display.columns and not pd.isna(df_display['BB_Upper'].iloc[last_idx]):
                main_labels.append({'label': 'BB Upper', 'value': df_display['BB_Upper'].iloc[last_idx], 'color': self.colors['BB_Upper']})
            if 'BB_Lower' in df_display.columns and not pd.isna(df_display['BB_Lower'].iloc[last_idx]):
                main_labels.append({'label': 'BB Lower', 'value': df_display['BB_Lower'].iloc[last_idx], 'color': self.colors['BB_Lower']})
            
            # 在主圖上方畫標籤
            if main_labels:
                self.add_header_labels(axes[0], main_labels)
            
            # -- 準備 Panel (MACD) 的標籤資料 --
            if 'MACD' in df_display.columns and df_display['MACD'].notna().any():
                macd_ax = axes[idx_macd * 2]
                macd_labels = []
                if not pd.isna(df_display['MACD'].iloc[last_idx]):
                    macd_labels.append({'label': 'MACD', 'value': df_display['MACD'].iloc[last_idx], 'color': self.colors['MACD']})
                if not pd.isna(df_display['MACD_Signal'].iloc[last_idx]):
                    macd_labels.append({'label': 'Signal', 'value': df_display['MACD_Signal'].iloc[last_idx], 'color': self.colors['Signal']})
                if macd_labels:
                    self.add_header_labels(macd_ax, macd_labels)

            # -- 準備 Panel (RSI) 的標籤資料 --
            if 'RSI' in df_display.columns and df_display['RSI'].notna().any():
                rsi_ax = axes[idx_rsi * 2]
                rsi_labels = []
                if not pd.isna(df_display['RSI'].iloc[last_idx]):
                    rsi_labels.append({'label': 'RSI(14)', 'value': df_display['RSI'].iloc[last_idx], 'color': self.colors['RSI']})
                if rsi_labels:
                    self.add_header_labels(rsi_ax, rsi_labels)

            # 儲存圖片
            fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            plt.close(fig)
            
        except Exception as e:
            plt.close('all')
            raise RuntimeError(f"Failed to generate chart: {str(e)}")

        buf.seek(0)
        return buf
    
    def get_taiex_chart(self, params: StockChartQueryParams) -> io.BytesIO:
        """
        Generate taiex chart using mplfinance
        """
        # 1. Get raw data (Full History)
        df = get_taiex_daily(self.data.raw_taiex_data)
        
        if df.empty:
            raise ValueError(f"No data found for taiex")
        

        # Ensure index is Datetime
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()        

        if params.timeframe in ["W", "M"]:
            try:
                agg_logic = {
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }
                # Only use columns that exist
                active_agg = {k: v for k, v in agg_logic.items() if k in df.columns}
                
                # Resample
                df = df.resample(params.timeframe).agg(active_agg)
                
                # Filter out empty bins (where Close is NaN)
                if 'close' in df.columns:
                    df = df.dropna(subset=['close'])
                else:
                    df = df.dropna(how='all')
                    
            except Exception as e:
                # Add debugging context to the error
                error_msg = f"Resample failed. Shape: {df.shape}, Dtypes: {df.dtypes.to_dict()}. Error: {str(e)}"
                raise RuntimeError(error_msg)

        # Rename columns for mplfinance / calculation
        df = df.rename(columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume"
        })

        if "Close" not in df.columns:
             raise ValueError("Data missing 'close' price column")
        # 2. Calculate Indicators using TALib (On Full Data)
        close = df["Close"].values
        
        # Panel 0: MAs
        df["MA5"] = talib.SMA(close, timeperiod=5)
        df["MA10"] = talib.SMA(close, timeperiod=10)
        df["MA20"] = talib.SMA(close, timeperiod=20)
        df["MA60"] = talib.SMA(close, timeperiod=60)
        df["MA240"] = talib.SMA(close, timeperiod=240)

        # 3. Filter Date Range for Display
        # Determine strict end date
        if params.end_date:
            display_end = pd.to_datetime(params.end_date).date()
        else:
            display_end = datetime.now().date()

        # Slice data up to end_date
        # We also need a start point. If not provided, show last N bars (e.g. 240)
        df_display = df[df.index.date <= display_end]
        
        if len(df_display) > 240:
            df_display = df_display.iloc[-240:]

        # 4. Construct AddPlots
        apds = []
    
        idx_main = 0
        idx_vol = 1
        
        

        # -- Panel 0: Main Chart Indicators --
        # MAs
        apds.append(mpf.make_addplot(df_display['MA5'], panel=idx_main, color=self.colors['MA5'], width=1.0))
        apds.append(mpf.make_addplot(df_display['MA10'], panel=idx_main, color=self.colors['MA10'], width=1.0))
        apds.append(mpf.make_addplot(df_display['MA20'], panel=idx_main, color=self.colors['MA20'], width=1.0))
        apds.append(mpf.make_addplot(df_display['MA60'], panel=idx_main, color=self.colors['MA60'], width=1.0))
        apds.append(mpf.make_addplot(df_display['MA240'], panel=idx_main, color=self.colors['MA240'], width=1.0))


        # Style
        # 使用適合螢幕閱讀的樣式
        my_colors = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='inherit')
        my_style = mpf.make_mpf_style(
            base_mpf_style='yahoo', # yahoo 風格背景比較乾淨
            rc={
                'font.family': 'Microsoft JhengHei',
                'axes.unicode_minus': False,
                'axes.labelsize': 10,
                'axes.titlesize': 20
            }, 
            marketcolors=my_colors
        )

        # 尺寸設定：19.2 x 10.8 英吋 (即 1920x1080 像素效果)
        fig_size = (19.2, 10.8)

        buf = io.BytesIO()
        
        try:
            # Plotting
            fig, axes = mpf.plot(
                df_display,
                type='candle',
                style=my_style,
                addplot=apds,
                volume=True,
                volume_panel=idx_vol, # 指定成交量面板
                title=f"{self.company_symbol}",
                figsize=fig_size,
                returnfig=True,
                tight_layout=True,
                scale_padding={'left': 0.5, 'top': 3, 'right': 1.5, 'bottom': 0.5}, # 留白給標籤
                datetime_format='%Y-%m-%d' # 修正 TAIEX 時間顯示問題，只顯示月-日，或者 Y-m-d
            )

            # 6. Adding Legends (Critical for readability)
            # -- 準備 Panel 0 (主圖) 的標籤資料 --
            # 取最後一筆非 NaN 的值
            last_idx = -1 
            
            main_labels = [
                {'label': 'SMA5', 'value': df_display['MA5'].iloc[last_idx], 'color': self.colors['MA5']},
                {'label': 'SMA10', 'value': df_display['MA10'].iloc[last_idx], 'color': self.colors['MA10']},
                {'label': 'SMA20', 'value': df_display['MA20'].iloc[last_idx], 'color': self.colors['MA20']},
                {'label': 'SMA60', 'value': df_display['MA60'].iloc[last_idx], 'color': self.colors['MA60']},
                {'label': 'SMA240', 'value': df_display['MA240'].iloc[last_idx], 'color': self.colors['MA240']},
            ]
            # 在主圖上方畫標籤
            self.add_header_labels(axes[0], main_labels)

            fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            plt.close(fig)

        except Exception as e:
            plt.close('all')
            raise RuntimeError(f"Failed to generate chart: {str(e)}")

        buf.seek(0)
        return buf
    
    def get_stock_river_chart(self, company_symbol: str, params: StockChartQueryParams) -> io.BytesIO:
        """
        Generate stock river chart using PE ratio bands and close price.

        Note: PE is computed from close price and trailing-4-quarter EPS (TTM):
        PE = Price / EPS_TTM.
        This avoids fetching/depending on precomputed PE ratio data.
        """
        
        buf = io.BytesIO()
        
        # Get data
        close = self.data.get("price:close")[company_symbol]
        
        # Ensure datetime index + numeric
        close.index = pd.to_datetime(close.index)
        close = pd.to_numeric(close, errors='coerce')
        
        # Filter date range
        end_date_dt = pd.to_datetime(self.end_date) if self.end_date else pd.Timestamp(datetime.now())
        start_date_dt = end_date_dt - pd.DateOffset(years=10)  # Show last 10 years only
        close = close[(close.index <= end_date_dt) & (close.index >= start_date_dt)]

        # Build trailing-4-quarter EPS (TTM) from report events.
        # Compute rolling TTM on fiscal quarter sequence, then map each TTM to its release_date.
        report_eps_dict = self.data.format_report_data("EPS")
        if not report_eps_dict or "EPS" not in report_eps_dict:
            raise ValueError("No EPS report data available")

        eps_events_df = report_eps_dict["EPS"]
        if self.company_symbol not in eps_events_df.columns:
            raise ValueError(f"No EPS data found for symbol {self.company_symbol}")

        # eps_events is indexed by (date, release_date)
        eps_events = eps_events_df[self.company_symbol].dropna().rename("eps").reset_index()
        if not {"date", "release_date", "eps"}.issubset(set(eps_events.columns)):
            raise ValueError("Unexpected EPS report data format")

        eps_events["date"] = pd.to_datetime(eps_events["date"])
        eps_events["release_date"] = pd.to_datetime(eps_events["release_date"])

        # Keep enough quarter history to compute rolling TTM for the visible window.
        eps_events = eps_events[
            (eps_events["release_date"] <= end_date_dt) &
            (eps_events["date"] >= (start_date_dt - pd.DateOffset(years=2)))
        ]

        # Dedupe by fiscal quarter first, then compute TTM in fiscal order.
        eps_quarterly = (
            eps_events
            .sort_values(by=["date", "release_date"])
            .groupby("date", as_index=False)
            .agg({"eps": "last", "release_date": "last"})
            .sort_values(by="date")
        )
        eps_quarterly["eps_ttm"] = eps_quarterly["eps"].rolling(window=4, min_periods=4).sum()

        # Use release_date as the first date when each TTM value is knowable.
        eps_ttm_by_release = (
            eps_quarterly.dropna(subset=["eps_ttm"])
            .sort_values(by=["release_date", "date"])
            .groupby("release_date")["eps_ttm"]
            .last()
            .sort_index()
        )

        # Align to close trading calendar using only available information up to that date
        eps_ttm_daily = eps_ttm_by_release.reindex(close.index, method="ffill")

        # Resample to monthly frequency
        close = close.resample('M').last() # Monthly frequency, take last value of the month
        eps_ttm = eps_ttm_daily.resample('M').last() # Monthly frequency
        
        # Combine monthly data (do NOT drop EPS<=0; we still want to plot close)
        data_full = pd.DataFrame({'close': close, 'eps': eps_ttm})
        data_full = data_full.dropna(subset=['close'])

        # Compute PE only when EPS_TTM > 0; otherwise keep NaN so river is not drawn
        valid_mask = data_full['eps'].notna() & (data_full['eps'] > 0) & data_full['close'].notna()
        data_full['pe'] = np.nan
        data_full.loc[valid_mask, 'pe'] = data_full.loc[valid_mask, 'close'] / data_full.loc[valid_mask, 'eps']
        data_full = data_full.replace([np.inf, -np.inf], np.nan)

        # Determine whether we have enough valid months to draw river bands
        valid_pe = data_full['pe'].dropna()
        has_river = len(valid_pe) >= 2
        
        pe_lines = None
        if has_river:
            # Get historical PE min and max (extreme values) from valid segments only
            pe_min = valid_pe.min()
            pe_max = valid_pe.max()

            # Divide into 6 bands (5 equal divisions between min and max)
            # This creates 6 PE threshold lines
            pe_lines = np.linspace(pe_min, pe_max, 6)
        
        # Create figure
        plt.rcParams['font.family'] = 'Microsoft JhengHei'
        plt.rcParams['axes.unicode_minus'] = False
        fig, ax = plt.subplots(figsize=(19.2, 10.8))
        
        # Define colors for PE bands (gradient from cool to warm, 5 colors for 5 bands)
        band_colors = [
            '#8FD4B8',  # 青綠 (低PE)
            '#B8E6A0',  # 淺綠
            '#F5C77E',  # 橙黃
            '#F59E6C',  # 橙
            '#E8746A'   # 紅橙 (高PE)
        ]
        
        # Define colors for 6 PE boundary lines (related to adjacent bands)
        line_colors = [
            '#6CBAA0',  # Darker cyan (below band 0)
            '#9FDD94',  # Between band 0 and 1
            '#D9B65E',  # Between band 1 and 2
            '#F28850',  # Between band 2 and 3
            '#E06558',  # Between band 3 and 4
            '#C84848'   # Darker red (above band 4)
        ]
        
        # Plot PE bands (fill between) - using price = EPS × PE
        x = data_full.index

        last_close_idx = data_full['close'].last_valid_index()
        last_close_val = float(data_full.loc[last_close_idx, 'close']) if last_close_idx is not None else np.nan

        end_month_idx = data_full.index.max() if len(data_full.index) else None
        end_eps_val = float(data_full.loc[end_month_idx, 'eps']) if end_month_idx is not None and pd.notna(data_full.loc[end_month_idx, 'eps']) else np.nan
        show_pe_legend_value = (not np.isnan(end_eps_val)) and (end_eps_val > 0)

        if has_river and pe_lines is not None:
            # Draw 5 bands between 6 PE lines (only where EPS_TTM>0)
            for i in range(5):
                pe_lower = pe_lines[i]
                pe_upper = pe_lines[i + 1]

                # Calculate price bands: Price = EPS × PE
                price_lower = data_full['eps'] * pe_lower
                price_upper = data_full['eps'] * pe_upper

                ax.fill_between(
                    x,
                    price_lower,
                    price_upper,
                    where=valid_mask,
                    interpolate=True,
                    color=band_colors[i],
                    alpha=0.7
                )

            # Draw 6 PE boundary lines with labels (only where EPS_TTM>0)
            for i, pe_val in enumerate(pe_lines):
                price_line = (data_full['eps'] * pe_val).where(valid_mask)

                # Legend numeric value should only be shown when end_date EPS_TTM > 0
                if show_pe_legend_value:
                    label = f'{pe_val:.1f}倍: {(end_eps_val * float(pe_val)):.2f}'
                else:
                    label = f'{pe_val:.1f}倍'

                ax.plot(
                    x,
                    price_line,
                    color=line_colors[i],
                    linewidth=1.5,
                    alpha=0.9,
                    linestyle='-',
                    label=label
                )

        # Plot actual close price (always)
        close_label_val = "N/A" if np.isnan(last_close_val) else f"{last_close_val:.2f}"
        ax.plot(x, data_full['close'], color='#1f4788', linewidth=2.5, label=f'close: {close_label_val}', zorder=10)
        
        # Formatting
        ax.set_title(f'{self.company_symbol} PE River Chart', fontsize=20, fontweight='bold', pad=20)
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Price', fontsize=12)
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        
        # Legend on the right side
        ax.legend(
            loc='center left',
            bbox_to_anchor=(1.01, 0.5),
            frameon=True,
            fancybox=True,
            shadow=True,
            fontsize=10
        )
        
        # Format y-axis
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{int(y)}'))
        
        # Adjust layout to prevent legend cutoff
        plt.tight_layout()
        
        try:
            fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            plt.close(fig)
        except Exception as e:
            plt.close(fig)
            raise RuntimeError(f"Failed to generate stock river chart: {str(e)}")

        buf.seek(0)
        return buf