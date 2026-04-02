import os
import re
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .config import get_config
from .backtest_utils import get_backtest_report

SIGNAL_HEADERS = ["stock", "position", "entry_sig_date"]
HOLDING_HEADERS = [
    "stock",
    "entry_sig_date",
    "exit_sig_date",
    "entry_date",
    "exit_date",
    "period",
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


def _signal_csv_path(strategy: str, trade_mode: str) -> str:
    return os.path.join(_mode_dir(strategy, trade_mode), "signal.csv")


def _holding_csv_path(strategy: str, trade_mode: str) -> str:
    return os.path.join(_mode_dir(strategy, trade_mode), "holding_account.csv")


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


def _resolve_modes(trade_mode: Optional[str] = None, trade_modes: Optional[List[str]] = None) -> Tuple[List[str], Dict[str, Dict[str, Any]]]:
    if trade_modes is not None:
        modes = trade_modes
    elif trade_mode is not None:
        modes = [trade_mode]
    else:
        modes = TRADE_MODES

    mode_errors: Dict[str, Dict[str, Any]] = {}
    valid_modes: List[str] = []
    for mode in modes:
        if mode in TRADE_MODES:
            valid_modes.append(mode)
        else:
            mode_errors[mode] = {
                "status": "error",
                "message": f"不支援的 trade_mode: {mode}",
                "trade_mode": mode,
            }
    return valid_modes, mode_errors


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
            }
        )
    return normalized


def _prepare_mode_orders(orders: List[Dict[str, Any]], signal_date: str, trade_mode: str) -> List[Dict[str, Any]]:
    normalized_orders = _normalize_orders(orders, signal_date)
    if not normalized_orders:
        return []

    is_equal_mode = trade_mode.startswith("equal_weight")

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
    signal_path = _signal_csv_path(strategy=strategy, trade_mode=trade_mode)

    if not isinstance(orders, list) or len(orders) == 0:
        return {"status": "error", "message": "orders 必須是非空 List[Dict]", "file_path": signal_path}

    date_error = _validate_date(signal_date, "signal_date")
    if date_error:
        return {"status": "error", "message": date_error, "file_path": signal_path}

    try:
        payload_rows = _prepare_mode_orders(orders=orders, signal_date=signal_date, trade_mode=trade_mode)
    except Exception as exc:
        return {"status": "error", "message": str(exc), "file_path": signal_path}

    position_sum = float(sum(float(row["position"]) for row in payload_rows)) if payload_rows else 0.0

    if os.path.exists(signal_path):
        old_df = pd.read_csv(signal_path, encoding="utf-8-sig")
        old_signal_date = signal_date
        if not old_df.empty and "entry_sig_date" in old_df.columns:
            old_signal_date = str(old_df.iloc[0].get("entry_sig_date", signal_date))
        backup_path = os.path.join(_mode_dir(strategy, trade_mode), f"signal_{old_signal_date}.csv")
        shutil.copyfile(signal_path, backup_path)

    signal_df = pd.DataFrame(payload_rows, columns=SIGNAL_HEADERS)
    signal_df.to_csv(signal_path, index=False, encoding="utf-8-sig")

    return {
        "status": "success",
        "message": f"策略 {strategy} ({trade_mode}) signal 已建立，共 {len(payload_rows)} 檔",
        "trade_mode": trade_mode,
        "file_path": signal_path,
        "updated_count": len(payload_rows),
        "position_sum": round(position_sum, 6),
        "updated_symbols": [row["stock"] for row in payload_rows],
    }


