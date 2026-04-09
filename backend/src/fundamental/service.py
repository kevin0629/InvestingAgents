from typing import List, Optional
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import defaultdict
import math
import pandas as pd
from dateutil.relativedelta import relativedelta
from src.format_data import get_each_company_fundamental, get_each_company_report


class IndicatorService:
    def __init__(self, data_instance):
        self.data = data_instance

    def _normalize_indicator_value(self, value):
        """Convert NaN/Inf-like values into None for JSON-safe response payloads."""
        if pd.isna(value):
            return None

        if isinstance(value, (int, float)):
            try:
                if not math.isfinite(float(value)):
                    return None
            except (TypeError, ValueError):
                return None

        return value

    def _normalize_end_date(self, end_date):
        if end_date is None:
            return datetime.now(tz=ZoneInfo("Asia/Taipei")).date()
        if isinstance(end_date, datetime):
            return end_date.date()
        if hasattr(end_date, "year") and hasattr(end_date, "month") and hasattr(end_date, "day"):
            return end_date
        return datetime.fromisoformat(end_date).date()

    def _quarter_keys_from_data(self, data, num):
        if data is None or data.empty:
            return []

        quarters = sorted({f"{d.year}Q{((d.month - 1) // 3 + 1)}" for d in data.index})
        return quarters[-num:]

    def _month_keys_from_data(self, data, num_months):
        if data is None or data.empty:
            return []

        month_keys = sorted({d.strftime("%Y/%m") for d in data.index})
        return month_keys[-num_months:]

    def _append_derived_indicator(self, data, left_name, right_name, new_name, operation="sum"):
        if data.empty:
            return data

        working = data.copy()
        pivot = working.pivot_table(
            index=working.index,
            columns="indicator_name",
            values="indicator_value",
            aggfunc="first",
        )

        if left_name not in pivot.columns or right_name not in pivot.columns:
            return working

        derived = pivot[[left_name, right_name]].copy()
        if operation == "sum":
            derived_value = derived[left_name] + derived[right_name]
        elif operation == "subtract":
            derived_value = derived[left_name] - derived[right_name]
        else:
            return working

        derived_value = derived_value.dropna()
        if derived_value.empty:
            return working

        derived_df = pd.DataFrame(
            {
                "indicator_name": new_name,
                "indicator_value": round(derived_value, 3),
            },
            index=derived_value.index,
        )

        working = working[working["indicator_name"] != new_name]
        return pd.concat([working, derived_df], axis=0)

    def get_company_balance_sheet(self, company_symbol: str, end_date: str = None, num: int = 4):
        end_date = self._normalize_end_date(end_date)
        data = get_each_company_fundamental(self.data.raw_fundamental, company_symbol)
        data = data[(data.release_date <= end_date) & (data.release_date > end_date - relativedelta(months=num*3))]
        indicator_list = [
            "現金及約當現金",
            "短期投資",
            "應收帳款及票據",
            "存貨",
            "流動資產",
            "長期投資",
            "不動產廠房及設備",
            "商譽及無形資產",
            "使用權資產",
            "非流動資產",
            "總資產",
            "合約負債",
            "流動負債",
            "非流動合約負債",
            "非流動負債",
            "總負債",
            "母公司股東權益合計",
            "非控制權益",
            "股東權益總額",
        ]
        data = data[data["indicator_name"].isin(indicator_list)]
        data = self._append_derived_indicator(data, "流動資產", "非流動資產", "總資產", operation="sum")
        data = self._append_derived_indicator(data, "流動負債", "非流動負債", "總負債", operation="sum")
        quarter_keys = self._quarter_keys_from_data(data, num)
        data = self.aggregated(data, indicator_order=indicator_list, period_keys=quarter_keys, period="quarter")

        return data

    def aggregated(self, data, indicator_order=None, period_keys=None, period="quarter"):
        """
        Aggregate rows into separate tables for year/quarter/month.

        Returns a dict with keys factor_name
        """

        # prepare containers for each requested grouping
        containers = {}

        if indicator_order is None:
            indicator_order = list(data["indicator_name"].drop_duplicates())
        if period_keys is None:
            if period == "month":
                period_keys = sorted(data.index.strftime("%Y/%m").unique()) if not data.empty else []
            else:
                period_keys = (
                    sorted({f"{d.year}Q{((d.month - 1) // 3 + 1)}" for d in data.index}) if not data.empty else []
                )
        allowed_period_keys = set(period_keys)

        for indicator in indicator_order:
            containers[indicator] = defaultdict(lambda: None)
            for key in period_keys:
                containers[indicator][key] = None

        for row in data.itertuples(index=True):
            date = row.Index
            factor_name = getattr(row, "indicator_name", None)
            factor_value = getattr(row, "indicator_value", None)
            factor_value = self._normalize_indicator_value(factor_value)

            if period == "month":
                period_key = date.strftime("%Y/%m")
            else:
                period_key = f"{date.year}Q{((date.month - 1) // 3 + 1)}"

            if period_key not in allowed_period_keys:
                continue

            if factor_name not in containers:
                containers[factor_name] = defaultdict(lambda: None)
                for key in period_keys:
                    containers[factor_name][key] = None
            containers[factor_name][period_key] = factor_value

        return containers

    def get_company_income_statement(self, company_symbol: str, end_date: str = None, num: int = 4):
        end_date = self._normalize_end_date(end_date)
        data = get_each_company_fundamental(self.data.raw_fundamental, company_symbol)
        data = data[(data.release_date <= end_date) & (data.release_date > end_date - relativedelta(months=num*3))]
        indicator_list = [
            "營業收入",
            "營業成本",
            "營業毛利",
            "營業費用",
            "研究發展費用",
            "營業利益",
            "財務成本",
            "稅前淨利",
            "所得稅費用",
            "稅後淨利",
            "歸屬母公司淨利",
            "歸屬非控制權益淨利",
        ]
        source_indicators = [name for name in indicator_list if name != "營業成本"]
        data = data[data["indicator_name"].isin(source_indicators)]
        data = self._append_derived_indicator(data, "營業收入", "營業毛利", "營業成本", operation="subtract")
        quarter_keys = self._quarter_keys_from_data(data, num)
        data = self.aggregated(data, indicator_order=indicator_list, period_keys=quarter_keys, period="quarter")

        return data
    
    def get_company_cash_flow_statement(self, company_symbol: str, end_date: str = None, num: int = 4):
        end_date = self._normalize_end_date(end_date)
        data = get_each_company_fundamental(self.data.raw_fundamental, company_symbol)
        data1 = get_each_company_report(self.data.raw_report_data, company_symbol)
        data1 = data1[(data1.release_date <= end_date) & (data1.release_date > end_date - relativedelta(months=num*3))]
        data = data[(data.release_date <= end_date) & (data.release_date > end_date - relativedelta(months=num*3))]

        indicator_list = [
            "營業現金流",
            "投資現金流",
            "購置不動產廠房設備",
            "獲得無形資產",
            "籌資現金流",
            "支付現金股利",
            "自由現金流",
        ]
        source_indicators = [name for name in indicator_list if name != "自由現金流"]
        data = data[data["indicator_name"].isin(source_indicators)]
        data1 = data1[data1["factor_name"] == "FCF"]
        data1["factor_name"] = "自由現金流"
        data1 = data1.rename(columns={"factor_name": "indicator_name", "factor_value": "indicator_value"})
        data = pd.concat([data, data1], axis=0)
        quarter_keys = self._quarter_keys_from_data(data, num)
        data = self.aggregated(data, indicator_order=indicator_list, period_keys=quarter_keys, period="quarter")

        return data
    
    def get_company_monthly_revenue(self, company_symbol: str, end_date: str = None, num: int = 4):
        end_date = self._normalize_end_date(end_date)
        data = get_each_company_fundamental(self.data.raw_fundamental, company_symbol)
        data1 = get_each_company_report(self.data.raw_report_data, company_symbol)
        data = data[(data.release_date <= end_date) & (data.release_date > end_date - relativedelta(months=(int(num/4)+1)*12))]
        data1 = data1[(data1.release_date <= end_date) & (data1.release_date > end_date - relativedelta(months=num*3))]

        indicator_list = ["當月營收", "月營收年增率", "累計營收", "累積營收年增率"]

        data = data[data["indicator_name"] == "當月營收"]
        monthly_revenue = data.copy()
        monthly_revenue = monthly_revenue.groupby(level=0)["indicator_value"].first().sort_index()
        monthly_revenue = monthly_revenue.dropna()
        monthly_revenue.index = pd.to_datetime(monthly_revenue.index, errors="coerce")
        monthly_revenue = monthly_revenue[~monthly_revenue.index.isna()]

        cumulative_revenue = monthly_revenue.groupby(monthly_revenue.index.year).cumsum().dropna()
        cumulative_revenue_df = pd.DataFrame(
            {
                "indicator_name": "累計營收",
                "indicator_value": round(cumulative_revenue, 3),
            },
            index=cumulative_revenue.index,
        )

        data1 = data1[data1["factor_name"].isin(["MRYoY", "CRYoY"])].copy()
        data1["factor_name"] = data1["factor_name"].map({"MRYoY": "月營收年增率", "CRYoY": "累積營收年增率"})
        data1 = data1.rename(columns={"factor_name": "indicator_name", "factor_value": "indicator_value"})
        data = pd.concat([data, cumulative_revenue_df, data1], axis=0)
        month_keys = self._month_keys_from_data(data, num * 3)

        return self.aggregated(data, indicator_order=indicator_list, period_keys=month_keys, period="month")