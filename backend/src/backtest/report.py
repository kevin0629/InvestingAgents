import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path
import plotly.graph_objs as go
import matplotlib.pyplot as plt
from typing import Mapping, Sequence

class Report():
    def __init__(self, stock_data, position, data) -> None:
        self.stock_data = stock_data
        self.position = position
        self.calc_return_table()

        try:
            self.benchmark = data.get('adjustedtaiex:close')
            self.benchmark.index = pd.to_datetime(self.benchmark.index)

            self.daily_benchmark = rebase(self.benchmark\
                .dropna().reindex(self.stock_data.index, method='ffill') \
                .ffill())
        except Exception as e:
            print(f"無法建立 Benchmark: {e}")
            pass

    def display(self, jupyter=False):
        from IPython.display import display
        
        # 計算
        fig = self.create_performance_figure(self.position)

        stats = self.get_stats()

        imp_stats = pd.Series({
         'annualized_rate_of_return':str(round(self.calc_cagr()*100, 2))+'%',
         'sharpe': str(self.calc_sharpe(self.stock_data['portfolio_returns'], nperiods=252)),
         'alpha': str(round(stats['alpha']*100, 2))+'%',
         'beta': str(round(stats['beta'], 2)),
         'max_drawdown':str(round(self.calc_dd(self.stock_data['portfolio_returns']).min()*100, 2))+'%',
         'avg_holdings': str(int(round(stats['avg_holdings'], 0))),
         'max_holdings': str(int(stats['max_holdings'])),
         'win_ratio':str(round(stats['win_ratio']*100, 2))+'%',
        }).to_frame().T
        imp_stats.index = ['']

        yearly_return_fig = self.create_yearly_return_figure()
        monthly_return_fig = self.create_monthly_return_figure()

        # show出來
        if jupyter:
            display(imp_stats)
            display(fig)
            display(yearly_return_fig)
            display(monthly_return_fig)
            if hasattr(self, 'current_trades'):
                display(self.current_trades)

        else:
            if hasattr(self, 'current_trades'):
                return imp_stats, self.current_trades
            
            return imp_stats
    
    def create_monthly_return_figure(self):
        import plotly.express as px
        monthly_table = pd.DataFrame(self.return_table).T
        monthly_table = round(monthly_table*100,1).drop(columns='YTD')

        fig = px.imshow(monthly_table.values,
                        labels=dict(x="month", y='year', color="return(%)"),
                        x=monthly_table.columns.astype(str),
                        y=monthly_table.index.astype(str),
                        text_auto=True,
                        color_continuous_scale='RdBu_r',

                        )

        fig.update_traces(
            hovertemplate="<br>".join([
                "year: %{y}",
                "month: %{x}",
                "return: %{z}%",
            ])
        )

        fig.update_layout(
            height = 550,
            width= 800,
            margin=dict(l=20, r=270, t=40, b=40),
            title={
                'text': 'monthly return',
                'x': 0.025,
                'yanchor': 'top',
            },
            yaxis={
                'side': "right",
            },
            coloraxis_showscale=False,
            coloraxis={'cmid':0}
        )

        return fig
    
    def create_yearly_return_figure(self):
        import plotly.express as px
        yearly_return = [round(v['YTD']*1000)/10 for v in self.return_table.values()]

        fig = px.imshow([yearly_return],
                        labels=dict(color="return(%)"),
                        x=list([str(k) for k in self.return_table.keys()]),
                        text_auto=True,
                        color_continuous_scale='RdBu_r',
                        )

        fig.update_traces(
            hovertemplate="<br>".join([
                "year: %{x}",
                "return: %{z}%",
            ])
        )

        fig.update_layout(
            height = 120,
            width= 800,
            margin=dict(l=20, r=270, t=40, b=40),
            yaxis={
                'visible': False,
            },
            title={
                'text': 'yearly return',
                'x': 0.025,
                'yanchor': 'top',
            },
            coloraxis_showscale=False,
            coloraxis={'cmid':0}
            )

        return fig

    def create_performance_figure(self, position):

        from plotly.subplots import make_subplots
        # plot performance

        def diff(s, period):
            return (s / s.shift(period) - 1)

        drawdowns = self.calc_dd(self.stock_data['portfolio_returns'])
        if hasattr(self, 'benchmark'):
            benchmark_drawdown = self.calc_dd(self.daily_benchmark['close'])
        performance_detail = self.stock_data.copy()
        nstocks = self.stock_data['company_count']

        fig = go.Figure(make_subplots(
            rows=4, cols=1, shared_xaxes=True, row_heights=[2, 1, 1, 1]))
        fig.add_scatter(x=performance_detail.index, y=round(performance_detail['cum_returns'] - 1, 2),
                        name='strategy', row=1, col=1, legendgroup='performance', fill='tozeroy')
        fig.add_scatter(x=drawdowns.index, y=drawdowns, name='strategy - drawdown',
                        row=2, col=1, legendgroup='drawdown', fill='tozeroy')
        fig.add_scatter(x=performance_detail.index, y=diff(performance_detail['portfolio_returns'], 20),
                        fill='tozeroy', name='strategy - month rolling return',
                        row=3, col=1, legendgroup='rolling performance', )
        
        # benchmark
        if hasattr(self, 'benchmark'):
            fig.add_scatter(x=performance_detail.index, y=self.daily_benchmark['close'] / 100 - 1,
                            name='benchmark', row=1, col=1, legendgroup='performance', line={'color': 'gray'})
            fig.add_scatter(x=drawdowns.index, y=benchmark_drawdown, name='benchmark - drawdown',
                            row=2, col=1, legendgroup='drawdown', line={'color': 'gray'})
            fig.add_scatter(x=performance_detail.index, y=diff(self.daily_benchmark['close'], 20),
                            fill='tozeroy', name='benchmark - month rolling return',
                            row=3, col=1, legendgroup='rolling performance', line={'color': 'rgba(0,0,0,0.2)'})

        fig.add_scatter(x=nstocks.index, y=nstocks, row=4,
                        col=1, name='nstocks', fill='tozeroy')

        fig.update_layout(legend={'bgcolor': 'rgba(0,0,0,0)'},
                          margin=dict(l=60, r=20, t=40, b=20),
                          height=600,
                          width=800,
                          xaxis4=dict(
                              rangeselector=dict(
                                  buttons=list([
                                      dict(count=1,
                                           label="1m",
                                           step="month",
                                           stepmode="backward"),
                                      dict(count=6,
                                           label="6m",
                                           step="month",
                                           stepmode="backward"),
                                      dict(count=1,
                                           label="YTD",
                                           step="year",
                                           stepmode="todate"),
                                      dict(count=1,
                                           label="1y",
                                           step="year",
                                           stepmode="backward"),
                                      dict(step="all")
                                  ]),
                                  x=0,
                                  y=1,
                              ),
                              rangeslider={'visible': True, 'thickness': 0.1},
                              type="date",
                          ),
                          yaxis={'tickformat': ',.0%', },
                          yaxis2={'tickformat': ',.0%', },
                          yaxis3={'tickformat': ',.0%', },
                          )
        return fig

    def calc_dd(self, daily_return):
        '''
        計算Drawdown的方式是找出截至當下的最大累計報酬(%)除以當下的累計報酬
        所以用累計報酬/累計報酬.cummax()

        return:
            dd : 每天的drawdown (可用來畫圖)
            mdd : 最大回落
            start : mdd開始日期
            end : mdd結束日期
            days : 持續時間
        '''
        # drawdown = self.stock_data['portfolio_returns'].copy()
        drawdown = daily_return.copy()

        # Fill NaN's with previous values
        drawdown = drawdown.ffill()

        # Ignore problems with NaN's in the beginning
        drawdown[np.isnan(drawdown)] = -np.Inf

        # Rolling maximum
        if isinstance(drawdown, pd.DataFrame):
            roll_max = pd.DataFrame()
            for col in drawdown:
                roll_max[col] = np.maximum.accumulate(drawdown[col])
        else:
            roll_max = np.maximum.accumulate(drawdown)

        drawdown = drawdown / roll_max - 1.0

        return drawdown

    def calc_cagr(self):
        '''
        計算CAGR用 (最終價值/初始價值) ^ (1/持有時間(年)) - 1
        那其實 最終價值/初始價值 跟「累計回報」會差不多，
        所以公式可以變為:累計報酬^(1/持有時間(年))-1

        return:
            cagr : 年均報酬率
        '''
        def year_frac(start, end):
            """
            Similar to excel's yearfrac function. Returns
            a year fraction between two dates (i.e. 1.53 years).
            Approximation using the average number of seconds
            in a year.
            Args:
                * start (datetime): start date
                * end (datetime): end date
            """
            if start > end:
                raise ValueError("start cannot be larger than end")

            # obviously not perfect but good enough
            return (end - start).total_seconds() / (31557600)
        
        daily_prices = self.stock_data['portfolio_returns'].resample("D").last().dropna()

        start = daily_prices.index[0]
        end = daily_prices.index[-1]
        # return (daily_prices.iloc[-1] / daily_prices.iloc[0]) ** (1 / year_frac(start, end)) - 1
        return (safe_division(daily_prices.iloc[-1], daily_prices.iloc[0])) ** safe_division(1, year_frac(start, end)) - 1

    def calc_return_table(self):
        self.return_table = {}
        obj = self.stock_data['portfolio_returns']
        daily_prices = obj.resample("D").last().dropna()
        # M = month end frequency
        monthly_prices = obj.resample("M").last()  # .dropna()
        # A == year end frequency
        yearly_prices = obj.resample("A").last()  # .dropna()

        # let's save some typing
        dp = daily_prices
        mp = monthly_prices
        yp = yearly_prices

        monthly_returns = mp / mp.shift(1) -1
        mr = monthly_returns

        for idx in mr.index:
            # use string keys for months to avoid mixed-type index issues in pandas
            year_key = idx.year
            if year_key not in self.return_table:
                # initialize months as strings '1'..'12'
                self.return_table[year_key] = {str(m): 0 for m in range(1, 13)}
            if not np.isnan(mr[idx]):
                self.return_table[year_key][str(idx.month)] = mr[idx]
        # add first month
        fidx = mr.index[0]
        try:
            self.return_table[fidx.year][str(fidx.month)] = float(mp.iloc[0]) / dp.iloc[0] - 1
        except ZeroDivisionError:
            self.return_table[fidx.year][str(fidx.month)] = 0
        # calculate the YTD values
        for idx in self.return_table:
            arr = np.array(list(self.return_table[idx].values()))
            self.return_table[idx]["YTD"] = np.prod(arr + 1) - 1

    def calc_sharpe(self, returns, rf=None, nperiods=None, annualize=True):
        """
        Calculates the `Sharpe ratio <https://www.investopedia.com/terms/s/sharperatio.asp>`_
        (see `Sharpe vs. Sortino <https://www.investopedia.com/ask/answers/010815/what-difference-between-sharpe-ratio-and-sortino-ratio.asp>`_).
        
        Args:
            * returns (Series, DataFrame): Input return series
            * rf (float, Series): `Risk-free rate` expressed as a yearly (annualized) return or return series.
                                  If None, tries to read from 'backend/src/backtest/risk_free_rate.csv'.
            * nperiods (int): Frequency of returns (252 for daily, 12 for monthly, etc.)
        """
        if rf is None:
            try:
                current_file = Path(__file__).resolve()
                # 假設結構是 backend/src/backtest/report.py，我們要去 backend/static/file/risk_free.csv
                # parents[0] = backtest, parents[1] = src, parents[2] = backend
                project_root = current_file.parents[2] 
                csv_path = project_root / 'static' / 'file' / 'risk_free.csv'

                # 預期格式: 證券代碼, 年月, 無風險利率
                # 嘗試多種編碼讀取 (utf-8, cp950/big5, utf-16)
                # 假設可能使用 \t 分隔
                try:
                    rf_df = pd.read_csv(csv_path, encoding='utf-8', sep=None, engine='python')
                except UnicodeDecodeError:
                    try:
                        rf_df = pd.read_csv(csv_path, encoding='cp950', sep=None, engine='python')
                    except UnicodeDecodeError:
                        rf_df = pd.read_csv(csv_path, encoding='utf-16', sep=None, engine='python')
                
                if '年月' in rf_df.columns and '無風險利率' in rf_df.columns:
                     rf_df['date'] = pd.to_datetime(rf_df['年月'].astype(str), format='%Y%m')
                     rf_df = rf_df.set_index('date').sort_index()
                     rf = rf_df['無風險利率'] / 100
                else:
                    print("risk_free.csv 欄位不符 (需有: 年月, 無風險利率)")
                    rf = 0.0
                
            except Exception as e:
                print(f"無風險利率讀取失敗: {e}")
                rf = 0.0

        if isinstance(rf, float) and rf != 0 and nperiods is None:
             raise Exception("Must provide nperiods if rf != 0")

        er = to_excess_returns(returns, rf, nperiods=nperiods)
        std = np.std(er, ddof=1)
        res = np.divide(er.mean(), max(std, 0.000001))

        if annualize:
            if nperiods is None:
                nperiods = 1
            sharpe_ratio = res * np.sqrt(nperiods)
        else:
            sharpe_ratio = res

        # Round the result to two decimal places
        return round(sharpe_ratio, 2)
    
    def calc_ytd(self, daily_prices, yearly_prices):
        if len(yearly_prices) == 1:
            return daily_prices.iloc[-1] / daily_prices.iloc[0] - 1
        else:
            return daily_prices.iloc[-1] / yearly_prices.iloc[-2] - 1

    def get_stats(self):
        obj = self.stock_data['portfolio_returns']
        daily_prices = obj.resample("D").last().dropna()
        # M = month end frequency
        monthly_prices = obj.resample("M").last()  # .dropna()
        # A == year end frequency
        yearly_prices = obj.resample("A").last()  # .dropna()

        # let's save some typing
        dp = daily_prices
        mp = monthly_prices
        yp = yearly_prices

        trades = self.trades.dropna()

        stats = {}
        # stats["daily_mean"] = dr.mean() * 252
        stats["CAGR"] = self.calc_cagr()
        stats['daily_sharpe'] = self.calc_sharpe(dp, nperiods=252)
        stats['max_drawdown'] = self.calc_dd(self.stock_data['portfolio_returns']).min()
        stats['avg_drawdown'] = self.calc_dd(self.stock_data['portfolio_returns']).mean()
        stats['win_ratio'] = sum(trades['return'] > 0) / len(trades) if len(trades) != 0 else 0
        stats['ytd'] = self.calc_ytd(dp,yp)

        # 計算 Alpha 與 Beta
        if hasattr(self, 'daily_benchmark'):
            try:
                s_rets = dp.copy().pct_change().dropna()
                b_rets = self.daily_benchmark.copy().pct_change().dropna()
                
                if isinstance(b_rets, pd.DataFrame):
                    b_rets = b_rets.iloc[:, 0]
                
                common_index = s_rets.index.intersection(b_rets.index)
                if len(common_index) > 1:
                    s_rets = s_rets.loc[common_index]
                    b_rets = b_rets.loc[common_index]
                    
                    # 載入無風險利率 (比照 calc_sharpe 邏輯)
                    try:
                        current_file = Path(__file__).resolve()
                        project_root = current_file.parents[2] 
                        csv_path = project_root / 'static' / 'file' / 'risk_free.csv'
                        try:
                            rf_df = pd.read_csv(csv_path, encoding='utf-8', sep=None, engine='python')
                        except UnicodeDecodeError:
                            try:
                                rf_df = pd.read_csv(csv_path, encoding='cp950', sep=None, engine='python')
                            except UnicodeDecodeError:
                                rf_df = pd.read_csv(csv_path, encoding='utf-16', sep=None, engine='python')
                        
                        if '年月' in rf_df.columns and '無風險利率' in rf_df.columns:
                            rf_df['date'] = pd.to_datetime(rf_df['年月'].astype(str), format='%Y%m')
                            rf_df = rf_df.set_index('date').sort_index()
                            rf_annual = rf_df['無風險利率'] / 100
                            rf_daily = deannualize(rf_annual, 252)
                            rf_series = rf_daily.reindex(common_index, method='ffill').fillna(0.0)
                        else:
                            rf_series = pd.Series(0.0, index=common_index)
                    except:
                        rf_series = pd.Series(0.0, index=common_index)

                    # 1. 計算 Beta
                    # 公式: Correlation(策略, 大盤) * (策略標準差 / 大盤標準差)
                    corr = s_rets.corr(b_rets)
                    std_s = s_rets.std()
                    std_b = b_rets.std()
                    
                    if std_b != 0:
                        beta = corr * (std_s / std_b)
                    else:
                        beta = 0.0
                    
                    # 2. 計算 Jensen's Alpha
                    # 公式: Alpha = (Rp - Rf) - Beta * (Rm - Rf)
                    # 先計算年化平均報酬
                    avg_excess_s = (s_rets - rf_series).mean() * 252
                    avg_excess_b = (b_rets - rf_series).mean() * 252
                    
                    alpha = avg_excess_s - beta * avg_excess_b

                    stats['alpha'] = alpha
                    stats['beta'] = beta
                else:
                    stats['alpha'] = 0.0
                    stats['beta'] = 0.0
            except Exception as e:
                print(f"Alpha/Beta 計算失敗: {e}")
        else:
            print("無法計算 Alpha/Beta，缺少 Benchmark 資料")

        # 計算持股檔數統計
        if 'company_count' in self.stock_data:
            stats['avg_holdings'] = self.stock_data['company_count'].mean()
            stats['max_holdings'] = self.stock_data['company_count'].max()
        else:
            stats['avg_holdings'] = 0
            stats['max_holdings'] = 0

        return stats

    def display_return_treemap(self, company_info=None):
        df = self.trades.copy()
        df["cum_return"] =  (1 + df['return']).groupby(df['stock_id']).cumprod() - 1
        df = df.groupby('stock_id').last()
        df = df.reset_index()

        # fig = px.treemap(df, path=['stock_id'], values='cum_return',
        #          title='Treemap of Cumulative Returns by Stock',
        #          color='cum_return', color_continuous_scale='RdBu_r',color_continuous_midpoint=0,
        #          custom_data=['stock_id', 'cum_return'],
        #          width=1600,
        #          height=800)
        # fig.update_traces(textposition='middle center',
        #                 textfont_size=20,
        #                 texttemplate="%{label}<br>cum_return = %{customdata[1]:.2f}",
        #                 )

        # fig.show()
        

        company_info = company_info.copy() if isinstance(company_info, pd.DataFrame) else pd.DataFrame()

        if not company_info.empty:
            keep_cols = ['company_symbol', 'name', 'industry', 'subindustry']
            company_info = company_info[keep_cols].copy()
            df = df.merge(company_info, left_on='stock_id', right_on='company_symbol', how='left')
            df = df.drop(columns=['company_symbol'], errors='ignore')

        df['stock_label'] = np.where(
            df['name'] == df['stock_id'],
            df['stock_id'],
            df['stock_id'] + ' ' + df['name']
        )
        df["size"] = df["cum_return"].abs().clip(lower=1e-6)
        df['all'] = 'all'

        fig = px.treemap(
            df,
            path=['all', 'industry', 'subindustry', 'stock_label'],
            values='size',
            title='Treemap of Cumulative Returns by Stock',
            color='cum_return',
            color_continuous_scale='RdBu_r',
            color_continuous_midpoint=0,
            custom_data=['stock_id', 'name', 'industry', 'subindustry', 'cum_return'],
            width=1600,
            height=800,
        )
        fig.update_traces(
            textposition='middle center',
            textfont_size=20,
            texttemplate="%{label}<br>%{customdata[4]:.2%}",
            hovertemplate="<br>".join([
                "Industry: %{customdata[2]}",
                "Subindustry: %{customdata[3]}",
                "Stock ID: %{customdata[0]}",
                "Stock Name: %{customdata[1]}",
                "Cumulative Return: %{customdata[4]:.2%}",
                "<extra></extra>",
            ]),
        )
        # fig.update_layout(margin=dict(t=50, l=25, r=25, b=25))
        fig.show()

    def display_stock_return_barplot(self, company_info=None, xtick_fontsize=None):
        df = self.trades.copy()
        df["cum_return"] = (1 + df['return']).groupby(df['stock_id']).cumprod() - 1
        df = df.groupby('stock_id').last().reset_index()

        company_info = company_info.copy() if isinstance(company_info, pd.DataFrame) else pd.DataFrame()
        if not company_info.empty:
            keep_cols = ['company_symbol', 'name']
            company_info = company_info[keep_cols].copy()
            df = df.merge(company_info, left_on='stock_id', right_on='company_symbol', how='left')
            df = df.drop(columns=['company_symbol'], errors='ignore')

        if 'name' not in df.columns:
            df['name'] = df['stock_id']
        else:
            df['name'] = df['name'].fillna(df['stock_id'])

        df['stock_label'] = np.where(
            df['name'] == df['stock_id'],
            df['stock_id'],
            df['stock_id'] + ' ' + df['name']
        )

        df = df.sort_values('cum_return')

        plt.rcParams['font.family'] = 'Microsoft JhengHei'
        plt.rcParams['axes.unicode_minus'] = False

        fig, ax = plt.subplots(figsize=(12, 6))
        x_pos = np.arange(len(df))
        ax.bar(x_pos, df['cum_return'] * 100, color='steelblue', edgecolor='black', align='center')

        # choose fontsize automatically if not provided
        if xtick_fontsize is None:
            n = len(df)
            if n <= 20:
                fontsize = 10
            elif n <= 40:
                fontsize = 8
            elif n <= 80:
                fontsize = 7
            else:
                fontsize = 6
        else:
            fontsize = xtick_fontsize

        ax.set_xticks(x_pos)
        ax.set_xticklabels(df['stock_label'], rotation=45, ha='right', fontsize=fontsize)

        ax.set_xlabel('Stock')
        ax.set_ylabel('Return (%)')
        ax.set_title('Cumulative Return by Stock')

        fig.subplots_adjust(bottom=0.35)
        plt.show()

    def display_stock_return_histogram(self):
        df = self.trades.copy()
        df["cum_return"] = (1 + df['return']).groupby(df['stock_id']).cumprod() - 1
        df = df.groupby('stock_id').last().reset_index()

        data = (df['cum_return'] * 100).replace([np.inf, -np.inf], np.nan).dropna()
        if len(data) == 0:
            print("No valid data to plot histogram for cumulative returns")
            return

       
        bin_edges = np.histogram_bin_edges(data, bins='auto')

        if len(bin_edges) < 2:
            bin_edges = np.linspace(data.min(), data.max(), 11)

        plt.rcParams['font.family'] = 'Microsoft JhengHei'
        plt.rcParams['axes.unicode_minus'] = False
        plt.figure(figsize=(10, 6))
        plt.hist(data, bins=bin_edges, color='steelblue', edgecolor='black')
        plt.xlabel('Return (%)')
        plt.ylabel('Stock Count')
        plt.title('Histogram of Cumulative Returns by Stock')
        plt.tight_layout()
        plt.show()

    def display_each_trade_histogram(self, index = "return"):
        # index 有可能是:
        # position/period/return/mae/gmfe/bmfe/mdd/pdays
        # 假設你的dataframe名稱是trades_history
        
        df = self.trades.copy()
        
        # 檢查欄位是否存在
        if index not in df.columns:
            print(f"Column '{index}' not found in trades data.")
            return

        # 將return欄位的數值乘以100
        if(index == "position" or index == "return" or index == "mae" or index == "gmfe" or index == "bmfe" or index == "mdd" ):
            df[index] = df[index] * 100

        # 繪製直方圖
        plt.figure(figsize=(10, 6))
        
        # 移除 NaN 值以避免 np.histogram 錯誤
        data = df[index].dropna()
        
        if len(data) == 0:
            print(f"No valid data to plot histogram for {index}")
            return

        # 設置bins的數量
        bins = 30

        # 計算直方圖數據
        counts, bin_edges = np.histogram(data, bins=bins)

        # 根據值的正負設置顏色
        for i in range(len(counts)):
            if bin_edges[i] < 0:
                plt.bar(bin_edges[i], counts[i], width=bin_edges[i+1] - bin_edges[i], color='green', edgecolor='black')
            else:
                plt.bar(bin_edges[i], counts[i], width=bin_edges[i+1] - bin_edges[i], color='red', edgecolor='black')

        plt.xlabel(f'{index} of each trade(%)')
        plt.ylabel('Frequency(Count)')
        plt.title('Histogram of return with Different Colors for Positive and Negative Values')
        plt.show()

        # 計算各區間佔比
        total_count = len(data)
        percentages = {}

        # 計算各區間內數據佔總數據的比值
        thresholds = [-5, -10, -20]
        for threshold in thresholds:
            count = (data <= threshold).sum()
            percentages[threshold] = (count / total_count) * 100

        # 輸出結果
        for threshold, percentage in percentages.items():
            print(f"{threshold}% 占比: {percentage:.2f}%")
    
    def display_topN_cum_return_yearly(self, topN=5):
        trades_df = self.trades.copy()
        trades_df["cum_return"] =  (1 + trades_df['return']).groupby(trades_df['stock_id']).cumprod() - 1
        trades_df = trades_df.groupby('stock_id').last()
        trades_df = trades_df.reset_index()

        # 假設您有一個 DataFrame，命名為 df，其中包含每次交易的股票、收益等信息

        # 設定 entry_date 的型態為 datetime
        trades_df['entry_date'] = pd.to_datetime(trades_df['entry_date'])

        # 提取年份資訊
        trades_df['year'] = trades_df['entry_date'].dt.year

        # 計算每支股票的年度累積回報
        trades_df['cum_return'] = trades_df.groupby(['stock_id', 'year'])['return'].cumsum()
        # 選擇每年中累積回報最高的前N名股票
        top10_stocks = trades_df.groupby(['year', 'stock_id'])['cum_return'].last().reset_index()
        top10_stocks = top10_stocks.groupby('year').apply(lambda x: x.nlargest(topN, 'cum_return')).reset_index(drop=True)

 
        # Prepare the data
        years = top10_stocks['year'].unique()  # Get unique years
        stock_ids = sorted(top10_stocks['stock_id'].unique())  # Get unique stock IDs and sort them

        # Create a list to store bar traces for each stock
        traces = []

        for j, stock_id in enumerate(stock_ids):
            # Initialize a list to store returns for the current stock
            stock_returns = []
            for year in years:
                # Get the return for the current stock and year
                return_value = top10_stocks[(top10_stocks['year'] == year) & (top10_stocks['stock_id'] == stock_id)]['cum_return'].values
                # If there's a return value, append it to the list, otherwise append 0
                if len(return_value) > 0:
                    stock_returns.append(return_value[0])
                else:
                    stock_returns.append(0)
            # Create a bar trace for the current stock
            trace = go.Bar(
                x=years,
                y=stock_returns,
                name=f'Stock {stock_id}'
            )
            traces.append(trace)

        # Create the figure
        fig = go.Figure(data=traces)

        # Update layout
        fig.update_layout(
            barmode='stack',
            xaxis=dict(title='Year'),
            yaxis=dict(title='Cumulative Return'),
            title='Stacked Bar Chart of Cumulative Returns by Year'
        )

        # Show the plot
        fig.show()

    def display_annual_plot(self, index="company_count"):
        # 計算每年的績效指標，可帶入指標包含: company_count、cum_returns、portfolio_returns
        plt.plot(self.stock_data.index, self.stock_data[index], marker='o', linestyle='-', linewidth=1)  # 'o' 是點樣式, '-' 是線樣式
        plt.title(f'Plot of {index}')
        plt.xlabel('Time(year)')
        plt.ylabel(index)
        plt.grid(True)
        plt.show()


