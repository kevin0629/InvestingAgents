import os
import re
import shutil
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd

from .config import get_config
from .stock_utils import get_next_trading_day_close_price

BANK_HEADERS = ["日期", "帳戶餘額"]
SIGNAL_HEADERS = ["商品", "部位", "訊號日期", "買入理由"]
HOLDING_HEADERS = [
    "商品",
    "部位",
    "股數",
    "均價",
    "成本金額",
    "現價",
    "市值",
    "手續費",
    "交易稅",
    "預估淨收付",
    "預估損益",
    "報酬率",
    "訊號日期",
    "買入理由",
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


def _bank_csv_path(strategy: str) -> str:
    return os.path.join(_strategy_dir(strategy), "bank_account.csv")


def _signal_csv_path(strategy: str) -> str:
    return os.path.join(_strategy_dir(strategy), "signal.csv")


def _holding_csv_path(strategy: str) -> str:
    return os.path.join(_strategy_dir(strategy), "holding_account.csv")


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


def _write_bank_row(strategy: str, date: str, bank_balance: float) -> None:
    path = _bank_csv_path(strategy)
    dataframe = _read_csv_df(path, BANK_HEADERS)
    new_row = pd.DataFrame([{"日期": date, "帳戶餘額": float(bank_balance)}], columns=BANK_HEADERS)
    updated_df = pd.concat([dataframe, new_row], ignore_index=True)
    updated_df.to_csv(path, index=False, encoding="utf-8-sig")


def init_bank_account(date: str, strategy: str, bank_balance: int = 1_000_000) -> str:
    path = _bank_csv_path(strategy)
    dataframe = pd.DataFrame([{"日期": date, "帳戶餘額": float(bank_balance)}], columns=BANK_HEADERS)
    dataframe.to_csv(path, index=False, encoding="utf-8-sig")
    return f"策略 {strategy} 銀行帳戶已初始化，日期: {date}, 帳戶餘額: {bank_balance}"


def get_bank_account(strategy: str) -> Dict[str, Any]:
    path = _bank_csv_path(strategy)
    rows = _read_csv_rows(path, BANK_HEADERS)
    latest = rows[-1] if rows else {"日期": "", "帳戶餘額": 0}
    return {
        "status": "success",
        "file_path": path,
        "latest": latest,
        "row_count": len(rows),
        "rows": rows,
    }


def update_bank_account(date: str, strategy: str, bank_balance: float) -> Dict[str, Any]:
    _write_bank_row(strategy=strategy, date=date, bank_balance=bank_balance)
    snapshot = get_bank_account(strategy)
    return {
        "status": "success",
        "message": f"策略 {strategy} 銀行帳戶已更新",
        "file_path": snapshot["file_path"],
        "latest": snapshot["latest"],
        "row_count": snapshot["row_count"],
    }


def create_stock_holding(strategy: str, orders: List[Dict[str, Any]], signal_date: str) -> Dict[str, Any]:
    """
    建立 signal CSV（僅包含 商品、部位、訊號日期、買入理由）。

    若同一期 signal 檔已存在，會先備份為：
    signal_{signal_date}_{原檔內訊號日期}.csv
    """
    signal_path = _signal_csv_path(strategy=strategy)

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
    signal_path = _signal_csv_path(strategy)
    holding_path = _holding_csv_path(strategy)
    _ensure_csv_with_header(holding_path, HOLDING_HEADERS)

    # 若有 signal.csv，先執行更新流程
    if os.path.exists(signal_path):
        signal_df = pd.read_csv(signal_path, encoding="utf-8-sig")
        if not signal_df.empty and "訊號日期" in signal_df.columns:
            signal_date = str(signal_df.iloc[0].get("訊號日期", "")).strip()
            if signal_date:
                update_result = update_stock_holding(strategy=strategy, signal_date=signal_date)
                if update_result.get("status") == "error":
                    return update_result

    rows = _read_csv_rows(holding_path, HOLDING_HEADERS)
    return {
        "status": "success",
        "file_path": holding_path,
        "rows": rows,
        "row_count": len(rows),
    }


def update_stock_holding(strategy: str, signal_date: str) -> Dict[str, Any]:
    """
    以 signal CSV 更新 holding CSV：
    - 更新前備份 holding（若非空）
    - 將 signal 的部位增減套用到 holding
    - 用 next trading day close price 計算 holding 各欄位
    - 計算本次交易損益並回寫銀行帳戶
    """
    strategy_dir = _strategy_dir(strategy)
    signal_path = _signal_csv_path(strategy)
    holding_path = _holding_csv_path(strategy)

    # 第一次更新：若 holding 不存在，先建立空 holding
    _ensure_csv_with_header(holding_path, HOLDING_HEADERS)

    if not os.path.exists(signal_path):
        return {
            "status": "error",
            "message": f"找不到 signal 檔：{os.path.basename(signal_path)}",
            "signal_file": signal_path,
            "holding_file": holding_path,
        }

    signal_df = pd.read_csv(signal_path, encoding="utf-8-sig")
    if signal_df.empty:
        return {
            "status": "error",
            "message": "signal 檔為空，無法更新 holding",
            "signal_file": signal_path,
            "holding_file": holding_path,
        }

    for required_col in SIGNAL_HEADERS:
        if required_col not in signal_df.columns:
            return {
                "status": "error",
                "message": f"signal 缺少欄位：{required_col}",
                "signal_file": signal_path,
                "holding_file": holding_path,
            }

    holding_df = _read_csv_df(holding_path, HOLDING_HEADERS)

    # 備份 holding（更新前且有資料）
    backup_file = ""
    if not holding_df.empty:
        sample_symbol = str(signal_df.iloc[0]["商品"])
        next_day_info = get_next_trading_day_close_price(sample_symbol, end_date=signal_date)
        backup_date = str(next_day_info.get("date", signal_date))
        backup_file = os.path.join(strategy_dir, f"holding_account_{backup_date}.csv")
        shutil.copyfile(holding_path, backup_file)

    # 套用 position 變化（可正可負）
    for _, row in signal_df.iterrows():
        symbol = str(row["商品"]).strip()
        delta_position = float(row["部位"])
        reason = str(row.get("買入理由", ""))

        match_idx = holding_df.index[holding_df["商品"] == symbol].tolist()
        if match_idx:
            idx = match_idx[0]
            old_position = float(holding_df.at[idx, "部位"] or 0)
            new_position = old_position + delta_position
            holding_df.at[idx, "部位"] = new_position
            holding_df.at[idx, "買入理由"] = reason
            holding_df.at[idx, "訊號日期"] = signal_date
        else:
            new_row = {col: 0 for col in HOLDING_HEADERS}
            new_row["商品"] = symbol
            new_row["部位"] = delta_position
            new_row["訊號日期"] = signal_date
            new_row["買入理由"] = reason
            holding_df = pd.concat([holding_df, pd.DataFrame([new_row], columns=HOLDING_HEADERS)], ignore_index=True)

    # 去除部位 <= 0 的標的
    holding_df["部位"] = pd.to_numeric(holding_df["部位"], errors="coerce").fillna(0.0)
    holding_df = holding_df[holding_df["部位"] > 0].copy()

    total_position = float(holding_df["部位"].sum()) if not holding_df.empty else 0.0
    if total_position > 1:
        return {
            "status": "error",
            "message": f"更新後部位加總不可超過 1，目前為 {round(total_position, 6)}",
            "signal_file": signal_path,
            "holding_file": holding_path,
            "backup_file": backup_file,
        }

    # 取得銀行帳戶與交易前總資產
    bank_snapshot = get_bank_account(strategy)
    old_bank_balance = float(bank_snapshot["latest"].get("帳戶餘額", 0) or 0)

    # 計算各欄位（以部位 * 舊現金作為資本配置，使用 next day close）
    new_market_value_total = 0.0
    for idx in holding_df.index:
        symbol = str(holding_df.at[idx, "商品"]).strip()
        position = float(holding_df.at[idx, "部位"])
        close_info = get_next_trading_day_close_price(symbol, end_date=signal_date)
        next_day = str(close_info.get("date", signal_date))
        close_price = float(close_info.get("close", 0) or 0)

        capital = old_bank_balance * position
        shares = (capital / close_price) if close_price > 0 else 0.0
        shares = int(shares)
        cost_amount = round(shares * close_price)
        fee = int(cost_amount * 0.001425)
        tax = int(cost_amount * 0.003)
        net = cost_amount - fee - tax
        pnl = net - cost_amount
        ret = (pnl / cost_amount * 100) if cost_amount else 0.0

        holding_df.at[idx, "股數"] = shares
        holding_df.at[idx, "均價"] = round(close_price, 4)
        holding_df.at[idx, "成本金額"] = cost_amount
        holding_df.at[idx, "現價"] = round(close_price, 4)
        holding_df.at[idx, "市值"] = cost_amount
        holding_df.at[idx, "手續費"] = fee
        holding_df.at[idx, "交易稅"] = tax
        holding_df.at[idx, "預估淨收付"] = int(net)
        holding_df.at[idx, "預估損益"] = int(pnl)
        holding_df.at[idx, "報酬率"] = round(ret, 2)
        holding_df.at[idx, "訊號日期"] = next_day

        new_market_value_total += cost_amount

    # 寫回 holding
    holding_df = holding_df[HOLDING_HEADERS]
    holding_df.to_csv(holding_path, index=False, encoding="utf-8-sig")

    # 更新銀行帳戶：剩餘現金 = 舊現金 - 部位投入資金
    new_bank_balance = old_bank_balance - new_market_value_total
    bank_update = update_bank_account(date=signal_date, strategy=strategy, bank_balance=new_bank_balance)
    updated_rows = _read_csv_rows(holding_path, HOLDING_HEADERS)

    # 成功更新後，將 signal.csv 歸檔，避免後續重複套用同一批 signal
    signal_backup = os.path.join(strategy_dir, f"signal_{signal_date}.csv")
    if os.path.exists(signal_backup):
        signal_backup = os.path.join(
            strategy_dir,
            f"signal_{signal_date}.csv",
        )
    shutil.move(signal_path, signal_backup)

    return {
        "status": "success",
        "message": f"策略 {strategy} holding 已更新",
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
