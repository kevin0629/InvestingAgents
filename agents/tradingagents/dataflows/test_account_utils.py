import os
import shutil
from datetime import datetime
from unittest.mock import patch

from tradingagents.dataflows.account_utils import (
    create_stock_holding,
    get_stock_account,
    update_stock_holding,
)
from tradingagents.dataflows.config import get_config



def run_account_utils_tests() -> None:
    config = get_config()
    strategy = f"test_strategy_{datetime.now().strftime('%Y%m%d')}"
    strategy_dir = os.path.join(config["project_dir"], "dataflows", "data_cache", strategy)

    # 1) 建立 signal
    orders_p1 = [
        {"symbol": "2330", "position": 0.35, "reason": "基本面改善"},
        {"symbol": "2454", "position": 0.25, "reason": "AI 需求"},
    ]
    signal_result = create_stock_holding(strategy=strategy, orders=orders_p1, signal_date="2025-02-03")
    assert signal_result["status"] == "success"

    # 2) 依回測結果更新 holding
    fake_report = {
        "strategy_name": strategy,
        "current_holdings": [
            {"stock_id": "2330", "position": 0.7, "entry_date": "2025-02-04"},
            {"stock_id": "2454", "position": 0.3, "entry_date": "2025-02-04"},
        ],
        "performance": {},
        "message": "ok",
    }

    with patch("tradingagents.dataflows.account_utils.get_backtest_report", return_value=fake_report):
        update_result_1 = update_stock_holding(strategy=strategy, signal_date="2025-02-03")

    assert update_result_1["status"] == "success"
    custom_mode_result = update_result_1["mode_results"]["custom_weight"]
    equal_mode_result = update_result_1["mode_results"]["equal_weight"]
    assert custom_mode_result["holding_count"] == 2
    assert equal_mode_result["holding_count"] == 2

    holding_after_1 = get_stock_account(strategy=strategy)
    assert holding_after_1["row_count"] == 2

    # 3) 同一期再次 create signal，應該觸發 signal 備份
    orders_p1b = [
        {"symbol": "2330", "position": -0.05, "reason": "略減碼"},
        {"symbol": "2317", "position": 0.20, "reason": "新增"},
    ]
    signal_result_2 = create_stock_holding(strategy=strategy, orders=orders_p1b, signal_date="2025-03-03")
    assert signal_result_2["status"] == "success"

    files_now = os.listdir(strategy_dir)
    assert "custom_weight" in files_now

    # 4) 第二輪更新 holding（更新前應備份 holding）
    with patch("tradingagents.dataflows.account_utils.get_backtest_report", return_value=fake_report):
        update_result_2 = update_stock_holding(strategy=strategy, signal_date="2025-03-03", trade_modes=["custom_weight"])

    assert update_result_2["status"] == "success"
    mode_result_2 = update_result_2["mode_results"]["custom_weight"]
    assert mode_result_2["backup_file"] != ""
    assert os.path.exists(mode_result_2["backup_file"])

    holding_after_2 = get_stock_account(strategy=strategy)
    assert holding_after_2["status"] == "success"
    assert holding_after_2["row_count"] >= 1

    print("[PASS] account_utils tests passed")

    # shutil.rmtree(strategy_dir, ignore_errors=True)
    # print(f"[CLEANUP] removed {strategy_dir}")


if __name__ == "__main__":
    run_account_utils_tests()
