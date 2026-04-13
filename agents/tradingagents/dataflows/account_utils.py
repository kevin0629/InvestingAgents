import os
import re
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .config import get_config
from .backtest_utils import get_backtest_sim

SIGNAL_HEADERS = [
    "stock",
    "position",
    "entry_sig_date",
    "buy_reason",
    "growth_score",
    "value_score",
    "turnaround_score",
]
HOLDING_HEADERS = [
    "stock",
    "buy_reason",
    "growth_score",
    "value_score",
    "turnaround_score",
    "entry_sig_date",
    "exit_sig_date",
    "entry_date",
    "exit_date",
    "period",
    "entry_price",
    "exit_price",
    "position",
    "return",
    "mdd",
    "mae",
    "gmfe",
    "bmfe",
]

TRADE_MODES = [
    "equal_weight",
    "custom_weight",
    "equal_weight_without_reflection",
    "custom_weight_without_reflection",
]


def _data_cache_dir() -> str:
    config = get_config()
    cache_dir = os.path.join(config["project_dir"], "dataflows", "data_cache")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def _sanitize_strategy(strategy: str) -> str:
    strategy_name = str(strategy or "default").strip().lower()
    strategy_name = re.sub(r"[^a-zA-Z0-9_-]", "_", strategy_name)
    return strategy_name or "default"


def _strategy_dir(strategy: str) -> str:
    strategy_dir = os.path.join(_data_cache_dir(), _sanitize_strategy(strategy))
    os.makedirs(strategy_dir, exist_ok=True)
    return strategy_dir


def _mode_dir(strategy: str, trade_mode: str) -> str:
    mode_dir = os.path.join(_strategy_dir(strategy), _sanitize_strategy(trade_mode))
    os.makedirs(mode_dir, exist_ok=True)
    return mode_dir


def _signal_csv_path_by_date(strategy: str, trade_mode: str, signal_date: str) -> str:
    date_token = signal_date.replace("-", "")
    return os.path.join(_mode_dir(strategy, trade_mode), f"signal_{date_token}.csv")


def _latest_dated_signal_csv_path(strategy: str, trade_mode: str) -> Optional[str]:
    mode_dir = _mode_dir(strategy, trade_mode)
    candidate_files = [
        name for name in os.listdir(mode_dir)
        if re.fullmatch(r"signal_\d{8}\.csv", name)
    ]
    if not candidate_files:
        return None

    latest_file = sorted(candidate_files)[-1]
    return os.path.join(mode_dir, latest_file)


def _holding_csv_path_by_date(strategy: str, trade_mode: str, end_date: str) -> str:
    date_token = end_date.replace("-", "")
    return os.path.join(_mode_dir(strategy, trade_mode), f"holding_account_{date_token}.csv")


def _latest_dated_holding_csv_path(strategy: str, trade_mode: str) -> Optional[str]:
    mode_dir = _mode_dir(strategy, trade_mode)
    candidate_files = [
        name for name in os.listdir(mode_dir)
        if re.fullmatch(r"holding_account_\d{8}\.csv", name)
    ]
    if not candidate_files:
        return None

    latest_file = sorted(candidate_files)[-1]
    return os.path.join(mode_dir, latest_file)


def _ensure_csv_with_header(path: str, headers: List[str]) -> None:
    if os.path.exists(path):
        return
    pd.DataFrame(columns=headers).to_csv(path, index=False, encoding="utf-8-sig")


def _read_csv_df(path: str, headers: List[str]) -> pd.DataFrame:
    _ensure_csv_with_header(path, headers)
    dataframe = pd.read_csv(path, encoding="utf-8-sig")
    for header in headers:
        if header not in dataframe.columns:
            dataframe[header] = None
    return dataframe[headers]


def _read_csv_rows(path: str, headers: List[str]) -> List[Dict[str, Any]]:
    dataframe = _read_csv_df(path, headers)
    if dataframe.empty:
        return []
    dataframe = dataframe.where(pd.notnull(dataframe), "")
    return dataframe.to_dict(orient="records")


def _validate_date(date_str: str, field_name: str) -> Optional[str]:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return f"{field_name} 格式錯誤，需為 YYYY-MM-DD"
    return None


