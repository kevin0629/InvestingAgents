import os
import re
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from .config import get_config
from .stock_utils import get_next_trading_day_close_price

BANK_HEADERS = ["日期", "帳戶餘額"]
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


def _bank_csv_path(strategy: str, trade_mode: str) -> str:
    return os.path.join(_mode_dir(strategy, trade_mode), "bank_account.csv")


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


def _write_bank_row(strategy: str, trade_mode: str, date: str, bank_balance: float) -> None:
    path = _bank_csv_path(strategy, trade_mode)
    dataframe = _read_csv_df(path, BANK_HEADERS)
    new_row = pd.DataFrame([{"日期": date, "帳戶餘額": float(bank_balance)}], columns=BANK_HEADERS)
    updated_df = pd.concat([dataframe, new_row], ignore_index=True)
    updated_df.to_csv(path, index=False, encoding="utf-8-sig")


def _init_mode_bank_account(date: str, strategy: str, trade_mode: str, bank_balance: float) -> Dict[str, Any]:
    path = _bank_csv_path(strategy, trade_mode)
    dataframe = pd.DataFrame([{"日期": date, "帳戶餘額": float(bank_balance)}], columns=BANK_HEADERS)
    dataframe.to_csv(path, index=False, encoding="utf-8-sig")
    return {
        "status": "success",
        "trade_mode": trade_mode,
        "file_path": path,
        "latest": {"日期": date, "帳戶餘額": float(bank_balance)},
    }


