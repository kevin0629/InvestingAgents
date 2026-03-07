from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class Task(BaseModel):
    symbol: str = Field(description="The stock symbol related to this task, must be integer string like '2330', '2455', '3491'")
    task_type: Literal["ANALYSIS", "VERIFICATION"] = Field(None, description="Type of the technical task")
    task: str = Field(description="Detailed description of the task")
    buy_reason: Optional[str] = Field(None, description="The reason for recommending a buy action, if task_type is VERIFICATION else None")

class CoordinatorOutput(BaseModel):
    """Respond to the user with this"""
    user_query: str = Field(description="The original user query that initiated the analysis and trading process")
    mode: Literal["query", "strategy"] = Field(description="Operation mode: query or strategy")
    market_situation: str = Field(description="Summary of the current market situation.")
    end_date: Optional[str] = Field(None, description="The end date for the data retrieval, analysis and trading decision.")
    
    strategy: Optional[str] = Field(None, description="The investment strategy to follow, e.g. monthly_revenue_growth_roe.")

    technical_tasks: List[Task] = Field(None, description="The coordinator's detailed plan for technical analysis.")
    financial_tasks: List[Task] = Field(None, description="The coordinator's detailed plan for financial analysis.")
    news_tasks: List[Task] = Field(None, description="The coordinator's detailed plan for news analysis.")



class FinancialAnalysisReport(BaseModel):
    symbol: str = Field(description="The stock symbol related to this financial analysis report")
    signal: Literal["strong_buy", "buy", "neutral", "sell", "strong_sell"] = Field(description="Investment recommendation based on the financial analysis")
    confidence_score: int = Field(description="Confidence score for the investment recommendation, ranging from 0 to 10")
    report: str = Field(description="Detailed financial analysis report for the given stock symbol")

class FinancialVerificationReport(BaseModel):
    symbol: str = Field(description="The stock symbol related to this financial verification report")
    signal: Literal["strong_buy", "buy", "neutral", "sell", "strong_sell"] = Field(description="Investment recommendation based on the financial analysis")
    confidence_score: int = Field(description="Confidence score for the investment recommendation, ranging from 0 to 10")
    buy_reason: str = Field(description="The reason for recommending a buy action, if applicable")
    review_comment: str = Field(description="The financial analyst's reflection and review comment for the buy_reason")
    report: str = Field(description="The result of the verification process for the given financial task")

class FinancialOutput(BaseModel):
    """Respond to the user with financial_analysis_reports when the task_type is ANALYSIS, or financial_verification_reports when the task_type is VERIFICATION"""
    financial_analysis_reports: List[FinancialAnalysisReport] = Field(None, description="Financial analyst outputs for analysis")
    financial_verification_reports: List[FinancialVerificationReport] = Field(None, description="Financial analyst reflections for verification")



class NewsAnalysisReport(BaseModel):
    symbol: str = Field(description="The stock symbol related to this news analysis report")
    signal: Literal["strong_buy", "buy", "neutral", "sell", "strong_sell"] = Field(description="Investment recommendation based on the news analysis")
    confidence_score: int = Field(description="Confidence score for the investment recommendation, ranging from 0 to 10")
    report: str = Field(description="Detailed news analysis report for the given stock symbol")

class NewsVerificationReport(BaseModel):
    symbol: str = Field(description="The stock symbol related to this news verification report")
    signal: Literal["strong_buy", "buy", "neutral", "sell", "strong_sell"] = Field(description="Investment recommendation based on the news analysis")
    confidence_score: int = Field(description="Confidence score for the investment recommendation, ranging from 0 to 10")
    buy_reason: str = Field(description="The reason for recommending a buy action, if applicable")
    review_comment: str = Field(description="The news analyst's reflection and review comment for the buy_reason")
    report: str = Field(description="The result of the verification process for the given news task")

class NewsOutput(BaseModel):
    """Respond to the user with news_analysis_reports when the task_type is ANALYSIS, or news_verification_reports when the task_type is VERIFICATION"""
    news_analysis_reports: List[NewsAnalysisReport] = Field(None, description="News analyst outputs for analysis")
    news_verification_reports: List[NewsVerificationReport] = Field(None, description="News analyst reflections for verification")


class TechnicalAnalysisReport(BaseModel):
    symbol: str = Field(description="The stock symbol related to this technical analysis report")
    signal: Literal["strong_buy", "buy", "neutral", "sell", "strong_sell"] = Field(description="Investment recommendation based on the technical analysis")
    confidence_score: int = Field(description="Confidence score for the investment recommendation, ranging from 0 to 10")
    report: str = Field(description="Detailed technical analysis report for the given stock symbol")

class TechnicalVerificationReport(BaseModel):
    symbol: str = Field(description="The stock symbol related to this technical verification report")
    signal: Literal["strong_buy", "buy", "neutral", "sell", "strong_sell"] = Field(description="Investment recommendation based on the technical analysis")
    confidence_score: int = Field(description="Confidence score for the investment recommendation, ranging from 0 to 10")
    buy_reason: str = Field(description="The reason for recommending a buy action, if applicable")
    review_comment: str = Field(description="The technical analyst's reflection and review comment for the buy_reason")
    report: str = Field(description="The result of the verification process for the given technical task")

class TechnicalOutput(BaseModel):
    """Respond to the user with technical_analysis_reports when the task_type is ANALYSIS, or technical_verification_reports when the task_type is VERIFICATION"""
    technical_analysis_reports: List[TechnicalAnalysisReport] = Field(None, description="Technical analyst outputs for analysis")
    technical_verification_reports: List[TechnicalVerificationReport] = Field(None, description="Technical analyst reflections for verification")


class PortfolioDecision(BaseModel):
    symbol: str = Field(description="The stock symbol related to this portfolio decision")
    stock_type: Literal["growth", "value", "turnaround", "thematic"] = Field(description="The identified stock type based on the integrated analysis")
    stock_type_classification_rationale: str = Field(description="The rationale behind classifying the stock into a specific type")
    action: Literal["buy", "hold", "sell"] = Field(description="The trading action decided by the portfolio manager for the next trading day")
    position: float = Field(description="The target position size for the given stock symbol, represented as a percentage of the total portfolio (e.g., 0.1 for 10%)")
    confidence_score: int = Field(description="Confidence score for the trading action, ranging from 0 to 10")
    rationale: str = Field(description="Detailed rationale behind the portfolio manager's trading decision for the given stock symbol")

class PortfolioDecisions(BaseModel):
    """Respond to the user with this"""
    portfolio_decisions: List[PortfolioDecision] = Field(None, description="The portfolio manager's final trading decisions for the next trading day")