def _is_equal_weight_mode(trade_mode: str) -> bool:
    return trade_mode.startswith("equal_weight")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _normalize_date_value(raw_value: Any, fallback: str) -> str:
    text_value = str(raw_value or "").strip()[:10]
    if text_value and _validate_date(text_value, "date") is None:
        return text_value
    return fallback


def _extract_performance_return(dataframe: Any) -> str:
    if not isinstance(dataframe, pd.DataFrame) or dataframe.empty:
        return "0.0000%"

    if "position" not in dataframe.columns or "return" not in dataframe.columns:
        return "0.0000%"

    def _to_ratio(value: Any) -> float:
        if value is None:
            return 0.0

        text = str(value).strip()
        if not text:
            return 0.0

        is_percent = text.endswith("%")
        if is_percent:
            text = text[:-1].strip()

        try:
            numeric_value = float(text)
        except (TypeError, ValueError):
            return 0.0

        return numeric_value / 100.0 if is_percent else numeric_value

    position_series = pd.to_numeric(dataframe["position"], errors="coerce").fillna(0.0)
    return_series = dataframe["return"].apply(_to_ratio)
    weighted_return = float((position_series * return_series).sum())

    return f"{weighted_return * 100:.4f}%"


def _modes_by_reflection(reflection: bool) -> List[str]:
    if reflection:
        return ["equal_weight", "custom_weight"]
    return ["equal_weight_without_reflection", "custom_weight_without_reflection"]


def _previous_month_token(date_str: str) -> str:
    current = datetime.strptime(date_str, "%Y-%m-%d")
    if current.month == 1:
        year, month = current.year - 1, 12
    else:
        year, month = current.year, current.month - 1
    return f"{year:04d}{month:02d}"


def _signal_date_from_path(signal_path: str) -> Optional[str]:
    file_name = os.path.basename(signal_path)
    matched = re.fullmatch(r"signal_(\d{4})(\d{2})(\d{2})\.csv", file_name)
    if not matched:
        return None
    yyyy, mm, dd = matched.groups()
    return f"{yyyy}-{mm}-{dd}"


def _latest_dated_signal_csv_path_in_month(strategy: str, trade_mode: str, month_token: str) -> Optional[str]:
    mode_dir = _mode_dir(strategy, trade_mode)
    candidate_files = [
        name for name in os.listdir(mode_dir)
        if re.fullmatch(rf"signal_{month_token}\d{{2}}\.csv", name)
    ]
    if not candidate_files:
        return None

    latest_file = sorted(candidate_files)[-1]
    return os.path.join(mode_dir, latest_file)


def _normalize_orders(orders: List[Dict[str, Any]], signal_date: str) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for index, order in enumerate(orders):
        if not isinstance(order, dict):
            raise ValueError(f"orders[{index}] 必須是 Dict")

        stock = str(order.get("stock") or order.get("symbol") or "").strip()
        if not stock:
            raise ValueError(f"orders[{index}] stock 不可為空")

        position = float(order.get("position", 0) or 0)
        entry_sig_date = str(order.get("entry_sig_date") or signal_date).strip()
        date_error = _validate_date(entry_sig_date, f"orders[{index}].entry_sig_date")
        if date_error:
            raise ValueError(date_error)

        normalized.append(
            {
                "stock": stock,
                "position": position,
                "entry_sig_date": entry_sig_date,
                "buy_reason": str(order.get("buy_reason") or "").strip(),
                "growth_score": _safe_int(order.get("growth_score"), 0) or 0,
                "value_score": _safe_int(order.get("value_score"), 0) or 0,
                "turnaround_score": _safe_int(order.get("turnaround_score"), 0) or 0,
            }
        )
    return normalized