def init_bank_account(
    date: str,
    strategy: str,
    bank_balance: int = 1_000_000,
    trade_modes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    modes = trade_modes or TRADE_MODES
    results = [_init_mode_bank_account(date=date, strategy=strategy, trade_mode=mode, bank_balance=bank_balance) for mode in modes]
    return {
        "status": "success",
        "message": f"策略 {strategy} 已初始化 {len(results)} 個銀行帳戶",
        "strategy": strategy,
        "trade_modes": modes,
        "results": results,
    }


def get_bank_account(strategy: str, trade_mode: str = "custom_weight") -> Dict[str, Any]:
    path = _bank_csv_path(strategy, trade_mode)
    rows = _read_csv_rows(path, BANK_HEADERS)
    latest = rows[-1] if rows else {"日期": "", "帳戶餘額": 0}
    return {
        "status": "success",
        "trade_mode": trade_mode,
        "file_path": path,
        "latest": latest,
        "row_count": len(rows),
        "rows": rows,
    }


def update_bank_account(date: str, strategy: str, bank_balance: float, trade_mode: str = "custom_weight") -> Dict[str, Any]:
    _write_bank_row(strategy=strategy, trade_mode=trade_mode, date=date, bank_balance=bank_balance)
    snapshot = get_bank_account(strategy, trade_mode=trade_mode)
    return {
        "status": "success",
        "message": f"策略 {strategy} ({trade_mode}) 銀行帳戶已更新",
        "trade_mode": trade_mode,
        "file_path": snapshot["file_path"],
        "latest": snapshot["latest"],
        "row_count": snapshot["row_count"],
    }


def _validate_date(date_str: str, field_name: str) -> Optional[str]:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return f"{field_name} 格式錯誤，需為 YYYY-MM-DD"
    return None


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
    trade_mode: str = "custom_weight",
) -> Dict[str, Any]:
    """建立單一交易模式的 signal CSV。"""
    return _create_signal_csv(strategy=strategy, trade_mode=trade_mode, orders=orders, signal_date=signal_date)

    if not isinstance(orders, list) or len(orders) == 0:
        return {"status": "error", "message": "orders 必須是非空 List[Dict]", "file_path": signal_path}

    try:
        datetime.strptime(signal_date, "%Y-%m-%d")
    except ValueError:
        return {"status": "error", "message": "signal_date 格式錯誤，需為 YYYY-MM-DD", "file_path": signal_path}

    payload_rows: List[Dict[str, Any]] = []
    position_sum = 0.0
    for index, order in enumerate(orders):
        if not isinstance(order, dict):
            return {"status": "error", "message": f"orders[{index}] 必須是 Dict", "file_path": signal_path}
        if "symbol" not in order or "position" not in order:
            return {"status": "error", "message": f"orders[{index}] 缺少 symbol 或 position", "file_path": signal_path}

        try:
            symbol = str(order.get("symbol", "")).strip()
            position = float(order.get("position"))
            reason = str(order.get("reason", ""))
        except Exception:
            return {"status": "error", "message": f"orders[{index}] 格式錯誤", "file_path": signal_path}

        if not symbol:
            return {"status": "error", "message": f"orders[{index}] symbol 不可為空", "file_path": signal_path}
        position_sum += position
        payload_rows.append({"商品": symbol, "部位": position, "訊號日期": signal_date, "買入理由": reason})

    if os.path.exists(signal_path):
        old_df = pd.read_csv(signal_path, encoding="utf-8-sig")
        old_signal_date = signal_date
        if not old_df.empty and "訊號日期" in old_df.columns:
            old_signal_date = str(old_df.iloc[0].get("訊號日期", signal_date))
        backup_path = os.path.join(_strategy_dir(strategy), f"signal_{old_signal_date}.csv")
        shutil.copyfile(signal_path, backup_path)

    signal_df = pd.DataFrame(payload_rows, columns=SIGNAL_HEADERS)
    signal_df.to_csv(signal_path, index=False, encoding="utf-8-sig")

    return {
        "status": "success",
        "message": f"策略 {strategy} signal 已建立，共 {len(payload_rows)} 檔",
        "file_path": signal_path,
        "updated_count": len(payload_rows),
        "position_sum": round(position_sum, 6),
        "updated_symbols": [row["商品"] for row in payload_rows],
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


def _apply_signal_to_holding(strategy: str, trade_mode: str, signal_date: str, bank_balance: float) -> Dict[str, Any]:
    mode_dir = _mode_dir(strategy, trade_mode)
    signal_path = _signal_csv_path(strategy, trade_mode)
    holding_path = _holding_csv_path(strategy, trade_mode)

    _ensure_csv_with_header(holding_path, HOLDING_HEADERS)
    if not os.path.exists(signal_path):
        return {
            "status": "error",
            "message": f"找不到 signal 檔：{os.path.basename(signal_path)}",
            "trade_mode": trade_mode,
            "signal_file": signal_path,
            "holding_file": holding_path,
        }

    signal_df = pd.read_csv(signal_path, encoding="utf-8-sig")
    if signal_df.empty:
        return {
            "status": "error",
            "message": "signal 檔為空，無法更新 holding",
            "trade_mode": trade_mode,
            "signal_file": signal_path,
            "holding_file": holding_path,
        }

    for required_col in SIGNAL_HEADERS:
        if required_col not in signal_df.columns:
            return {
                "status": "error",
                "message": f"signal 缺少欄位：{required_col}",
                "trade_mode": trade_mode,
                "signal_file": signal_path,
                "holding_file": holding_path,
            }

    bank_path = _bank_csv_path(strategy, trade_mode)
    if not os.path.exists(bank_path):
        _init_mode_bank_account(date=signal_date, strategy=strategy, trade_mode=trade_mode, bank_balance=bank_balance)

    holding_df = _read_csv_df(holding_path, HOLDING_HEADERS)

    backup_file = ""
    if not holding_df.empty:
        backup_file = os.path.join(mode_dir, f"holding_account_{signal_date}.csv")
        shutil.copyfile(holding_path, backup_file)

    for _, row in signal_df.iterrows():
        stock = str(row["stock"]).strip()
        delta_position = float(row["position"])
        entry_sig_date = str(row.get("entry_sig_date", signal_date)).strip()

        match_idx = holding_df.index[holding_df["stock"] == stock].tolist()
        if match_idx:
            idx = match_idx[0]
            old_position = float(holding_df.at[idx, "position"] or 0)
            holding_df.at[idx, "position"] = old_position + delta_position
            holding_df.at[idx, "entry_sig_date"] = entry_sig_date
            holding_df.at[idx, "exit_sig_date"] = ""
            holding_df.at[idx, "exit_date"] = ""
        else:
            new_row = {col: "" for col in HOLDING_HEADERS}
            new_row["stock"] = stock
            new_row["entry_sig_date"] = entry_sig_date
            new_row["position"] = delta_position
            new_row["period"] = 0
            new_row["return"] = 0.0
            new_row["mdd"] = 0.0
            new_row["mae"] = 0.0
            new_row["gmfe"] = 0.0
            new_row["bmfe"] = 0.0
            holding_df = pd.concat([holding_df, pd.DataFrame([new_row], columns=HOLDING_HEADERS)], ignore_index=True)

    holding_df["position"] = pd.to_numeric(holding_df["position"], errors="coerce").fillna(0.0)
    holding_df = holding_df[holding_df["position"] > 0].copy()
    total_position = float(holding_df["position"].sum()) if not holding_df.empty else 0.0
    if total_position > 1:
        return {
            "status": "error",
            "message": f"更新後部位加總不可超過 1，目前為 {round(total_position, 6)}",
            "trade_mode": trade_mode,
            "signal_file": signal_path,
            "holding_file": holding_path,
            "backup_file": backup_file,
        }

    bank_snapshot = get_bank_account(strategy=strategy, trade_mode=trade_mode)
    old_bank_balance = float(bank_snapshot["latest"].get("帳戶餘額", 0) or 0)
    if old_bank_balance <= 0 and bank_balance > 0:
        _init_mode_bank_account(date=signal_date, strategy=strategy, trade_mode=trade_mode, bank_balance=bank_balance)
        bank_snapshot = get_bank_account(strategy=strategy, trade_mode=trade_mode)
        old_bank_balance = float(bank_snapshot["latest"].get("帳戶餘額", 0) or 0)

    invested_amount = 0.0
    for idx in holding_df.index:
        stock = str(holding_df.at[idx, "stock"]).strip()
        position = float(holding_df.at[idx, "position"])
        entry_sig_date = str(holding_df.at[idx, "entry_sig_date"] or signal_date).strip()

        close_info = get_next_trading_day_close_price(stock, end_date=entry_sig_date)
        entry_date = str(close_info.get("date", signal_date))
        close_price = float(close_info.get("close", 0) or 0)

        parsed_sig = datetime.strptime(entry_sig_date, "%Y-%m-%d")
        parsed_entry = datetime.strptime(entry_date, "%Y-%m-%d")
        period = max((parsed_entry - parsed_sig).days, 0)

        holding_df.at[idx, "entry_date"] = entry_date
        holding_df.at[idx, "period"] = int(period)
        holding_df.at[idx, "return"] = round(ret, 4)
        holding_df.at[idx, "mdd"] = min(round(ret, 4), 0.0)
        holding_df.at[idx, "mae"] = min(round(ret, 4), 0.0)
        holding_df.at[idx, "gmfe"] = max(round(ret, 4), 0.0)
        holding_df.at[idx, "bmfe"] = max(round(ret, 4), 0.0)

        invested_amount += old_bank_balance * position

    holding_df = holding_df[HOLDING_HEADERS]
    holding_df.to_csv(holding_path, index=False, encoding="utf-8-sig")

    new_bank_balance = old_bank_balance - invested_amount
    bank_update = update_bank_account(
        date=signal_date,
        strategy=strategy,
        bank_balance=new_bank_balance,
        trade_mode=trade_mode,
    )
    updated_rows = _read_csv_rows(holding_path, HOLDING_HEADERS)

    signal_backup = os.path.join(mode_dir, f"signal_{signal_date}.csv")
    if os.path.exists(signal_backup):
        signal_backup = os.path.join(mode_dir, f"signal_{signal_date}_{datetime.now().strftime('%H%M%S')}.csv")
    shutil.move(signal_path, signal_backup)

    return {
        "status": "success",
        "message": f"策略 {strategy} ({trade_mode}) holding 已更新",
        "trade_mode": trade_mode,
        "signal_file": signal_path,
        "holding_file": holding_path,
        "backup_file": backup_file,
        "holding_count": len(holding_df),
        "position_sum": round(total_position, 6),
        "bank_before": round(old_bank_balance, 2),
        "bank_after": round(new_bank_balance, 2),
        "bank_update": bank_update,
        "signal_backup": signal_backup,
        "updated_holdings": updated_rows,
    }


def update_stock_holding(
    strategy: str,
    signal_date: str,
    orders: Optional[List[Dict[str, Any]]] = None,
    bank_balance: float = 1_000_000,
    trade_modes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    單一入口工具：
    1) 初始化銀行帳戶（若不存在）
    2) 依 trade mode 產生 signal（若提供 orders）
    3) 將 signal 套用到 holding 並更新銀行帳戶

    預設一次處理 2 種模式：
    - equal_weight
    - custom_weight
    """
    date_error = _validate_date(signal_date, "signal_date")
    if date_error:
        return {"status": "error", "message": date_error}

    modes = trade_modes or TRADE_MODES
    mode_results: Dict[str, Any] = {}

    for mode in modes:
        if mode not in TRADE_MODES:
            mode_results[mode] = {
                "status": "error",
                "message": f"不支援的 trade_mode: {mode}",
                "trade_mode": mode,
            }
            continue

        bank_path = _bank_csv_path(strategy, mode)
        if not os.path.exists(bank_path):
            _init_mode_bank_account(date=signal_date, strategy=strategy, trade_mode=mode, bank_balance=bank_balance)

        if orders is not None:
            signal_result = _create_signal_csv(strategy=strategy, trade_mode=mode, orders=orders, signal_date=signal_date)
            if signal_result.get("status") == "error":
                mode_results[mode] = signal_result
                continue

        apply_result = _apply_signal_to_holding(strategy=strategy, trade_mode=mode, signal_date=signal_date, bank_balance=bank_balance)
        mode_results[mode] = apply_result

    success_count = sum(1 for result in mode_results.values() if result.get("status") == "success")
    status = "success" if success_count == len(modes) else "partial_success"
    return {
        "status": status,
        "strategy": strategy,
        "signal_date": signal_date,
        "trade_modes": modes,
        "success_count": success_count,
        "mode_results": mode_results,
    }
