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
from typing import Optional, List

class StockService:
    def __init__(self, data, company_symbol: str, end_date: Optional[str] = None):
        """
        Initialize StockService
        :param data: Data instance from src.get_data
        :param company_symbol: Stock symbol
        :param end_date: Optional end date for data context
        """
        self.data = data
        self.company_symbol = company_symbol
        self.end_date = end_date
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
            # 在 transAxes 中，0.1 大約是寬度的 10%。根據字串長度動態調整
            # 每個字元大約佔 0.008 (這取決於字型大小和圖表寬度，可能需要微調)
            char_width_approx = 0.0045
            x_pos += len(text) * char_width_approx

    def get_stock_chart(self, params: StockChartQueryParams) -> io.BytesIO:
        """
        Generate stock chart using mplfinance
        """
        # 1. Get raw data (Full History)
        df = get_each_company_daily_price(self.data.raw_price_data, self.company_symbol)
        
        if df.empty:
            raise ValueError(f"No data found for symbol {self.company_symbol}")

        # Ensure index is Datetime
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        
        # Ensure columns are numeric to avoid aggregation errors
        temp_df = df.copy()
        target_cols = ['open', 'high', 'low', 'close', 'volume']
        valid_cols = [c for c in target_cols if c in temp_df.columns]
        
        # Keep only valid columns
        temp_df = temp_df[valid_cols]
        
        # Strict numeric conversion
        for col in valid_cols:
            temp_df[col] = pd.to_numeric(temp_df[col], errors='coerce')
            
        # Drop rows where essential price data is missing
        # We need at least Close to be present, but usually OHLC all needed
        essential_cols = [c for c in ['open', 'high', 'low', 'close'] if c in valid_cols]
        if essential_cols:
            temp_df = temp_df.dropna(subset=essential_cols)
        
        if temp_df.empty:
            raise ValueError(f"No valid numeric data found for symbol {self.company_symbol} after cleaning")
            
        # Final strict cast to float
        df = temp_df.astype(float)

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
                print(error_msg) # Print to server logs
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
    
        # Adjust indicator periods based on timeframe and data length
        data_len = len(close)
        
        # Safety check: need minimum data for any calculation
        if data_len < 14:
            raise ValueError(f"Insufficient data for technical indicators. Only {data_len} bars available, need at least 14.")
        
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
            print(f"[ERROR] {error_msg}")
            raise RuntimeError(error_msg)

        # 3. Filter Date Range for Display
        # Determine strict end date
        if params.end_date:
            display_end = pd.to_datetime(params.end_date).date()
        elif self.end_date:
            display_end = pd.to_datetime(self.end_date).date()
        else:
            display_end = datetime.now().date()

        # Slice data up to end_date
        # We also need a start point. If not provided, show last N bars (e.g. 240)
        df_display = df[df.index.date <= display_end]
        
        if len(df_display) > 240:
            df_display = df_display.iloc[-240:]

        if len(df_display) < 2:
            raise ValueError("Not enough data to plot chart for the selected range")

        # 4. Construct AddPlots
        apds = []
    
        idx_main = 0
        idx_vol = 1
        
        current_idx = 1
        
        idx_macd = current_idx + 1
        idx_rsi = current_idx + 2

        # -- Panel 0: Main Chart Indicators --
        # Verify BB data integrity
        # bb_valid = df_display[['BB_Upper', 'BB_Lower']].notna().all(axis=1)
        # if bb_valid.any():
        #     bb_check = df_display.loc[bb_valid, 'BB_Upper'] >= df_display.loc[bb_valid, 'BB_Lower']
        #     if not bb_check.all():
        #         print(f"[WARNING] Bollinger Bands validation failed! Some Upper < Lower")
        #         print(f"[WARNING] Sample data: {df_display[['BB_Upper', 'BB_Lower']].tail()}")
        
        # MAs (explicitly set secondary_y=False to use primary y-axis) - Only plot if exists
        if 'MA20' in df_display.columns:
            apds.append(mpf.make_addplot(df_display['MA20'], panel=idx_main, color=self.colors['MA20'], width=1.0, secondary_y=False))
        if 'MA60' in df_display.columns:
            apds.append(mpf.make_addplot(df_display['MA60'], panel=idx_main, color=self.colors['MA60'], width=1.0, secondary_y=False))
        if 'MA240' in df_display.columns:
            apds.append(mpf.make_addplot(df_display['MA240'], panel=idx_main, color=self.colors['MA240'], width=1.0, secondary_y=False))
        
        # BBands (畫在主圖，因為需要跟 K 線對照) - Only plot if exists
        # 使用 linestyle='--' 區隔 BB 和 MA，並加上填充色
        if 'BB_Upper' in df_display.columns and 'BB_Lower' in df_display.columns:
            apds.append(mpf.make_addplot(df_display['BB_Upper'], panel=idx_main, color=self.colors['BB_Upper'], alpha=0.5, width=0.8, linestyle='--', secondary_y=False))
            apds.append(mpf.make_addplot(df_display['BB_Lower'], panel=idx_main, color=self.colors['BB_Lower'], alpha=0.5, width=0.8, linestyle='--', secondary_y=False))
        # 這裡我們可以選擇是否畫中軌，因為中軌其實就是 MA20，避免重複可以不畫，或是畫細一點

        # -- Panel: MACD -- Only plot if exists
        if 'MACD' in df_display.columns:
            apds.append(mpf.make_addplot(df_display['MACD'], panel=idx_macd, color=self.colors['MACD'], width=1.0, ylabel='MACD', secondary_y=False))
            apds.append(mpf.make_addplot(df_display['MACD_Signal'], panel=idx_macd, color=self.colors['Signal'], width=1.0, secondary_y=False))
            # MACD 柱狀圖：根據正負給顏色
            macd_hist_colors = [self.colors['MACD_Hist_Positive'] if v >= 0 else self.colors['MACD_Hist_Negative'] for v in df_display['MACD_Hist']]
            apds.append(mpf.make_addplot(df_display['MACD_Hist'], type='bar', panel=idx_macd, color=macd_hist_colors, alpha=0.5, secondary_y=False))

        # -- Panel: RSI -- Only plot if exists
        if 'RSI' in df_display.columns:
            apds.append(mpf.make_addplot(df_display['RSI'], panel=idx_rsi, color=self.colors['RSI'], width=1.0, ylabel='RSI', secondary_y=False))
            apds.append(mpf.make_addplot(pd.Series(70, index=df_display.index), panel=idx_rsi, color=self.colors['RSI_Overbought'], width=0.8, linestyle='--', secondary_y=False))
            apds.append(mpf.make_addplot(pd.Series(30, index=df_display.index), panel=idx_rsi, color=self.colors['RSI_Oversold'], width=0.8, linestyle='--', secondary_y=False))

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
            # Plotting
            fig, axes = mpf.plot(
                df_display,
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
                scale_padding={'left': 0.5, 'top': 3, 'right': 1.5, 'bottom': 0.5} # 留白給標籤
            )

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
            if 'MACD' in df_display.columns:
                macd_ax = axes[idx_macd * 2]
                macd_labels = []
                if not pd.isna(df_display['MACD'].iloc[last_idx]):
                    macd_labels.append({'label': 'MACD', 'value': df_display['MACD'].iloc[last_idx], 'color': self.colors['MACD']})
                if not pd.isna(df_display['MACD_Signal'].iloc[last_idx]):
                    macd_labels.append({'label': 'Signal', 'value': df_display['MACD_Signal'].iloc[last_idx], 'color': self.colors['Signal']})
                if macd_labels:
                    self.add_header_labels(macd_ax, macd_labels)

            # -- 準備 Panel (RSI) 的標籤資料 --
            if 'RSI' in df_display.columns:
                rsi_ax = axes[idx_rsi * 2]
                rsi_labels = []
                if not pd.isna(df_display['RSI'].iloc[last_idx]):
                    rsi_labels.append({'label': 'RSI(14)', 'value': df_display['RSI'].iloc[last_idx], 'color': self.colors['RSI']})
                if rsi_labels:
                    self.add_header_labels(rsi_ax, rsi_labels)

            # 儲存圖片
            fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            
        except Exception as e:
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
                print(error_msg) # Print to server logs
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
        elif self.end_date:
            display_end = pd.to_datetime(self.end_date).date()
        else:
            display_end = datetime.now().date()

        # Slice data up to end_date
        # We also need a start point. If not provided, show last N bars (e.g. 240)
        df_display = df[df.index.date <= display_end]
        
        if len(df_display) > 240:
            df_display = df_display.iloc[-240:]

        if len(df_display) < 2:
            raise ValueError("Not enough data to plot chart for the selected range")

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
            
        except Exception as e:
            raise RuntimeError(f"Failed to generate chart: {str(e)}")

        buf.seek(0)
        return buf
    
    def get_stock_river_chart(self) -> io.BytesIO:
        """
        Generate stock river chart using PE ratio bands and close price
        """
        
        buf = io.BytesIO()
        
        # Get data
        close = self.data.get("price:close")[self.company_symbol]
        pe = self.data.get("price:pe_ratio")[self.company_symbol]
        
        # Ensure datetime index
        close.index = pd.to_datetime(close.index)
        pe.index = pd.to_datetime(pe.index)
        
        # Filter date range
        end_date_dt = pd.to_datetime(self.end_date) if self.end_date else pd.Timestamp(datetime.now())
        start_date_dt = end_date_dt - pd.DateOffset(years=10) # Show last 10 years
        close = close[(close.index <= end_date_dt) & (close.index >= start_date_dt)]
        pe = pe[(pe.index <= end_date_dt) & (pe.index >= start_date_dt)]

        # Resample to monthly frequency
        close = close.resample('M').last() # Monthly frequency, take last value of the month
        pe = pe.resample('M').last() # Monthly frequency, take last value of the month
        
        # Combine and clean data
        data = pd.DataFrame({'close': close, 'pe': pe})
        data = data.dropna()
        
        if len(data) < 10:
            raise ValueError("Insufficient data for PE river chart (need at least 10 months)")
        
        # Calculate EPS from close price and PE ratio (EPS = Price / PE)
        data['eps'] = data['close'] / data['pe']
        
        # Get historical PE min and max (extreme values)
        pe_min = data['pe'].min()
        pe_max = data['pe'].max()
        
        # Divide into 6 bands (5 equal divisions between min and max)
        # This creates 6 PE threshold lines
        pe_lines = np.linspace(pe_min, pe_max, 6)
        
        # Create figure
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
        x = data.index
        
        # Draw 5 bands between 6 PE lines
        for i in range(5):
            pe_lower = pe_lines[i]
            pe_upper = pe_lines[i + 1]
            
            # Calculate price bands: Price = EPS × PE
            price_lower = data['eps'] * pe_lower
            price_upper = data['eps'] * pe_upper
            
            ax.fill_between(
                x, 
                price_lower, 
                price_upper,
                color=band_colors[i],
                alpha=0.7
            )
        
        # Draw 6 PE boundary lines with labels (solid lines with colors related to adjacent bands)
        for i, pe_val in enumerate(pe_lines):
            price_line = data['eps'] * pe_val
            ax.plot(x, price_line, color=line_colors[i], linewidth=1.5, alpha=0.9, linestyle='-', label=f'PE {pe_val:.1f}')
        
        # Plot actual close price (bold line on top)
        ax.plot(x, data['close'], color='#1f4788', linewidth=2.5, label='Close Price', zorder=10)
        
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

    def get_next_trading_day_close_price(self) -> float:
        """
        Get next trading day and close price for a given company symbol and end date
        """
        df = get_each_company_daily_price(self.data.raw_price_data, self.company_symbol)
        
        if df.empty:
            raise ValueError(f"No data found for symbol {self.company_symbol}")

        # Ensure index is Datetime
        df.index = pd.to_datetime(df.index).date
        df = df.sort_index()

        # Filter data up to end_date
        if self.end_date:
            display_end = pd.to_datetime(self.end_date).date()
        elif self.end_date:
            display_end = pd.to_datetime(self.end_date).date()
        else:
            display_end = datetime.now().date()

        df_filtered = df[df.index > display_end]

        # Get the last available close price (which is the next trading day's close price)
        next_trading_date = df_filtered.index[0]
        next_trading_day_close_price = df_filtered['close'].iat[0]

        return {"date": next_trading_date, "close": next_trading_day_close_price}