def _parse_orders_payload(parsed_orders: Any, signal_date: str) -> List[Dict[str, Any]]:
    """
    支援兩種 orders JSON 結構：
    1) 舊格式（向下相容）: {"2330": 0.35, "2454": 0.2}
    2) 新格式（推薦）:
       {
         "orders": [
                     {"stock": "2330", "position": 0.35, "buy_reason": "...", "growth_score": 8, "value_score": 6, "turnaround_score": 4},
                     {"stock": "2454", "position": 0.2, "buy_reason": "...", "growth_score": 7, "value_score": 5, "turnaround_score": 3}
         ]
       }
    """
    if isinstance(parsed_orders, dict) and isinstance(parsed_orders.get("orders"), list):
        parsed_order_rows: List[Dict[str, Any]] = []
        for index, order in enumerate(parsed_orders.get("orders") or []):
            if not isinstance(order, dict):
                raise ValueError(f"orders.orders[{index}] 必須是 Dict")

            stock = str(order.get("stock") or order.get("symbol") or "").strip()
            if not stock:
                raise ValueError(f"orders.orders[{index}] stock 不可為空")

            try:
                parsed_position = float(order.get("position", 0) or 0)
            except (TypeError, ValueError):
                raise ValueError(f"orders.orders[{index}].position 必須是數字")

            entry_sig_date = str(order.get("entry_sig_date") or signal_date).strip()
            date_error = _validate_date(entry_sig_date, f"orders.orders[{index}].entry_sig_date")
            if date_error:
                raise ValueError(date_error)

            parsed_order_rows.append(
                {
                    "stock": stock,
                    "position": parsed_position,
                    "entry_sig_date": entry_sig_date,
                    "buy_reason": str(order.get("buy_reason") or "").strip(),
                    "growth_score": _safe_int(order.get("growth_score"), 0) or 0,
                    "value_score": _safe_int(order.get("value_score"), 0) or 0,
                    "turnaround_score": _safe_int(order.get("turnaround_score"), 0) or 0,
                }
            )
        return parsed_order_rows

    if isinstance(parsed_orders, dict):
        parsed_order_rows = []
        for stock, position in parsed_orders.items():
            if stock == "orders":
                continue
            try:
                parsed_position = float(position)
            except (TypeError, ValueError):
                raise ValueError(f"orders[{stock}] 必須是數字")

            parsed_order_rows.append(
                {
                    "stock": str(stock),
                    "position": parsed_position,
                    "entry_sig_date": signal_date,
                    "buy_reason": "",
                    "growth_score": 0,
                    "value_score": 0,
                    "turnaround_score": 0,
                }
            )
        return parsed_order_rows

    raise ValueError(
        "orders JSON 必須是 Dict。建議格式: {\"orders\": [{\"stock\": \"2330\", \"position\": 0.35, \"buy_reason\": \"...\", \"growth_score\": 8, \"value_score\": 6, \"turnaround_score\": 4}]}"
    )


def _prepare_mode_orders(orders: List[Dict[str, Any]], signal_date: str, trade_mode: str) -> List[Dict[str, Any]]:
    normalized_orders = _normalize_orders(orders, signal_date)
    if not normalized_orders:
        return []

    is_equal_mode = _is_equal_weight_mode(trade_mode)

    if is_equal_mode:
        positive_stocks = [row for row in normalized_orders if row["position"] > 0]
        if positive_stocks:
            equal_position = round(1.0 / len(positive_stocks), 6)
            positive_names = {row["stock"] for row in positive_stocks}
            for row in normalized_orders:
                if row["stock"] in positive_names and row["position"] > 0:
                    row["position"] = equal_position

    return normalized_orders


def _create_signal_csv(strategy: str, trade_mode: str, orders: List[Dict[str, Any]], signal_date: str) -> Dict[str, Any]:
    dated_signal_path = _signal_csv_path_by_date(strategy=strategy, trade_mode=trade_mode, signal_date=signal_date)

    if not isinstance(orders, list) or len(orders) == 0:
        return {"status": "error", "message": "orders 必須是非空 List[Dict]", "file_path": dated_signal_path}

    date_error = _validate_date(signal_date, "signal_date")
    if date_error:
        return {"status": "error", "message": date_error, "file_path": dated_signal_path}

    try:
        payload_rows = _prepare_mode_orders(orders=orders, signal_date=signal_date, trade_mode=trade_mode)
    except Exception as exc:
        return {"status": "error", "message": str(exc), "file_path": dated_signal_path}

    position_sum = float(sum(float(row["position"]) for row in payload_rows)) if payload_rows else 0.0

    signal_df = pd.DataFrame(payload_rows, columns=SIGNAL_HEADERS)
    signal_df.to_csv(dated_signal_path, index=False, encoding="utf-8-sig")

    return {
        "status": "success",
        "message": f"策略 {strategy} ({trade_mode}) signal 已建立，共 {len(payload_rows)} 檔",
        "trade_mode": trade_mode,
        "file_path": dated_signal_path,
        "updated_count": len(payload_rows),
        "position_sum": round(position_sum, 6),
        "updated_symbols": [row["stock"] for row in payload_rows],
    }