def create_stock_holding(
    strategy: str,
    orders: List[Dict[str, Any]],
    signal_date: str,
    trade_mode: Optional[str] = None,
    trade_modes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """建立 signal CSV。預設同時建立 equal_weight 與 custom_weight 兩種模式。"""
    date_error = _validate_date(signal_date, "signal_date")
    if date_error:
        return {"status": "error", "message": date_error}

    modes, mode_errors = _resolve_modes(trade_mode=trade_mode, trade_modes=trade_modes)
    mode_results: Dict[str, Any] = {**mode_errors}

    for mode in modes:
        mode_results[mode] = _create_signal_csv(
            strategy=strategy,
            trade_mode=mode,
            orders=orders,
            signal_date=signal_date,
        )

    success_count = sum(1 for result in mode_results.values() if result.get("status") == "success")
    status = "success" if success_count == len(mode_results) else "partial_success"
    return {
        "status": status,
        "strategy": strategy,
        "signal_date": signal_date,
        "trade_modes": list(mode_results.keys()),
        "success_count": success_count,
        "mode_results": mode_results,
    }


def get_stock_account(strategy: str) -> Dict[str, Any]:
    """先嘗試依 signal 更新 holding，再回傳最新持股清單。"""
    signal_path = _signal_csv_path(strategy, "custom_weight")
    holding_path = _holding_csv_path(strategy, "custom_weight")
    _ensure_csv_with_header(holding_path, HOLDING_HEADERS)

    # 若有 signal.csv，先執行更新流程
    if os.path.exists(signal_path):
        signal_df = pd.read_csv(signal_path, encoding="utf-8-sig")
        if not signal_df.empty and "entry_sig_date" in signal_df.columns:
            signal_date = str(signal_df.iloc[0].get("entry_sig_date", "")).strip()
            if signal_date:
                update_result = update_stock_holding(
                    strategy=strategy,
                    signal_date=signal_date,
                    trade_modes=["custom_weight"],
                )
                if update_result.get("status") == "error":
                    return update_result

    rows = _read_csv_rows(holding_path, HOLDING_HEADERS)
    return {
        "status": "success",
        "file_path": holding_path,
        "rows": rows,
        "row_count": len(rows),
        "trade_mode": "custom_weight",
    }


def _build_holding_rows_from_backtest(current_holdings: List[Dict[str, Any]], signal_date: str, trade_mode: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for index, holding in enumerate(current_holdings):
        if not isinstance(holding, dict):
            raise ValueError(f"current_holdings[{index}] 格式錯誤，必須是 Dict")

        stock = str(holding.get("stock_id") or holding.get("stock") or "").strip()
        if not stock:
            raise ValueError(f"current_holdings[{index}] 缺少 stock_id")

        raw_position = holding.get("position", 0)
        try:
            position = float(raw_position or 0)
        except (TypeError, ValueError):
            raise ValueError(f"current_holdings[{index}] position 無法轉為數值")

        entry_date = str(holding.get("entry_date") or signal_date).strip()[:10]
        if _validate_date(entry_date, f"current_holdings[{index}].entry_date"):
            entry_date = signal_date

        parsed_sig = datetime.strptime(signal_date, "%Y-%m-%d")
        parsed_entry = datetime.strptime(entry_date, "%Y-%m-%d")
        period = max((parsed_entry - parsed_sig).days, 0)

        rows.append(
            {
                "stock": stock,
                "entry_sig_date": signal_date,
                "exit_sig_date": "",
                "entry_date": entry_date,
                "exit_date": "",
                "period": int(period),
                "position": round(position, 6),
                "return": 0.0,
                "mdd": 0.0,
                "mae": 0.0,
                "gmfe": 0.0,
                "bmfe": 0.0,
            }
        )

    rows = [row for row in rows if row["position"] > 0]
    if trade_mode.startswith("equal_weight") and rows:
        equal_position = round(1.0 / len(rows), 6)
        for row in rows:
            row["position"] = equal_position

    total_position = sum(row["position"] for row in rows)
    if rows and total_position > 1.000001:
        normalized_ratio = 1.0 / total_position
        for row in rows:
            row["position"] = round(row["position"] * normalized_ratio, 6)

    return rows


def _apply_backtest_to_holding(
    strategy: str,
    trade_mode: str,
    signal_date: str,
    report_data: Dict[str, Any],
) -> Dict[str, Any]:
    mode_dir = _mode_dir(strategy, trade_mode)
    signal_path = _signal_csv_path(strategy, trade_mode)
    holding_path = _holding_csv_path(strategy, trade_mode)

    _ensure_csv_with_header(holding_path, HOLDING_HEADERS)
    existing_holding_df = _read_csv_df(holding_path, HOLDING_HEADERS)

    backup_file = ""
    if not existing_holding_df.empty:
        backup_file = os.path.join(mode_dir, f"holding_account_{signal_date}.csv")
        shutil.copyfile(holding_path, backup_file)

    current_holdings = report_data.get("current_holdings", []) if isinstance(report_data, dict) else []

    holding_rows = _build_holding_rows_from_backtest(
        current_holdings=current_holdings,
        signal_date=signal_date,
        trade_mode=trade_mode,
    )

    holding_df = pd.DataFrame(holding_rows, columns=HOLDING_HEADERS)
    if holding_df.empty:
        holding_df = pd.DataFrame(columns=HOLDING_HEADERS)

    holding_df.to_csv(holding_path, index=False, encoding="utf-8-sig")
    updated_rows = _read_csv_rows(holding_path, HOLDING_HEADERS)

    signal_backup = ""
    if os.path.exists(signal_path):
        signal_backup = os.path.join(mode_dir, f"signal_{signal_date}.csv")
        if os.path.exists(signal_backup):
            signal_backup = os.path.join(mode_dir, f"signal_{signal_date}_{datetime.now().strftime('%H%M%S')}.csv")
        shutil.move(signal_path, signal_backup)

    return {
        "status": "success",
        "message": f"策略 {strategy} ({trade_mode}) 依回測結果更新 holding 完成",
        "trade_mode": trade_mode,
        "signal_file": signal_path,
        "holding_file": holding_path,
        "backup_file": backup_file,
        "holding_count": len(holding_df),
        "position_sum": round(float(pd.to_numeric(holding_df.get("position", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()), 6),
        "backtest_message": report_data.get("message") if isinstance(report_data, dict) else "",
        "performance": report_data.get("performance") if isinstance(report_data, dict) else {},
        "signal_backup": signal_backup,
        "updated_holdings": updated_rows,
    }


def update_stock_holding(
    strategy: str,
    signal_date: str,
    orders: Optional[List[Dict[str, Any]]] = None,
    start_date: Optional[str] = None,
    trade_modes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    單一入口工具：
    1) 依 trade mode 產生 signal（若提供 orders）
    2) 呼叫 backtest report
    3) 將 current_holdings 寫入兩種 holding account

    預設一次處理 2 種模式：
    - equal_weight
    - custom_weight
    """
    date_error = _validate_date(signal_date, "signal_date")
    if date_error:
        return {"status": "error", "message": date_error}

    if start_date:
        start_date_error = _validate_date(start_date, "start_date")
        if start_date_error:
            return {"status": "error", "message": start_date_error}

    modes, mode_errors = _resolve_modes(trade_modes=trade_modes)
    mode_results: Dict[str, Any] = {**mode_errors}

    if not modes:
        return {
            "status": "error",
            "strategy": strategy,
            "signal_date": signal_date,
            "trade_modes": list(mode_results.keys()),
            "success_count": 0,
            "mode_results": mode_results,
            "message": "無有效 trade_mode 可執行",
        }

    report_data = get_backtest_report(
        strategy_name=strategy,
        start_date=start_date,
        end_date=signal_date,
    )

    for mode in modes:
        if orders is not None:
            signal_result = _create_signal_csv(strategy=strategy, trade_mode=mode, orders=orders, signal_date=signal_date)
            if signal_result.get("status") == "error":
                mode_results[mode] = signal_result
                continue

        apply_result = _apply_backtest_to_holding(
            strategy=strategy,
            trade_mode=mode,
            signal_date=signal_date,
            report_data=report_data,
        )
        mode_results[mode] = apply_result

    success_count = sum(1 for result in mode_results.values() if result.get("status") == "success")
    status = "success" if success_count == len(mode_results) else "partial_success"
    return {
        "status": status,
        "strategy": strategy,
        "signal_date": signal_date,
        "trade_modes": list(mode_results.keys()),
        "success_count": success_count,
        "mode_results": mode_results,
    }
