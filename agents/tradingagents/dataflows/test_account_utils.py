import os
import shutil
from datetime import datetime
from unittest.mock import patch

from tradingagents.dataflows.account_utils import (
    create_stock_holding,
    get_bank_account,
    get_stock_account,
    init_bank_account,
    update_stock_holding,
)
from tradingagents.dataflows.config import get_config


def _mock_next_close(symbol: str, end_date: str = None):
    return {
        "date": "2026-02-11",
        "close": {
            "2330": 1000.0,
            "2454": 500.0,
            "2317": 150.0,
        }.get(symbol, 100.0),
    }


def run_account_utils_tests() -> None:
    config = get_config()
    strategy = f"test_strategy_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    strategy_dir = os.path.join(config["project_dir"], "dataflows", "data_cache", strategy)

    print(f"[TEST] strategy = {strategy}")

    # 1) 初始化銀行帳戶
    init_msg = init_bank_account(date="2026-02-01", strategy=strategy, bank_balance=1000000)
    assert "已初始化" in init_msg

    # 2) 第一次先跑 update_stock_holding：此時沒有 signal，應回 error 且 holding 應是空檔
    first_update = update_stock_holding(strategy=strategy, signal_date="2026-02-03")
    assert first_update["status"] == "error"
    assert "找不到 signal 檔" in first_update["message"]

    empty_holding = get_stock_account(strategy=strategy)
    assert empty_holding["status"] == "success"
    assert empty_holding["row_count"] == 0

    # 3) 建立 signal（僅四欄）
    orders_p1 = [
        {"symbol": "2330", "position": 0.35, "reason": "基本面改善"},
        {"symbol": "2454", "position": 0.25, "reason": "AI 需求"},
    ]
    signal_result = create_stock_holding(strategy=strategy, orders=orders_p1, signal_date="2026-02-03")
    assert signal_result["status"] == "success"
    assert abs(signal_result["position_sum"] - 0.6) < 1e-9

    # 4) 第一輪更新 holding
    with patch("tradingagents.dataflows.account_utils.get_next_trading_day_close_price", side_effect=_mock_next_close):
        update_result_1 = update_stock_holding(strategy=strategy, signal_date="2026-02-03")
    assert update_result_1["status"] == "success"
    assert update_result_1["holding_count"] == 2
    assert update_result_1["backup_file"] == ""

    holding_after_1 = get_stock_account(strategy=strategy)
    assert holding_after_1["row_count"] == 2

    bank_after_1 = get_bank_account(strategy=strategy)
    assert bank_after_1["status"] == "success"
    assert float(bank_after_1["latest"]["帳戶餘額"]) <= 1_000_000

    # 5) 同一期再次 create signal，應該觸發 signal 備份
    orders_p1b = [
        {"symbol": "2330", "position": -0.05, "reason": "略減碼"},
        {"symbol": "2317", "position": 0.20, "reason": "新增"},
    ]
    signal_result_2 = create_stock_holding(strategy=strategy, orders=orders_p1b, signal_date="2026-02-03")
    assert signal_result_2["status"] == "success"

    files_now = os.listdir(strategy_dir)
    assert "signal.csv" in files_now
    assert any(name == "signal_2026-02-03.csv" for name in files_now)

    # 6) 第二輪更新 holding（更新前應備份 holding）
    with patch("tradingagents.dataflows.account_utils.get_next_trading_day_close_price", side_effect=_mock_next_close):
        update_result_2 = update_stock_holding(strategy=strategy, signal_date="2026-02-03")
    assert update_result_2["status"] == "success"
    assert update_result_2["backup_file"] != ""
    assert os.path.exists(update_result_2["backup_file"])

    holding_after_2 = get_stock_account(strategy=strategy)
    assert holding_after_2["status"] == "success"
    assert holding_after_2["row_count"] >= 1

    print("[PASS] account_utils tests passed")

    # shutil.rmtree(strategy_dir, ignore_errors=True)
    # print(f"[CLEANUP] removed {strategy_dir}")


if __name__ == "__main__":
    run_account_utils_tests()
