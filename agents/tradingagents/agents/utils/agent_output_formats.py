from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class Task(BaseModel):
    symbol: str = Field(description="The stock symbol related to this task, must be integer string like '2330', '2455', '3491'")
    task_type: Literal["ANALYSIS", "VERIFICATION", "HYBRID"] = Field(None, description="Type of task")
    position: Optional[float] = Field(None, description="The target position size for the given stock symbol in previous period.")
    stock_return: Optional[str] = Field(None, description="The stock return for the previous period, used for VERIFICATION and HYBRID tasks to reflect on the accuracy of the previous recommendation")
    buy_reason: Optional[str] = Field(None, description="The reason for recommending a buy action, if task_type is VERIFICATION else None")
    selected: bool = Field(False, description="Whether this symbol is selected in both previous and current period")
    company_info: Optional[str] = Field(None, description="Company basic information")

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
    selected: bool = Field(False, description="True only when this symbol is selected in both previous and current period")
    review_comment: str = Field(description="The financial analyst's reflection and review comment for the buy_reason")
    report: str = Field(description="The result of the verification process for the given financial task")

class FinancialOutput(BaseModel):
    """Respond with analysis for ANALYSIS, verification for VERIFICATION, and both for HYBRID."""
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
    selected: bool = Field(False, description="True only when this symbol is selected in both previous and current period")
    review_comment: str = Field(description="The news analyst's reflection and review comment for the buy_reason")
    report: str = Field(description="The result of the verification process for the given news task")

class NewsOutput(BaseModel):
    """Respond with analysis for ANALYSIS, verification for VERIFICATION, and both for HYBRID."""
    news_analysis_reports: List[NewsAnalysisReport] = Field(None, description="News analyst outputs for analysis")
    news_verification_reports: List[NewsVerificationReport] = Field(None, description="News analyst reflections for verification")

class MacroAnalysisReport(BaseModel):
    signal: Literal["strong_buy", "buy", "neutral", "sell", "strong_sell"] = Field(description="Investment recommendation based on the macro analysis")
    confidence_score: int = Field(description="Confidence score for the investment recommendation, ranging from 0 to 10")
    report: str = Field(description="Detailed macro analysis report")

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
    selected: bool = Field(False, description="True only when this symbol is selected in both previous and current period")
    review_comment: str = Field(description="The technical analyst's reflection and review comment for the buy_reason")
    report: str = Field(description="The result of the verification process for the given technical task")

class TechnicalOutput(BaseModel):
    """Respond with analysis for ANALYSIS, verification for VERIFICATION, and both for HYBRID."""
    technical_analysis_reports: List[TechnicalAnalysisReport] = Field(None, description="Technical analyst outputs for analysis")
    technical_verification_reports: List[TechnicalVerificationReport] = Field(None, description="Technical analyst reflections for verification")

class PortfolioReport(BaseModel):
    symbol: str = Field(description="The stock symbol related to this portfolio decision")
    stock_type: Literal["growth", "value", "turnaround"] = Field(description="The identified stock type based on the integrated analysis")
    stock_type_classification_rationale: str = Field(description="The rationale behind classifying the stock into a specific type")
    growth_score: int = Field(description="Growth score for the stock, ranging from 0 to 10")
    value_score: int = Field(description="Value score for the stock, ranging from 0 to 10")
    turnaround_score: int = Field(description="Turnaround score for the stock, ranging from 0 to 10")
    report: str = Field(description="The portfolio manager's final report for the given stock symbol")

class PortfolioReports(BaseModel):
    """Respond to the user with this"""
    portfolio_reports: List[PortfolioReport] = Field(None, description="The portfolio manager's final reports")

