## Prerequisite
* 下載 [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/zh-hant/visual-cpp-build-tools/) 
* 勾選以下套件並重新啟動電腦
    1. MSVC v143 - VS 2022 C++ x64/x86 建置工具
    2. Windows 11 SDK（視系統版本而定）
    3. 適用於Windows C++ 的 CMake 工具 
    4. 測試工具的核心功能 - 建置工具
    5. C++ AddressSanitizer
* 將`Microsoft C++ Build Tools`等相關設定新增到系統環境變數 [參考](https://github.com/bycloudai/InstallVSBuildToolsWindows)
* 安裝 TA-LIB到TA-LIB資料夾中
    1. [前往此網址]https://github.com/cgohlke/talib-build/releases
    2. 安裝對應版本的whl檔到TA-LIB資料夾中 (假設是3.10版本就下載ta_lib-0.6.3-cp310-cp310-win_amd64.whl)
    3. 更改專案資料夾中`requirement.txt`的內容，`TA-Lib @ file:///D:/<路徑>/pandas-ta/<檔案全名.whl>`
    4. 更改專案資料夾中`requirement.txt`的內容，`TA-Lib @ file:///D:/<路徑>/TA-LIB/<檔案全名.whl>`
* 安裝 Python 3.7 ~ 3.11版本(這是由於Ta-Lib、finlab library只有支援到這些版本，使用python3.12版finlab那邊會有問題)，強烈建議一起安裝python launcher

## Installation
建立虛擬環境並安裝requirement
```
py -<版本> -m venv .venv
.venv\scripts\activate
pip install -r requirements.txt
```

## Compile CPython Extension Modules
1. Command Prompt執行以下指令
    ```
    cd core
    python setup.py build_ext --inplace
    ```
2. 執行過後會出現以下檔案
    ![執行後應該長這樣](./img/after_build_backtest_core.pyx.png)

## Run
使用下面的指令來運作：
```
uvicorn src.main:app --reload
```

## 程式架構說明

### 根目錄
- `core/`：高效能回測核心（C++/Cython 擴充模組）
- `src/`：主要 FastAPI 與商業邏輯程式碼
- `code/`：研究分析 Notebook 與實驗腳本
- `static/`：無風險利率 csv 檔案放置處
- `cache/`：資料庫快取資料
- `TA-LIB/`、`pandas-ta/`：技術分析相關 wheel 檔與依賴資源

### core/
- `backtest_core.cpp`：回測核心 C++ 實作
- `backtest_core.pyx`：Cython 介面，連接 Python 與 C++
- `setup.py`：編譯擴充模組設定
- `build/`：編譯產物暫存與輸出資料夾

### src/
- `main.py`：API 應用啟動入口
- `config.py`：系統設定與環境參數管理
- `database.py`、`models.py`、`dataframe.py`：資料存取與資料模型處理
- `get_data.py`、`format_data.py`、`utils.py`：資料抓取、轉換與共用工具
- `backtest/`：回測 API、服務層、報表與 schema
- `company/`、`factor/`、`fundamental/`、`news/`、`stock/`：不同資料域與功能模組

### code/
- `analysis*.ipynb`、`strategy_test.ipynb` 等：策略研究與驗證 Notebook
- `figures/`：分析圖表輸出