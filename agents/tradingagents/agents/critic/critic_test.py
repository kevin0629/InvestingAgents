"""
Critic subgraph (test version).

create_critic(llm) 回傳一個已 compile 的 StateGraph subgraph。
Critic 只接收 VerificationReport，彙整上期持股的驗證結果並提煉教訓。
"""
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_states import CriticState
from tradingagents.agents.utils.agent_utils import get_tools



def create_critic(llm):
    """回傳 Critic 的 compiled subgraph。
    只在有 VerificationReport 時才會被呼叫（由 route_after_analysts 控制）。
    """

    def critic_node(state: CriticState):
        reports_summary = (
            f"財務驗證報告:\n{state.get('financial_verification_reports')}\n\n"
            f"技術驗證報告:\n{state.get('technical_verification_reports')}\n\n"
            f"新聞驗證報告:\n{state.get('news_verification_reports')}"
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是一位投資決策系統中的事後檢討稽核員。你的職責是針對上期庫存進行歸因分析。\n"
                    "你需要整合來自 Financial、Technical、News Analyst 的驗證報告，"
                    "對比當初的買入理由與實際發生的結果，找出決策成功/失敗的根本原因。\n\n"
                    "分析方法:\n"
                    "Step1: 事實核對\n"
                    "- 情境 A：預測發生了，股價也漲了 → 決策正確（記錄成功模式）\n"
                    "- 情境 B：預測發生了，但股價跌了 → 市場定價錯誤 或 忽略了其他風險（需深度檢討）\n"
                    "- 情境 C：預測沒發生（例如營收不如預期） → 分析失準（需檢討分析邏輯）\n\n"
                    "Step2: 偏誤識別\n"
                    "- 確認偏誤：是否只看利多新聞，忽略了當時已存在的利空訊號？\n"
                    "- 過度樂觀：是否對未實現的「轉機」給予過高權重？\n"
                    "- 技術/基本面背離：是否在基本面轉好但技術面崩盤時，執意進場接刀？\n\n"
                    "Step3: 提煉教訓\n"
                    "- 將分析結果轉化為通用的投資原則，原則必須具體且可執行，供 Portfolio Manager 下次決策參考\n\n"
                    "最後請依【股票代號 | 買入理由 | 驗證結果 | 學到的經驗教訓】將結果以 Markdown 格式輸出報告。"
                    "驗證報告:\n"
                    "{reports_summary}\n"
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(reports_summary=reports_summary)
        chain = prompt | llm
        
        return {"messages": [chain.invoke(state["messages"])]}

    def _format_node(state: CriticState):
        final_text = state["messages"][-1].content
        return {"critic_reflections": [final_text]}

    sg = StateGraph(CriticState)
    sg.add_node("critic_llm", critic_node)
    sg.add_node("critic_format", _format_node)

    sg.add_edge(START, "critic_llm")
    sg.add_edge("critic_llm", "critic_format")
    sg.add_edge("critic_format", END)

    return sg.compile()