def create_multi_strategy_performance_figure(
    reports,
    include_benchmark=False,
    width=1000,
    height=750,
):
    """建立多策略比較圖，包含 cum returns、drawdown、period return。

    Args:
        reports (dict[str, Report] | list[Report]):
            多個 backtest.sim 回傳的 report 物件。
            若為 list/tuple，會自動命名為 strategy_1、strategy_2 ...。
        rolling_window (int): 保留相容性的參數，當前版本未使用。
        include_benchmark (bool): 是否額外繪製 benchmark (取第一個 report 的 benchmark)。
        width (int): 圖寬。
        height (int): 圖高。

    Returns:
        plotly.graph_objects.Figure
    """

    from plotly.subplots import make_subplots

    if isinstance(reports, Mapping):
        report_items = list(reports.items())
    elif isinstance(reports, Sequence):
        report_items = [(f"strategy_{idx}", rpt) for idx, rpt in enumerate(reports, start=1)]
    else:
        raise TypeError("reports 必須是 dict 或 list/tuple，內容為 backtest.sim 回傳物件")

    if len(report_items) == 0:
        raise ValueError("reports 不可為空")

    def calc_dd(series):
        s = series.copy().ffill()
        s[np.isnan(s)] = -np.Inf
        roll_max = np.maximum.accumulate(s)
        return s / roll_max - 1.0

    def map_signal_to_next_trading_days(signal_dates, trading_index):
        """將訊號日映射為其後第一個有盤交易日（strictly after）。"""
        signals = pd.DatetimeIndex(pd.to_datetime(signal_dates)).drop_duplicates().sort_values()
        trades = pd.DatetimeIndex(pd.to_datetime(trading_index)).drop_duplicates().sort_values()
        mapped = []

        for sig in signals:
            pos = trades.searchsorted(sig, side="right")
            if pos < len(trades):
                mapped.append(trades[pos])

        if len(mapped) == 0:
            return pd.DatetimeIndex([])
        return pd.DatetimeIndex(mapped).drop_duplicates().sort_values()

    def calc_period_returns_from_signals(series, signal_dates):
        """以訊號日後第一個交易日切分每一期，計算期報酬。"""
        s = series.copy()
        s.index = pd.to_datetime(s.index)
        s = s.sort_index().dropna()
        if len(s) == 0:
            empty = pd.Series(dtype="float64")
            return empty, pd.DatetimeIndex([]), pd.DatetimeIndex([])

        period_trade_dates = map_signal_to_next_trading_days(signal_dates, s.index)
        if len(period_trade_dates) < 2:
            empty = pd.Series(dtype="float64")
            return empty, pd.DatetimeIndex([]), pd.DatetimeIndex([])

        starts = pd.DatetimeIndex(period_trade_dates[:-1])
        ends = pd.DatetimeIndex(period_trade_dates[1:])
        start_vals = s.reindex(starts).to_numpy(dtype="float64")
        end_vals = s.reindex(ends).to_numpy(dtype="float64")

        # 使用位置對齊避免 pandas 以索引對齊造成布林長度不一致
        valid = np.isfinite(start_vals) & np.isfinite(end_vals) & (start_vals != 0)
        starts = starts[valid]
        ends = ends[valid]
        if len(starts) == 0:
            empty = pd.Series(dtype="float64")
            return empty, pd.DatetimeIndex([]), pd.DatetimeIndex([])

        period_returns = pd.Series((end_vals[valid] / start_vals[valid]) - 1.0, index=ends)
        return period_returns, starts, ends

    # 固定策略色盤，確保 legend 與所有子圖的 trace 顏色一致
    colorway = px.colors.qualitative.Plotly

    fig = go.Figure(
        make_subplots(
            rows=3,
            cols=1,
            shared_xaxes=False,
            row_heights=[2, 1, 1],
            subplot_titles=(
                "Cumulative Return",
                "Drawdown",
                "Period Return",
            ),
        )
    )

    for idx, (strategy_name, rpt) in enumerate(report_items):
        if not hasattr(rpt, "stock_data"):
            raise TypeError(f"{strategy_name} 並非有效的 report 物件 (缺少 stock_data)")

        perf = rpt.stock_data.copy()
        if "cum_returns" not in perf.columns or "portfolio_returns" not in perf.columns:
            raise ValueError(
                f"{strategy_name} 的 stock_data 缺少必要欄位 (cum_returns / portfolio_returns)"
            )

        portfolio_curve = perf["portfolio_returns"].copy()
        base_value = portfolio_curve.iloc[0]
        if base_value == 0:
            cum_ret = portfolio_curve * 0
        else:
            cum_ret = portfolio_curve / base_value - 1
        drawdown = calc_dd(perf["portfolio_returns"])
        period_ret, period_starts, period_ends = calc_period_returns_from_signals(
            portfolio_curve,
            rpt.position.index,
        )
        period_labels = [f"M{i}" for i in range(1, len(period_ret) + 1)]
        period_customdata = np.array(
            [[s.strftime("%Y-%m-%d"), e.strftime("%Y-%m-%d")] for s, e in zip(period_starts, period_ends)]
        ) if len(period_ret) else None
        strategy_color = colorway[idx % len(colorway)]

        fig.add_scatter(
            x=cum_ret.index,
            y=cum_ret,
            mode="lines",
            name=strategy_name,
            legendgroup=strategy_name,
            line={"color": strategy_color},
            row=1,
            col=1,
        )
        fig.add_scatter(
            x=drawdown.index,
            y=drawdown,
            mode="lines",
            name=f"{strategy_name} - drawdown",
            legendgroup=strategy_name,
            showlegend=False,
            line={"color": strategy_color},
            row=2,
            col=1,
        )
        fig.add_bar(
            x=period_labels,
            y=period_ret.values,
            name=f"{strategy_name} - period",
            legendgroup=strategy_name,
            showlegend=False,
            marker={"color": strategy_color},
            customdata=period_customdata,
            hovertemplate="<br>".join([
                "Period: %{x}",
                "Start: %{customdata[0]}",
                "End: %{customdata[1]}",
                "Return: %{y:.2%}",
                "<extra></extra>",
            ]),
            row=3,
            col=1,
        )

    if include_benchmark:
        first_report = report_items[0][1]
        if hasattr(first_report, "daily_benchmark"):
            benchmark_close = first_report.daily_benchmark["close"]
            benchmark_base = benchmark_close.iloc[0]
            benchmark_cum = benchmark_close / benchmark_base - 1 if benchmark_base != 0 else benchmark_close * 0
            benchmark_dd = calc_dd(benchmark_close)
            benchmark_period, benchmark_starts, benchmark_ends = calc_period_returns_from_signals(
                benchmark_close,
                first_report.position.index,
            )
            benchmark_labels = [f"M{i}" for i in range(1, len(benchmark_period) + 1)]
            benchmark_customdata = np.array(
                [[s.strftime("%Y-%m-%d"), e.strftime("%Y-%m-%d")] for s, e in zip(benchmark_starts, benchmark_ends)]
            ) if len(benchmark_period) else None

            fig.add_scatter(
                x=benchmark_cum.index,
                y=benchmark_cum,
                mode="lines",
                name="benchmark",
                line={"color": "gray", "dash": "dot"},
                row=1,
                col=1,
            )
            fig.add_scatter(
                x=benchmark_dd.index,
                y=benchmark_dd,
                mode="lines",
                name="benchmark - drawdown",
                line={"color": "gray", "dash": "dot"},
                showlegend=False,
                row=2,
                col=1,
            )
            fig.add_bar(
                x=benchmark_labels,
                y=benchmark_period.values,
                name="benchmark - period",
                marker={"color": "gray"},
                showlegend=False,
                customdata=benchmark_customdata,
                hovertemplate="<br>".join([
                    "Period: %{x}",
                    "Start: %{customdata[0]}",
                    "End: %{customdata[1]}",
                    "Return: %{y:.2%}",
                    "<extra></extra>",
                ]),
                row=3,
                col=1,
            )

    fig.add_hline(
        y=0,
        line_width=1,
        line_dash="dash",
        line_color="black",
        row=3,
        col=1,
    )

    fig.update_layout(
        template="plotly_white",
        legend={"bgcolor": "rgba(0,0,0,0)"},
        barmode="group",
        margin=dict(l=60, r=20, t=70, b=20),
        height=height,
        width=width,
        xaxis={"showticklabels": False},
        xaxis2={"showticklabels": False},
        xaxis3={"type": "category", "title": "Period (M1~MX)"},
        yaxis={"tickformat": ",.0%"},
        yaxis2={"tickformat": ",.0%"},
        yaxis3={"tickformat": ",.0%"},
    )

    return fig