def create_stock_holding(
    strategy: str,
    orders: str,
    signal_date: str,
    reflection: bool = False,
) -> Dict[str, Any]:
    """建立 signal CSV。支援舊格式與新格式 orders JSON。"""
    date_error = _validate_date(signal_date, "signal_date")
    if date_error:
        return {"status": "error", "message": date_error}

    try:
        parsed_orders = json.loads(orders)
    except json.JSONDecodeError:
        return {"status": "error", "message": "orders 必須為合法 JSON 字串"}

    try:
        parsed_order_rows = _parse_orders_payload(parsed_orders=parsed_orders, signal_date=signal_date)
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}

    if not parsed_order_rows:
        return {"status": "error", "message": "orders 不可為空"}

    modes = _modes_by_reflection(reflection)
    mode_results: Dict[str, Any] = {}

    for mode in modes:
        mode_results[mode] = _create_signal_csv(
            strategy=strategy,
            trade_mode=mode,
            orders=parsed_order_rows,
            signal_date=signal_date,
        )

    return "Successfully place orders with reflection!" if reflection else "Successfully place orders!"


def get_stock_account(strategy: str, end_date: str) -> Dict[str, Any]:
    """
    先依 end_date 執行 update_stock_holding，再回傳 custom_weight 最新 holding DataFrame。
    同時回傳上一期 signal_date（作為 distributor 的 start_date 來源）。
    """
    update_result = update_stock_holding(strategy=strategy, end_date=end_date)

    if update_result.get("status") == "error":
        return {
            "status": "error",
            "message": update_result.get("message", "update_stock_holding 失敗"),
            "trade_mode": "custom_weight",
            "file_path": "",
            "start_sig_date": "",
            "performance": {},
            "performance_return": "",
            "dataframe": pd.DataFrame(columns=HOLDING_HEADERS),
            "rows": [],
            "row_count": 0,
        }

    holding_path = _latest_dated_holding_csv_path(strategy, "custom_weight")
    if not holding_path or not os.path.exists(holding_path):
        return {
            "status": "success",
            "message": "custom_weight 無可用 holding 檔案",
            "trade_mode": "custom_weight",
            "file_path": "",
            "start_sig_date": str(update_result.get("signal_date") or ""),
            "performance": update_result.get("performance", {}),
            "performance_return": _extract_performance_return(pd.DataFrame(columns=HOLDING_HEADERS)),
            "dataframe": pd.DataFrame(columns=HOLDING_HEADERS),
            "rows": [],
            "row_count": 0,
        }

    dataframe = _read_csv_df(holding_path, HOLDING_HEADERS)
    rows = dataframe.where(pd.notnull(dataframe), "").to_dict(orient="records") if not dataframe.empty else []
    return {
        "status": "success",
        "message": "custom_weight holding 更新並載入完成",
        "trade_mode": "custom_weight",
        "file_path": holding_path,
        "start_sig_date": str(update_result.get("signal_date") or ""),
        "performance": update_result.get("performance", {}),
        "performance_return": _extract_performance_return(dataframe),
        "dataframe": dataframe,
        "rows": rows,
        "row_count": len(rows),
    }


