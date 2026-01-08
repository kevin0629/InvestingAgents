from src.config import Config
from src.dataframe import CustomDataFrame
from src.models import Taiex, Stock, Company, Factor, FactorValue
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from datetime import date
import asyncio
from src.config import Config

class Database:
    def __init__(self):
        self._config = Config()
        self._engine = None
        self._session_maker = None
    

    def connection(self):
        """
        用 asyncpg 連線到 config.ini 指定的資料庫，如果資料庫中沒有資料庫請先自己建立一個。
        回傳：async engine
        """
        if self._engine is None:
            try:
                self._engine = create_async_engine(
                    str(self._config.DATABASE_URL),
                    echo=False
                )
            except Exception as e:
                print("無法建立資料庫引擎: %s", e)
                return None
            
        return self._engine
    
    def async_session(self):
        """
        用sqlalchemy 創建 async session 來溝通
        回傳：AsyncSession
        """
        if self._session_maker is None:
            db_engine = self.connection()
            if db_engine:
                self._session_maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

        return self._session_maker()


    # 取得公司的開高低收、市值、本益比、beta(stock)
    async def get_daily_stock(self):
        async with self.async_session() as session:
            try:
                # 使用 SQLAlchemy Core/ORM 查詢，對應 models 結構
                stmt = (
                    select(
                        Company.symbol.label("company_symbol"),
                        Company.name,
                        Stock.date,
                        Stock.open,
                        Stock.high,
                        Stock.low,
                        Stock.close,
                        Stock.volume,
                        Stock.market_cap.label("market_capital"),
                        Stock.pe_ratio,
                        Stock.beta,
                    )
                    .join(Company, Stock.company_id == Company.id)
                    .where(Company.exchange_name == 'TWSE')
                    .where(Stock.date > date(2025, 1, 1))
                )

                result = await session.execute(stmt)
                data = result.all()
                
                columns = [
                    "company_symbol",
                    "name",
                    "date",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "market_capital",
                    "pe_ratio",
                    "beta",
                ]
                
                df = CustomDataFrame(data, columns=columns)
                return df

            except Exception as e:
                print(f"取得 Daily Stock 失敗: {e}")
                return e

    # 取得公司的財報(factorvalue)
    async def get_finance_report(self):
        async with self.async_session() as session:
            try:
                stmt = (
                    select(
                        FactorValue.date,
                        Company.symbol.label("company_symbol"),
                        Factor.factor_name,
                        FactorValue.factor_value
                    )
                    .join(Factor, FactorValue.factor_id == Factor.id)
                    .join(Company, FactorValue.company_id == Company.id)
                    .where(Company.exchange_name == 'TWSE')
                    .where(FactorValue.date > date(2025, 1, 1))
                )

                result = await session.execute(stmt)
                data = result.all()
                
                columns = ["date", "company_symbol", "factor_name", "factor_value"]
                df = CustomDataFrame(data, columns=columns)
                return df

            except Exception as e:
                print(f"取得 Finance Report 失敗: {e}")
                return e

    # 取得台股加權指數(taiex)
    async def get_taiex_data(self):
        async with self.async_session() as session:
            try:
                stmt = select(
                    Taiex.date,
                    Taiex.open,
                    Taiex.high,
                    Taiex.low,
                    Taiex.close,
                    Taiex.volume,
                    Taiex.market_cap.label("market_capital"),
                )

                result = await session.execute(stmt)
                data = result.all()

                columns = ["date", "open", "high", "low", "close", "volume", "market_capital"]
                df = CustomDataFrame(data, columns=columns)
                return df

            except Exception as e:
                print(f"取得 Taiex 失敗: {e}")
                return e

    async def dispose(self):
        """
        關閉資料庫引擎和所有連線
        """
        if self._engine is not None:
            await self._engine.dispose()


async def main():
    db = Database()

    # 取得公司的開高低收、市值、本益比、beta(stock)
    stock_df = await db.get_daily_stock()
    filtered_df = stock_df[stock_df["company_symbol"] == "3491"]
    filtered_df.set_index("date", inplace=True)
    filtered_df = filtered_df.sort_index(ascending=True)
    filtered_df.to_csv("./OutputFile/filtered_stock.csv")

    # 取得公司的財務因子(factorvalue)
    finance_report_df = await db.get_finance_report()
    filtered_df = finance_report_df[finance_report_df["company_symbol"] == "3491"]
    filtered_df.set_index("date", inplace=True)
    filtered_df = filtered_df.sort_index(ascending=True)
    filtered_df.to_csv("./OutputFile/filtered_finance_report.csv")

    # 取得台股加權指數(taiex)
    taiex_df = await db.get_taiex_data()
    taiex_df.set_index("date", inplace=True)
    taiex_df = taiex_df.sort_index(ascending=True)
    taiex_df.to_csv("./OutputFile/taiex.csv")

    # 關閉資料庫引擎
    await db.dispose()
    


if __name__ == "__main__":
    asyncio.run(main())
