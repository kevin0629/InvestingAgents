# 從原本get_data.py節取出來的，更模組化
# 這些function是將原始DB TABLE的資料轉成get() api可用格式

import pandas as pd
from src.dataframe import CustomDataFrame
from datetime import datetime, timedelta

# Abstract API：
from talib import abstract


def format_price_data(raw_price_data, item):
    """
    格式化原始價格資料成樞紐表格式。

    參數：
    raw_price_data (DataFrame)：來自DB表格的原始價格資料。
    item (str)：要提取的項目（例如："open"、"high"、"low"、"close"、"volume"、"market_capital"）。

    返回：
    DataFrame：包含每家公司和日期的項目值的樞紐表。
    """
    selected_data = raw_price_data[["date", item, "company_symbol"]]
    pivot_data = selected_data.pivot_table(
        index="date", columns="company_symbol", values=item
    )
    return CustomDataFrame(pivot_data)


def format_report_data(raw_report_data, factor):
    """
    格式化原始報告資料成不同因子的DataFrame字典。

    參數：
    raw_report_data (DataFrame)：來自DB表格的原始報告資料。
    factor (str)：要提取的因子名稱。

    返回：
    dict：包含每家公司和日期的因子值的DataFrame字典。
    """
    factor_list = factor.split(",")
    dfs_by_id = {}
    for f in factor_list:
        # 使用不區分大小寫的方式比對 factor_name
        # 因為 DB 裡可能是 MRYoY，但輸入可能被轉為 MRYOY
        mask = raw_report_data["factor_name"].str.upper() == f.upper()
        temp_df = raw_report_data[mask].pivot(
            index=["date", "release_date"], columns="company_symbol", values="factor_value"
        )
        dfs_by_id[f] = CustomDataFrame(temp_df)

    return dfs_by_id


def handle_price_data(raw_price_data):
    """
    格式化原始價格資料成包含不同價格項目的字典。

    參數：
    raw_price_data (DataFrame)：來自DB表格的原始價格資料。

    返回：
    dict：包含"open"、"high"、"low"、"close"、"volume"和"market_capital"的DataFrame的字典。
    """
    all_open = format_price_data(raw_price_data, "open")
    all_high = format_price_data(raw_price_data, "high")
    all_low = format_price_data(raw_price_data, "low")
    all_close = format_price_data(raw_price_data, "close")
    all_volume = format_price_data(raw_price_data, "volume")
    all_market_capital = format_price_data(raw_price_data, "market_capital")
    all_price_dict = {
        "open": all_open,
        "high": all_high,
        "low": all_low,
        "close": all_close,
        "volume": all_volume,
        "market_capital": all_market_capital,
    }
    return all_price_dict


def get_each_company_daily_price(raw_price_data, company_symbol):
    """
    獲取特定公司的每日價格資料。

    參數：
    raw_price_data (DataFrame)：來自DB表格的原始價格資料。
    company_symbol (str)：要檢索資料的公司代號。

    返回：
    DataFrame：指定公司的每日價格資料。
    """
    filtered_df = raw_price_data[raw_price_data["company_symbol"] == company_symbol]
    filtered_df.set_index("date", inplace=True)
    filtered_df = filtered_df.sort_index(ascending=True)
    return filtered_df


def get_all_company_symbol(raw_price_data):
    """
    獲取原始價格資料中所有獨特的公司代號清單。

    參數：
    raw_price_data (DataFrame)：來自DB表格的原始價格資料。

    返回：
    list：獨特的公司代號清單。
    """
    unique_symbols = raw_price_data["company_symbol"].drop_duplicates()
    unique_symbols_list = unique_symbols.tolist()
    return unique_symbols_list