def _load_signal_payload(
    strategy: str,
    trade_mode: str,
    signal_date: Optional[str] = None,
    signal_path: Optional[str] = None,
) -> Tuple[Optional[Dict[str, float]], Optional[Dict[str, str]], Optional[Dict[str, Dict[str, int]]], Optional[str]]:
    resolved_signal_path = signal_path
    if not resolved_signal_path:
        resolved_signal_path = _signal_csv_path_by_date(strategy, trade_mode, signal_date) if signal_date else _latest_dated_signal_csv_path(strategy, trade_mode)

    if not resolved_signal_path:
        return None, None, None, f"找不到可用的 signal: {trade_mode}"

    if not os.path.exists(resolved_signal_path):
        return None, None, None, f"找不到可用的 signal: {resolved_signal_path}"

    signal_df = _read_csv_df(resolved_signal_path, SIGNAL_HEADERS)
    if signal_df.empty:
        return None, None, None, f"找不到可用的 signal: {resolved_signal_path}"

    payload: Dict[str, float] = {}
    buy_reason_map: Dict[str, str] = {}
    kpi_score_map: Dict[str, Dict[str, int]] = {}
    for row in signal_df.to_dict(orient="records"):
        stock = str(row.get("stock") or "").strip()
        if not stock:
            continue
        payload[stock] = _safe_float(row.get("position"), 0.0)
        buy_reason_map[stock] = str(row.get("buy_reason") or "").strip()
        kpi_score_map[stock] = {
            "growth_score": _safe_int(row.get("growth_score"), 0) or 0,
            "value_score": _safe_int(row.get("value_score"), 0) or 0,
            "turnaround_score": _safe_int(row.get("turnaround_score"), 0) or 0,
        }

    if not payload:
        return None, None, None, "signal.csv 沒有可用股票資料"
    return payload, buy_reason_map, kpi_score_map, None


