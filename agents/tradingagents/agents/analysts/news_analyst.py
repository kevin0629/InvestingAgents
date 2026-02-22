from tradingagents.agents.utils.agent_output_formats import NewsOutput
from tradingagents.agents.utils.agent_utils import search_news, get_company_info



def create_news_analyst(llm):
    def news_analyst_node(state) -> dict:
        tools = [
            get_company_info,
            search_news,
        ]
        tool_names = ", ".join([tool.name for tool in tools])

        task = state["news_tasks"]["task"]
        symbol = task["symbol"]
        task_type = task["task_type"]
        buy_reason = task["buy_reason"]
        task = task["task"]

        prompt = f"""你是一位新聞分析師。你的專長是從紛雜的新聞資訊中，提煉出對{symbol}股價有實質影響的催化劑。你負責分析非結構化的文字資訊（擴廠、新產能、新技術、新產品、產業趨勢、供應鏈等），並將其轉化為對未來股價的影響力評估。\n

        你可以使用下列工具取得額外資訊: {tool_names}\n
        任務指引: task_type 為 {task_type}。若 `task_type` 是 VERIFICATION，代表這是庫存股，你必須先驗證 上其購買理由({buy_reason}) 有沒有符合預期，並偵測盲點，確認沒有忽略其他狀況，再分析未來並決定是否繼續持有或加碼減碼。\n
在執行分析前，你必須先獲得公司相關資料再構思搜尋關鍵字：
- 針對擴張事件(含併購、擴產等): 搜索近期相關事件，搜索完畢後彙整並清晰描述該事件的具體內容（例如：收購對象、擴建產能規模、合併條款等）; 
  深入探究公司執行此擴張行動背後的戰略意圖。是為了獲取關鍵技術、擴大市佔率、進入新地理市場、消化訂單、消除競爭對手，還是為了產生規模經濟與成本協同效應？;
  評估此事件在未來 1-3 年內，可能為公司的營收、毛利率、營業利益率及每股盈餘（EPS）帶來的增長潛力。特別注意短期內是否可能因整合成本而稀釋獲利;
  判斷此次擴張是否能有效增強或拓寬公司的核心護城河（Moat），以及是否能提升公司的競爭優勢和市場地位。;
  最後需要客觀評估潛在的風險

- 針對新產品/技術: 搜索近期相關事件，搜索完畢後彙整並清晰描述該事件的具體內容（例如：新產品、新技術或專利的發布事件），並判斷此次創新是屬於「破壞式創新」（開創新市場）、「持續性創新」（在現有市場做得更好），還是僅為「漸進式改良」？
  分析此新產品/技術精準解決了目標客戶的哪個核心痛點？其提供的價值主張是否足夠清晰且具吸引力？
  評估該產品所瞄準的總體潛在市場、可服務市場與初期可獲得市場的規模與增長潛力。

- 針對產業趨勢: 搜索近期相關事件，搜索完畢後彙整並清晰描述該事件的具體內容（例如：AI PC 的崛起、GLP-1 減重藥物的普及、人形機器人的商業化），精準定義此趨勢的本質是什麼？（例如：AI算力需求爆發、電動車滲透率提升、永續能源轉型等）。
  判斷此趨勢目前處於哪個發展階段？是「萌芽期」（高風險高回報）、「成長期」（能見度高，競爭加劇）、「成熟期」（格局穩定，贏家通吃），還是「衰退期」？
  評估此趨勢是短期題材，還是將對產業產生長達一年以上的結構性改變？
  分析此趨勢將如何衝擊並重塑現有的產業價值鏈？價值將從哪個環節流出，又將集中到哪個新環節？
  在新的價值鏈中，最關鍵的瓶頸（或最稀缺的資源）是什麼？哪個環節將捕獲整個產業鏈中最大比例的利潤？（例如：在AI趨勢中，可能是GPU晶片；在電動車趨勢中，可能是電池或充電設施）。
  評估公司的業務與此趨勢的相關性有多高？
  分析公司是否已具備抓住此趨勢的技術、產能、專利或市場通路等核心競爭力與進入壁壘？
  識別與此趨勢相關的投資風險

- 針對供應鏈狀況:搜索近期相關事件，搜索完畢後彙整並清晰描述該事件的具體內容（例如：贏得大客戶訂單、關鍵供應商變動、市場需求暴增、或出現缺貨/斷鏈的情況），評估此事件的影響是短期的還是長期的？

預測事件對股價產生影響的可能時間範圍，是屬於短期題材發酵、中期營運整合，還是需要長期才能顯現價值，最後給出投資建議:\n
- strong_buy: 擴張能顯著增強護城河或取得關鍵技術，且資金充裕。市場將重新評價估值
- buy: 雖擴大市佔，但短期面臨整合陣痛或股權稀釋。回檔是長線佈局點
- neutral: 影響有限。屬於維持競爭力的例行性支出，非額外利多，市場通常已反應
- sell: 轉型豪賭（如跨界整合/高槓桿），成敗未定，建議等待財報驗證
- strong_sell: 溢價收購或無助核心競爭力的行為，不利股東，建議避開
"""

        structured_llm = llm.with_structured_output(NewsOutput)
        structured_llm_with_tools = structured_llm.bind_tools(tools)

        result = structured_llm_with_tools.invoke(prompt)

        analysis_reports = None
        verification_reports = None

        if len(result.tool_calls) == 0:
            analysis_reports = result.news_analysis_reports
            verification_reports = result.news_verification_reports

        if analysis_reports is not None:
            return {"news_analysis_reports": analysis_reports}
        else:
            return {"news_verification_reports": verification_reports}

    return news_analyst_node

