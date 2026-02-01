# 投資策略回測模組使用指南

本專案提供了兩大核心回測工具，位於 `backend/src/backtest/` 目錄下：
1. **`backtest.py`**：用於對單一策略信號進行詳細的歷史模擬。
2. **`combinations.py`**：用於同時測試多個策略條件，並比較它們的績效表現。

---

## 1. 單一策略回測 (`backtest.py`)

這是最基礎的回測引擎，核心函數為 `sim()`。它模擬在特定進出場訊號下的資產變化，並考慮手續費、稅金與滑價等成本。

### 核心函數：`sim()`

```python
from src.backtest.backtest import sim

# 假設 position 是一個 DataFrame，包含股票的進出場訊號 (True/False 或 1/0)
report = sim(position, resample='M', stop_loss=0.1, ...)
```

### 主要參數說明

| 參數 | 類型 | 說明 | 範例 |
| :--- | :--- | :--- | :--- |
| **`position`** | `DataFrame` | **(必填)** 進出場訊號表。`1`/`True` 代表持有，`0`/`False` 代表空手。這通常是策略計算後的布林值結果。 | `strategy_df` |
| **`resample`** | `str` | 換股頻率 (重平衡週期)。若不設定則依訊號變化交易。 | `'D'` (日), `'W'` (週), `'M'` (月), `'Q'` (季) |
| **`fee_ratio`** | `float` | 交易手續費率。預設為 `0.001425` (0.1425%)。 | `1.425/1000` |
| **`tax_ratio`** | `float` | 交易稅率。預設為 `0.003` (0.3%)。 | `3/1000` |
| **`stop_loss`** | `float` | 停損百分比。例如 10% 停損設為 `0.1`。 | `0.1` |
| **`take_profit`** | `float` | 停利百分比。例如 20% 停利設為 `0.2`。 | `0.2` |
| **`position_limit`** | `float` | 倉位限制 (總資金使用率)。預設為 `1` (不開槓桿，使用 100% 資金)。 | `1.0` |
| **`live_performance_start`**| `str` | 指定日期後為「樣本外」測試 (Live Performance)，在圖表上會區隔顯示。 | `'2023-01-01'` |

### 深入解析：換股機制與交易時機

很多人關心回測到底是在「哪一天」買賣？若是假日怎麼辦？以下直接引用 `src/backtest/backtest.py` 的程式碼來解釋其運作邏輯。

#### 1. 換股日期的產生 (Resampling)
當你有設定 `resample` 參數 (例如 `'M'`, `'W'`) 時，系統不會每天檢查訊號，而是只在特定的「換股日」進行部位調整。

程式碼片段 (`backtest.py`):
```python
# generate rebalance dates
alldates = pd.date_range(
    position.index[0], 
    position.index[-1] + datetime.timedelta(days=720), 
    freq=resample, tz=tz)

alldates += DateOffset(days=offset_days)
```
- **邏輯**：使用 pandas 的 `date_range` 函式，從策略訊號的第一天開始，依照你設定的頻率 (freq) 產生一系列的日期。
- **範例**：若 `resample='M'` (月終)，通常會產生每個月的最後一天 (如 1/31, 2/28, 3/31...)。

#### 2. 遇假日順延機制 (Holiday Handling)
產生的換股日如果是週六、週日或國定假日（沒有股價資料的日子），系統會如何處理？

程式碼片段 (`backtest.py` - `calc_essential_price`):
```python
def calc_essential_price(price, dates):
    # ... 省略部分代碼
    indexer = price.index.get_indexer(dates + dt)

    # 關鍵：若找不到該日期 (indexer == -1)，則往後找第一個存在的日期 (side='right')
    valid_idx = np.where(indexer == -1, np.searchsorted(price.index, dates, side='right'), indexer)
    # ...
```
- **邏輯**：系統會去比對股價資料 (`price.index`)。如果換股日當天沒有股價 (假日)，`np.searchsorted(..., side='right')` 會自動抓取**「下一個交易日」**作為實際執行交易的日期。
- **結論**：你不用擔心假日問題，回測引擎會自動在假日後的**次一個開盤日**以**開盤價** (或其他指定價格) 進行搓合。

#### 3. 訊號的對齊與填補 (Signal Alignment)
如果在換股日當天，原本的策略沒有產生訊號怎麼辦？

程式碼片段 (`backtest.py`):
```python
if dates is not None:
    position = position.reindex(dates, method='ffill')
```
- **邏輯**：系統會將你的訊號表 (`position`) 強制重新對齊 (reindex) 到上述計算出的換股日。
- **`ffill` (Forward Fill)**：若換股日當天原本沒有訊號，它會沿用**「最近一次」**的舊訊號。這確保了在定期換股時，我們是根據最新的已知狀態來決定持倉。

### 回傳物件：`Report`

`sim()` 函數執行後會回傳一個 `src.backtest.report.Report` 物件，你可以使用以下方法來分析結果：