def _build_holding_rows_from_performance(
    holdings_performance: List[Dict[str, Any]],
    signal_date: str,
    buy_reason_map: Optional[Dict[str, str]] = None,
    kpi_score_map: Optional[Dict[str, Dict[str, int]]] = None,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for index, holding in enumerate(holdings_performance):
        if not isinstance(holding, dict):
            raise ValueError(f"holdings_performance[{index}] 格式錯誤，必須是 Dict")

        stock = str(holding.get("stock_id") or holding.get("stock") or "").strip()
        if not stock:
            raise ValueError(f"holdings_performance[{index}] 缺少 stock_id")

        rows.append(
            {
                "stock": stock,
                "buy_reason": str((buy_reason_map or {}).get(stock) or holding.get("buy_reason") or "").strip(),
                "growth_score": _safe_int((kpi_score_map or {}).get(stock, {}).get("growth_score", holding.get("growth_score")), 0) or 0,
                "value_score": _safe_int((kpi_score_map or {}).get(stock, {}).get("value_score", holding.get("value_score")), 0) or 0,
                "turnaround_score": _safe_int((kpi_score_map or {}).get(stock, {}).get("turnaround_score", holding.get("turnaround_score")), 0) or 0,
                "entry_sig_date": _normalize_date_value(holding.get("entry_sig_date"), signal_date),
                "exit_sig_date": str(holding.get("exit_sig_date") or ""),
                "entry_date": str(holding.get("entry_date") or signal_date),
                "exit_date": str(holding.get("exit_date") or ""),
                "period": _safe_int(holding.get("period"), 0),
                "entry_price": holding.get("entry_price"),
                "exit_price": holding.get("exit_price"),
                "position": holding.get("position"),
                "return": holding.get("return"),
                "mdd": holding.get("mdd"),
                "mae": holding.get("mae"),
                "gmfe": holding.get("gmfe"),
                "bmfe": holding.get("bmfe"),
            }
        )

    return rows


def _resolve_holding_rows(
    report_data: Dict[str, Any],
    signal_date: str,
    buy_reason_map: Optional[Dict[str, str]] = None,
    kpi_score_map: Optional[Dict[str, Dict[str, int]]] = None,
) -> List[Dict[str, Any]]:
    holdings_performance = report_data.get("holdings_performance", []) if isinstance(report_data, dict) else []
    return _build_holding_rows_from_performance(
        holdings_performance=holdings_performance,
        signal_date=signal_date,
        buy_reason_map=buy_reason_map,
        kpi_score_map=kpi_score_map,
    )


def _apply_backtest_to_holding(
    strategy: str,
    trade_mode: str,
    signal_date: str,
    report_data: Dict[str, Any],
    buy_reason_map: Optional[Dict[str, str]] = None,
    kpi_score_map: Optional[Dict[str, Dict[str, int]]] = None,
) -> Dict[str, Any]:
    holding_path = _holding_csv_path_by_date(strategy, trade_mode, signal_date)

    holding_rows = _resolve_holding_rows(
        report_data=report_data,
        signal_date=signal_date,
        buy_reason_map=buy_reason_map,
        kpi_score_map=kpi_score_map,
    )

    holding_df = pd.DataFrame(holding_rows, columns=HOLDING_HEADERS)
    if holding_df.empty:
        holding_df = pd.DataFrame(columns=HOLDING_HEADERS)

    holding_df.to_csv(holding_path, index=False, encoding="utf-8-sig")
    updated_rows = _read_csv_rows(holding_path, HOLDING_HEADERS)

    return {
        "status": "success",
        "message": f"策略 {strategy} ({trade_mode}) 依回測結果更新 holding 完成",
        "trade_mode": trade_mode,
        "holding_file": holding_path,
        "backup_file": "",
        "holding_count": len(holding_df),
        "position_sum": round(float(pd.to_numeric(holding_df.get("position", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()), 6),
        "backtest_message": report_data.get("message") if isinstance(report_data, dict) else "",
        "performance": report_data.get("performance") if isinstance(report_data, dict) else {},
        "updated_holdings": updated_rows,
    }


def update_stock_holding(
    strategy: str,
    end_date: str,
) -> Dict[str, Any]:
    """
    單一入口工具：
    1) 依 end_date 前一個月內 signal_YYYYMMDD.csv（取該月最新）
    2) 呼叫 /backtest/cal_performance 取得 holdings_performance
    3) 將回傳持股明細寫入 holding account

    只更新 signal 存在的 mode。
    """
    date_error = _validate_date(end_date, "end_date")
    if date_error:
        return {"status": "error", "message": date_error}

    previous_month = _previous_month_token(end_date)
    mode_results: Dict[str, Any] = {}
    mode_sim_reports: Dict[str, Dict[str, Any]] = {}
    updated_modes: List[str] = []
    mode_signal_dates: Dict[str, str] = {}

    for mode in TRADE_MODES:
        monthly_signal_path = _latest_dated_signal_csv_path_in_month(strategy, mode, previous_month)
        if not monthly_signal_path:
            # 依需求：該月無檔案就跳過，不視為錯誤
            continue

        signal_date = _signal_date_from_path(monthly_signal_path)
        if not signal_date:
            continue

        signal_payload, signal_buy_reasons, signal_kpi_scores, signal_error = _load_signal_payload(
            strategy=strategy,
            trade_mode=mode,
            signal_path=monthly_signal_path,
        )
        if signal_error:
            # 依需求：不存在就跳過，不視為錯誤
            continue

        try:
            report_data = get_backtest_sim(
                signal=signal_payload or {},
                entry_sig_date=signal_date,
                exit_sig_date=end_date,
            )
            mode_sim_reports[mode] = report_data
            mode_signal_dates[mode] = signal_date
        except Exception as exc:
            mode_results[mode] = {
                "status": "error",
                "trade_mode": mode,
                "message": f"cal_performance 失敗: {exc}",
            }
            continue

        apply_result = _apply_backtest_to_holding(
            strategy=strategy,
            trade_mode=mode,
            signal_date=end_date,
            report_data=report_data,
            buy_reason_map=signal_buy_reasons,
            kpi_score_map=signal_kpi_scores,
        )
        mode_results[mode] = apply_result
        updated_modes.append(mode)

    preferred_mode = "custom_weight"
    if mode_results.get(preferred_mode, {}).get("status") != "success":
        for mode in TRADE_MODES:
            if mode_results.get(mode, {}).get("status") == "success":
                preferred_mode = mode
                break

    selected_report = mode_sim_reports.get(preferred_mode, {})
    if not selected_report:
        return {
            "status": "error",
            "message": f"找不到 {previous_month} 月可更新 signal 檔案",
            "mode_results": mode_results,
        }

    return {
        "performance": selected_report.get("performance", {}),
        "holdings_performance": selected_report.get("holdings_performance", []),
        "updated_modes": updated_modes,
        "signal_date": mode_signal_dates.get(preferred_mode, ""),
    }


if __name__ == "__main__":
    strategy = "test_strategy"

    orders = json.dumps(
        {
            "2317": 0.5,
            "3491": 0.3,
        },
        ensure_ascii=False,
    )
    signal_date = "2025-03-03"

    create_result = create_stock_holding(strategy=strategy, orders=orders, signal_date=signal_date, reflection=False)
    # print(create_result)
    create_result = create_stock_holding(strategy=strategy, orders=orders, signal_date=signal_date, reflection=True)
    # print(create_result)

    update_result = get_stock_account(strategy=strategy, end_date="2025-04-10")
    print(update_result)
