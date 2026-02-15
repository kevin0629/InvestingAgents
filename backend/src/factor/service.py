from typing import List, Optional
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import defaultdict
from dateutil.relativedelta import relativedelta
from src.format_data import get_each_company_report

class FactorService:
    def __init__(self, data_instance):
        self.data = data_instance

    def _normalize_end_date(self, end_date):
        if end_date is None:
            return datetime.now(tz=ZoneInfo("Asia/Taipei")).date()
        if isinstance(end_date, datetime):
            return end_date.date()
        if hasattr(end_date, "year") and hasattr(end_date, "month") and hasattr(end_date, "day"):
            return end_date
        return datetime.fromisoformat(end_date).date()

    def get_company_all_factors(self, company_symbol: str, end_date: str = None, num: int = 4):
        end_date = self._normalize_end_date(end_date)        
        data = get_each_company_report(self.data.raw_report_data, company_symbol)
        data = data[(data.release_date <= end_date) & (data.release_date > end_date - relativedelta(months=num*3))]
        data = self.aggregated(data)

        return data

    def aggregated(self, data):
        """
        Aggregate rows into separate tables for year/quarter/month.

        Returns a dict with keys factor_name
        """
        mapping = {
            'CR': '速動比率',
            'DBR': '負債比率',
            'DSI': '存貨週轉天數',
            'DSO': '應收帳款週轉天數',
            'QRYoY': '季營收年增率',
            'GM': '毛利率',
            'OPM': '營業利益率',
            'PM': '淨利率',
        }
        disable_list = ["MRYoY", "CRYoY", "ATR", "ER", "FCF"]

        # prepare containers for each requested grouping
        containers = {}

        for row in data.itertuples(index=True):
            if row[2] in disable_list:
                continue
            
            date = row[0]
            # release_date = row[1]
            factor_name = mapping.get(row[2], row[2])
            factor_value = row[3]

            # compute keys
            # year_key = f"{date.year}"
            quarter_key = f"{date.year}Q{((date.month - 1) // 3 + 1)}"

            if factor_name not in containers:
                containers[factor_name] = defaultdict(list)
            containers[factor_name][quarter_key] = factor_value

        return containers

    def get_company_factor_by_name(self, company_symbol: str, factor_name: str, end_date: str = None, num: int = 4):   
        end_date = self._normalize_end_date(end_date)       
        data = get_each_company_report(self.data.raw_report_data, company_symbol)
        data = data[(data.release_date <= end_date) & (data.release_date > end_date - relativedelta(months=num*3))]
        data = data[data["factor_name"].str.upper() == factor_name.upper()]
        
        data = self.aggregated(data)

        return data
    


    def dupont_analysis(self, company_symbol: str, end_date: str = None, num: int = 4):
        end_date = self._normalize_end_date(end_date)
        data = get_each_company_report(self.data.raw_report_data, company_symbol)
        data = data[(data.release_date <= end_date) & (data.release_date > end_date - relativedelta(months=num*3))]
        
        # 按日期和發布日期分組數據
        date_groups = defaultdict(lambda: {"date": None, "release_date": None, "factors": {}})
        
        for row in data.itertuples(index=True):
            date = row[0]
            release_date = row[1]
            factor_name = row[2]
            factor_value = row[3]
            
            # 使用季度鍵作為分組依據
            quarter_key = f"{date.year}Q{((date.month - 1) // 3 + 1)}"
            
            if date_groups[quarter_key]["date"] is None:
                date_groups[quarter_key]["date"] = date.isoformat()
                date_groups[quarter_key]["release_date"] = release_date.isoformat()
            
            # 儲存因子值
            if factor_name == "ROE":
                date_groups[quarter_key]["factors"]["ROE"] = factor_value
            elif factor_name == "PM":
                date_groups[quarter_key]["factors"]["PM"] = factor_value
            elif factor_name == "ATR":
                date_groups[quarter_key]["factors"]["ATR"] = factor_value / 100
            elif factor_name == "ER":
                date_groups[quarter_key]["factors"]["ER"] = factor_value / 100
        
        # 計算杜邦分析並格式化結果
        result_data = []
        for quarter_key in date_groups.keys():
            group = date_groups[quarter_key]
            factors = group["factors"]
            
            # 確保所有所需因子都存在
            if all(k in factors for k in ["ROE", "PM", "ATR", "ER"]):
                roe_actual = factors["ROE"]
                pm = factors["PM"]
                atr = factors["ATR"]
                er = factors["ER"]
                
                
                result_data.append({
                    "period": quarter_key,
                    "formula": f"{roe_actual}% = {pm}% × {round(atr, 4)} × {round(er, 4)}",
                })
        
        return {"dupont_analysis": result_data}