def get_number_of_indicator_return(indname, tmp_company_daily_price):
    """
    確定指標會回傳多少個DataFrame或單一值。

    Args:
    indname (str): 要計算的指標名稱。
    tmp_company_daily_price (pandas.DataFrame): 包含一間公司每日價格資料的DataFrame。

    Returns:
    int: 回傳值的數量，如果該指標回傳多個DataFrame，則為DataFrame的欄位數量；如果只回傳單一值，則為1。

    註解:
    - 此函數用於確定指標的回傳值數量，以便在後續處理中進行適當的資料處理。
    - 函數通過呼叫指定的指標函數（`indname`）來取得結果，然後檢查結果的型別來確定回傳值的數量。
    - 如果結果是DataFrame，則表示有多個回傳值，回傳其欄位數量。
    - 如果結果是Series，則表示只有單一回傳值，回傳1。
    """
    # 先根據該指標會回傳幾個DF來宣告
    # 隨便帶入一間公司做運算
    # tmp_company_daily_price = get_each_company_daily_price(self.raw_price_data, company_symbol)
    tmp_result = eval("abstract." + indname + "(tmp_company_daily_price)")
    if isinstance(tmp_result, pd.core.frame.DataFrame):
        # 如果是DataFrame，表示有多個回傳值
        num_of_return = tmp_result.shape[1]
        # print("回傳數量: ",num_of_return)
        return num_of_return
    elif isinstance(tmp_result, pd.Series):
        # 如果是Series，表示只有一個回傳值
        # 直接將該回傳值作為單一元素回傳
        # print("回傳數量: ",1)
        return 1

def adjust_index_of_report(df_dict):
    """
    根據索引日期調整財報資料字典中所有 DataFrame 的資料。
    
    參數：
    df_dict (dict[str, pd.DataFrame])：多個因子的資料字典。

    返回：
    dict[str, pd.DataFrame]：索引調整後的資料字典。
    """
    
    adjusted_dict = {}

    for factor, df in df_dict.items():
        # 複製一份以免修改到原始資料
        temp_df = df.copy()

        # 處理 Index，確保 date 和 release_date 變成 column
        # 預期輸入可能是 MultiIndex ['date', 'release_date']
        if isinstance(temp_df.index, pd.MultiIndex):
            temp_df = temp_df.reset_index()
        elif 'date' in temp_df.index.names and 'release_date' in temp_df.index.names:
             temp_df = temp_df.reset_index()

        # 確保需要的欄位存在才處理
        if 'date' in temp_df.columns and 'release_date' in temp_df.columns:
            temp_df['date'] = pd.to_datetime(temp_df['date'])
            temp_df['release_date'] = pd.to_datetime(temp_df['release_date'])

            # 1. 若 release_date 某日的值不是唯一，僅保留 date 較後面的資料
            temp_df = temp_df.sort_values(by=['release_date', 'date'])
            temp_df = temp_df.drop_duplicates(subset=['release_date'], keep='last')

            # 2. 針對 release_date 做觀察，每月如果有更早的日期都要被替換為該月日期最大的 release_date
            # 新增輔助欄位：月份
            temp_df['month_group'] = temp_df['release_date'].dt.to_period('M')
            # 找出每個月的最大 release_date
            monthly_max_dates = temp_df.groupby('month_group')['release_date'].transform('max')
            # 替換 release_date
            temp_df['release_date'] = monthly_max_dates
            # 移除輔助欄位
            temp_df = temp_df.drop(columns=['month_group'])

            # 合併同一 release_date 的資料，保留最後一筆非 NaN 的值 (達到將資料較少的 row 移動到資料較多的 row 的效果)
            temp_df = temp_df.groupby('release_date').last()

            # 3. 只將 release_date 設為 index，date 可以捨棄
            temp_df = temp_df.drop(columns=['date'])
            temp_df = temp_df.sort_index()
        
        adjusted_dict[factor] = CustomDataFrame(temp_df)

    return adjusted_dict

# def adjust_index_of_report(df_dict):
#     """
#     調整財報資料字典中所有 DataFrame 的索引日期。
    
#     參數：
#     df_dict (dict[str, pd.DataFrame])：多個因子的資料字典。

#     返回：
#     dict[str, pd.DataFrame]：索引調整後的資料字典。
#     """
    
#     adjusted_dict = {}

#     for factor, df in df_dict.items():
#         df = df.copy()
#         df.index = pd.to_datetime(df.index)

#         new_index = []
#         for current_date in df.index:
#             if current_date.month == 3:
#                 new_date = current_date.replace(month=5, day=15)
#             elif current_date.month == 6:
#                 new_date = current_date.replace(month=8, day=31)
#             elif current_date.month == 9:
#                 new_date = current_date.replace(month=11, day=15)
#             elif current_date.month == 12:
#                 new_date = (current_date + timedelta(days=90)).replace(day=31)
#             else:
#                 new_date = current_date
#             new_index.append(new_date)

#         df.index = new_index
#         adjusted_dict[factor] = df

#     return adjusted_dict


# if __name__ == "__main__":
