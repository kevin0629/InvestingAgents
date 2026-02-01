import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path
import plotly.graph_objs as go
import matplotlib.pyplot as plt

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

    def display(self):
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
        display(imp_stats)
        display(fig)
        display(yearly_return_fig)
        display(monthly_return_fig)
        if hasattr(self, 'current_trades'):
            display(self.current_trades)
    
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
            if idx.year not in self.return_table:
                self.return_table[idx.year] = {
                    1: 0,
                    2: 0,
                    3: 0,
                    4: 0,
                    5: 0,
                    6: 0,
                    7: 0,
                    8: 0,
                    9: 0,
                    10: 0,
                    11: 0,
                    12: 0,
                }
            if not np.isnan(mr[idx]):
                self.return_table[idx.year][idx.month] = mr[idx]
        # add first month
        fidx = mr.index[0]
        try:
            self.return_table[fidx.year][fidx.month] = float(mp.iloc[0]) / dp.iloc[0] - 1
        except ZeroDivisionError:
            self.return_table[fidx.year][fidx.month] = 0
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

    def display_reutrn_treemap(self):
        df = self.trades.copy()
        df["cum_return"] =  (1 + df['return']).groupby(df['stock_id']).cumprod() - 1
        df = df.groupby('stock_id').last()
        df = df.reset_index()

        fig = px.treemap(df, path=['stock_id'], values='cum_return',
                 title='Treemap of Cumulative Returns by Stock',
                 color='cum_return', color_continuous_scale='RdBu_r',color_continuous_midpoint=0,
                 custom_data=['stock_id', 'cum_return'],
                 width=1600,
                 height=800)
        fig.update_traces(textposition='middle center',
                        textfont_size=20,
                        texttemplate="%{label}<br>cum_return = %{customdata[1]:.2f}",
                        )

        fig.show()

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
