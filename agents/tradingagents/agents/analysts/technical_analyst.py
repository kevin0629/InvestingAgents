from tradingagents.agents.utils.agent_output_formats import TechnicalOutput
from tradingagents.agents.utils.agent_utils import get_stock_data
from langchain_core.messages import HumanMessage



def create_technical_analyst(llm):
    def technical_analyst_node(state) -> dict:
        def _extract_payload(result, output_tool_name):
            tool_calls = getattr(result, "tool_calls", None) or []
            for call in tool_calls:
                if call.get("name") == output_tool_name:
                    return call.get("args", {}) or {}
            content = getattr(result, "content", None)
            if isinstance(content, dict):
                return content
            return {}

        def _tool_name(tool):
            return getattr(tool, "name", getattr(tool, "__name__", tool.__class__.__name__))

        tools = [get_stock_data]
        tool_names = ", ".join([_tool_name(tool) for tool in tools])

        def _get_value(payload, key, default=""):
            if payload is None:
                return default
            if isinstance(payload, dict):
                return payload.get(key, default)
            return getattr(payload, key, default)

        task_payload = state.get("technical_task")
        if task_payload is None:
            technical_tasks = state.get("technical_tasks") or []
            if isinstance(technical_tasks, list) and technical_tasks:
                task_payload = technical_tasks[0]
            elif isinstance(technical_tasks, dict):
                task_payload = technical_tasks.get("task")

        symbol = _get_value(task_payload, "symbol", "")
        task_type = _get_value(task_payload, "task_type", "")
        buy_reason = _get_value(task_payload, "buy_reason", "")
        task = _get_value(task_payload, "task", "")

        prompt = f"""你是一位技術分析師，負責分析{symbol}的價格、成交量與技術指標，並進一步判讀未來的走勢。\n

        你的任務為 {task}\n
        你可以使用下列工具取得額外資訊: {tool_names}\n
        任務指引: task_type 為 {task_type}。若 `task_type` 是 VERIFICATION，代表這是庫存股，你必須先驗證 上其購買理由({buy_reason}) 有沒有符合預期，並偵測盲點，確認沒有忽略其他狀況，再分析未來並決定是否繼續持有或加碼減碼。\n
在分析{symbol}的技術面時，請務必從以下幾個層面進行全面的評估：
1. 趨勢與價位分析: 判斷目前股價處於長期、中期、短期分別處於何種趨勢（上升、下降、或盤整），並指出圖表上關鍵的「支撐」與「壓力」區間
2. 技術指標分析: 分析中期、長期移動平均線（例如 20MA, 60MA, 240MA）的排列狀況，判斷市場是處於多頭或空頭排列;
   檢視 RSI 指標的數值，判斷市場是否處於超買 (>70) 或超賣 (<30) 狀態，並特別注意是否存在價格與指標走勢相反的「背離」現象;
   分析 MACD 的快慢線交叉情況與柱狀體的變化，以判斷市場動能的增強或減弱;
   檢視布林通道的帶寬變化，判斷市場波動性的收斂或擴張，分析股價與上、中、下三條軌道的互動關係
3. 型態與成交量分析: 識別圖表上是否正在形成經典的價格型態，例如：頭肩頂/底、W底/M頭、旗形、或是三角收斂等，分析成交量的變化。一個健康的趨勢通常伴隨著成交量的支持（例如：價漲量增），若出現價量背離（例如：價漲量縮），則需提出警示

綜合以上所有分析，嚴格對照下面的邏輯產出最終的「交易建議」:
- strong_buy: 長、中、短期趨勢皆為多頭，且 RSI 無頂部背離，成交量配合價漲
- buy: 長期多頭，中期多頭，短線回測支撐有守，長線趨勢保護
- neutral: 長中短期趨勢不一致（例如：長期多頭但中期跌破支撐），或處於布林帶壓縮的情況
- sell: 長期空頭，中期反彈無力
- strong_sell: 長、中、短期趨勢皆為空頭，且 RSI 無底部背離，成交量配合價跌
"""

        llm_with_tools = llm.bind_tools(tools)

        messages = list(state.get("messages", []))
        messages.append(HumanMessage(content=prompt))
        result = llm_with_tools.invoke(messages)

        report = _extract_payload(result, TechnicalOutput.__name__)
        analysis_reports = report.get("technical_analysis_reports", [])
        verification_reports = report.get("technical_verification_reports", [])

        output = {"messages": [result]}
        if analysis_reports:
            output["technical_analysis_reports"] = analysis_reports
        if verification_reports:
            output["technical_verification_reports"] = verification_reports
        return output

    return technical_analyst_node