*   **`report.display()`**: 最常用的方法。一次顯示績效指標表格、權益曲線圖、年度損益圖與月度損益熱力圖。
*   **`report.get_stats()`**: 取得詳細績效數據 (如 CAGR, Sharpe Ratio, Max Drawdown, Win Ratio 等) 的 Dictionary。
*   **`report.display_reutrn_treemap()`**: 以矩形式樹狀圖 (Treemap) 顯示各檔股票的累積貢獻。
*   **`report.display_each_trade_histogram(index='return')`**: 顯示每筆交易報酬率分佈的直方圖。

### 使用範例

```python
from src.backtest.backtest import sim

# 1. 準備策略訊號 (這裡假設已經算出 buy_signal)
# buy_signal = ... 

# 2. 執行回測：每週換股，停損 10%
report = sim(buy_signal, resample="W", stop_loss=0.1)

# 3. 顯示完整報告
report.display()

# 4. 進階分析：查看每筆交易的報酬分佈
report.display_each_trade_histogram()
```

---

## 2. 多策略比較與最佳化 (`combinations.py`)

當你想要「比較不同因子」或「測試同一策略的不同參數組合」時，使用這個模組可以一次跑完多個回測，並生成比較圖表。

### 核心函數：`sim_conditions()`

```python
from src.backtest.combinations import sim_conditions

report_collection = sim_conditions(conditions, resample='Q', ...)
```

### 主要參數說明

| 參數 | 類型 | 說明 |
| :--- | :--- | :--- |
| **`conditions`** | `dict` | 策略集合字典。Key 是策略名稱 (字串)，Value 是該策略的訊號 DataFrame。 |
| **`combination`** | `bool` | 是否要自動排列組合 (進階功能，預設 False)。 |
| **`*args`, `**kwargs`** | - | 其他參數會直接透傳給 `sim()` (如 `resample`, `stop_loss` 等)，這代表所有策略會在相同設定下進行比較。 |

### 回傳物件：`ReportCollection`

執行後會回傳一個 `ReportCollection` 物件，用於彙整與比較：

*   **`collection.plot_creturns()`**: 將所有策略的累積報酬率畫在同一張折線圖上，方便直觀比較走勢。
*   **`collection.get_stats()`**: 產生一個 DataFrame，列出所有策略的關鍵績效指標 (CAGR, Sharpe, MDD...)。
*   **`collection.plot_stats(mode='bar'|'heatmap')`**: 
    *   `mode='bar'`: 繪製指標分群長條圖。
    *   `mode='heatmap'`: 繪製指標熱力圖 (顏色越深代表表現越好)，方便快速篩選。

### 使用範例

假設你有兩個策略訊號 `strategy_low_pe` (低本益比) 和 `strategy_high_yield` (高殖利率)：

```python
from src.backtest.combinations import sim_conditions

# 1. 定義要比較的策略集合
strategies = {
    "Strategy A: Low P/E": strategy_low_pe,
    "Strategy B: High Yield": strategy_high_yield
}

# 2. 批量執行回測 (設定共同參數：每季換股)
collection = sim_conditions(strategies, resample="Q")

# 3. 畫出累積報酬率比較圖
fig = collection.plot_creturns()
fig.show()

# 4. 取得並顯示比較報表
stats_df = collection.get_stats()
print(stats_df)

# 5. 用熱力圖快速檢視
collection.plot_stats(mode='heatmap')
```

---

## 3. 總結：我該用哪一個？

| 你的需求 | 推薦工具 | 說明 |
| :--- | :--- | :--- |
| **深入分析單一策略** | `backtest.sim` | 當你已經確定好一個策略邏輯，需要仔細檢查它的損益曲線、每筆交易明細、歷年表現時。 |
| **比較多個策略優劣** | `combinations.sim_conditions` | 在研發初期，需要從多個因子中挑選表現最好的；或是想知道加上停損與不加停損的差別時。 |

---

## 4. 資金管理準則 (Capital Management)

### 起始資金 (Initial Capital)
本系統的核心運算均以 **「1 單位」 (即 100%)** 作為起始資金。
*   **相對比例**：這是一種標準化的回測方式 (Normalized Backtesting)，方便直接計算累積報酬率 (Cumulative Return)。
*   **實際金額**：您可以將此「1 單位」視為任何您實際操作的本金 (例如 100 萬元或 1,000 萬元)。
    *   例如：若回測結果顯示資產淨值成長至 `1.5`，代表報酬率為 50%。若您本金為 100 萬，則實際資產約為 150 萬。

### 複利機制 (Reinvestment)
本系統預設採用 **複利 (Compounding)** 模式，即「以錢滾錢」。
*   **全額再投入**：當進行換股 (Rebalance) 時，系統會計算當下的**總權益** (Total Equity = 現金餘額 + 股票現值)，並以此總額作為下一次佈局的基準。
*   **運作邏輯**：
    *   **獲利時**：若資產增值，下次進場所能購買的股數或權重規模會隨之增加。
    *   **虧損時**：若資產縮水，下次投入的規模也會自動縮減，具有自然的部位控管效果。
