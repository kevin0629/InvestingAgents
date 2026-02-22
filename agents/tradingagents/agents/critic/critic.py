from tradingagents.agents.utils.agent_output_formats import FinancialOutput

from tradingagents.agents.utils.agent_utils import store_reflection



def create_critic(llm):
    def critic_node(state) -> dict:
        tools = [store_reflection]
        tool_names = ", ".join([tool.name for tool in tools])

        financial_verification = state["financial_verification_reports"]
        news_verification = state["news_verification_reports"]
        technical_verification = state["technical_verification_reports"]
        

        prompt = f"""你是一位投資決策系統中的事後檢討稽核員。你的職責是針對上期庫存進行歸因分析。
你需要整合來自 Financial, Technical, News Analyst 的驗證報告，對比當初的買入理由與實際發生的結果，找出決策成功/失敗的根本原因，並透過 {tool_names} 儲存成記憶，供未來交易參考\n
Financial Analyst 的驗證報告: {financial_verification}\n
Technical Analyst 的驗證報告: {technical_verification}\n
News Analyst 的驗證報告: {news_verification}\n

分析方法:
    Step1: 事實核對\n
    - 情境 A： 預測發生了，股價也漲了 -> 決策正確（記錄成功模式）
    - 情境 B： 預測發生了，但股價跌了 -> 市場定價錯誤 或 忽略了其他風險（需深度檢討）
    - 情境 C： 預測沒發生（例如營收不如預期） -> 分析失準（需檢討分析邏輯）
    Step2: 偏誤識別\n
    - 確認偏誤： 是否只看利多新聞，忽略了當時已存在的利空訊號？
    - 過度樂觀： 是否對未實現的「轉機」給予過高權重？
    - 技術/基本面背離： 是否在基本面轉好但技術面崩盤時，執意進場接刀？
    Step3: 提煉教訓\n
    - 將分析結果轉化為 **通用的投資原則**，並使用 {tool_names} 儲存成記憶，供未來交易參考。例如: "當基本面出現明顯轉機但技術面尚未反應時，應該耐心等待技術指標確認轉勢後再進場，以避免過早接刀的風險"。
    - 原則必須具體且可執行，供 Portfolio Manager 下次決策參考

最後要依 股票代號、買入理由、驗證結果、學到的經驗教訓 將結果以markdown格式儲存成報告
"""

        llm_with_tools = llm.bind_tools(tools)

        result = llm_with_tools.invoke(prompt)

        reflection = ""

        if len(result.tool_calls) == 0:
            reflection = result.contents

        return {"critic_reflection": reflection}

    return critic_node
