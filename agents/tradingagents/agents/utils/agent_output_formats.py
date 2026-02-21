from pydantic import BaseModel, Field
from typing import List, Literal

class Task(BaseModel):
    symbol: str = Field(None, description="The stock symbol related to this task")
    task_type: Literal["ANALYSIS", "VERIFICATION"] = Field(None, description="Type of the technical task")
    task: str = Field(None, description="Detailed description of the task")
    buy_reason: str = Field(None, description="The reason for recommending a buy action, if applicable")

class CoordinatorOutput(BaseModel):
    mode: Literal["query", "strategy"] = Field(None, description="Operation mode: query or strategy")
    market_situation: str = Field(None, description="Summary of the current market situation.")
    end_date: str = Field(None, description="The end date for the data retrieval, analysis and trading decision.")
    
    strategy: str = Field(None, description="The investment strategy to follow, e.g. monthly_revenue_growth_roe.")

    technical_tasks: List[Task] = Field(None, description="The coordinator's detailed plan for technical analysis.")
    financial_tasks: List[Task] = Field(None, description="The coordinator's detailed plan for financial analysis.")
    news_tasks: List[Task] = Field(None, description="The coordinator's detailed plan for news analysis.")



class FinancialAnalysisReport(BaseModel):
    symbol: str = Field(None, description="The stock symbol related to this financial analysis report")
    signal: Literal["strong_buy", "buy", "neutral", "sell", "strong_sell"] = Field(None, description="Investment recommendation based on the financial analysis")
    confidence_score: int = Field(None, description="Confidence score for the investment recommendation, ranging from 0 to 10")
    report: str = Field(None, description="Detailed financial analysis report for the given stock symbol")

class FinancialVerificationReport(BaseModel):
    symbol: str = Field(None, description="The stock symbol related to this financial verification report")
    signal: Literal["strong_buy", "buy", "neutral", "sell", "strong_sell"] = Field(None, description="Investment recommendation based on the financial analysis")
    confidence_score: int = Field(None, description="Confidence score for the investment recommendation, ranging from 0 to 10")
    buy_reason: str = Field(None, description="The reason for recommending a buy action, if applicable")
    review_comment: str = Field(None, description="The financial analyst's reflection and review comment for the buy_reason")
    report: str = Field(None, description="The result of the verification process for the given financial task")

class FinancialOutput(BaseModel):
    financial_analysis_reports: List[FinancialAnalysisReport] = Field(None, description="Financial analyst outputs for analysis")
    financial_verification_reports: List[FinancialVerificationReport] = Field(None, description="Financial analyst reflections for verification")