# 用來安全進行除法的函數。如果分母 d 不等於零，則返回 n / d，否則返回 0。
def safe_division(n, d):
    return n / d if d else 0

# 用來將dataframe按照月份排列
def sort_month(df):
    month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    return df[month_order] 

def deannualize(returns, nperiods):
    """
    Convert return expressed in annual terms on a different basis.
    Args:
        * returns (float, Series, DataFrame): Return(s)
        * nperiods (int): Target basis, typically 252 for daily, 12 for
            monthly, etc.
    """
    return np.power(1 + returns, 1.0 / nperiods) - 1.0

def to_excess_returns(returns, rf, nperiods=None):
    """
    Given a series of returns, it will return the excess returns over rf.
    Args:
        * returns (Series, DataFrame): Returns
        * rf (float, Series): `Risk-free rate <https://www.investopedia.com/terms/r/risk-freerate.asp>`_ expressed as a yearly (annualized) return or return series
        * nperiods (int): Optional. If provided, will convert rf to different
            frequency using deannualize only if rf is a float
    Returns:
        * excess_returns (Series, DataFrame): Returns - rf
    """

    returns = returns.copy().pct_change().dropna()

    if isinstance(rf, pd.Series):
        if nperiods is not None:
            _rf = deannualize(rf, nperiods)
            _rf = _rf.reindex(returns.index, method='ffill')
            _rf = _rf.bfill().fillna(0.0)
        else:
            _rf = rf.reindex(returns.index, method='ffill').fillna(0.0)
            
    elif isinstance(rf, (float, int)) and rf != 0:
        if nperiods is not None:
            _rf = deannualize(rf, nperiods)
        else:
             _rf = rf
    else:
        _rf = 0.0
  
    return returns - _rf

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
