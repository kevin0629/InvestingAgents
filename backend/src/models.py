from sqlalchemy import Column, Integer, String, ForeignKey, Float, BigInteger, Date
from sqlalchemy.orm import registry
from sqlalchemy.orm import relationship



mapper_registry = registry()
Base = mapper_registry.generate_base()


class Company(Base):
    '''
    公司
    註:一間實體公司可以有多項虛擬公司，若他在多個交易所上市，則會有多個虛擬公司
    '''
    __tablename__ = 'company'
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), nullable=False)
    name = Column(String(400), nullable=True)
    industry = Column(String(100), nullable=False)
    subindustry = Column(String(100), nullable=False)
    business1 = Column(String(500), nullable=False)  # 主要業務1
    business2 = Column(String(500), nullable=True)  # 主要業務2
    business3 = Column(String(500), nullable=True)  # 主要業務3
    main_product_proportion = Column(String(500), nullable=True)  # 主要產品比例
    exchange_name = Column(String(50), nullable=False)
    country = Column(String(50), nullable=False)
    
    # 第一個參數是你要對應到的class名稱，back_populates 是在他的class 裡面你的變數名稱(通常都是小寫的class名)
    stock = relationship('Stock', back_populates="company")
    financialReportIndicatorValue = relationship('FinancialReportIndicatorValue', back_populates="company")
    factorValue = relationship('FactorValue', back_populates="company")
    # chips = relationship('Chips', back_populates="company")

class Period(Base):
    """
    財報所表示的月，季與年
    """
    __tablename__ = 'period'
    id = Column(Integer, primary_key=True, autoincrement=True)
    period_name = Column(String(10), nullable=False)

    financialReportIndicatorValue = relationship('FinancialReportIndicatorValue', back_populates="period")
    factorValue = relationship('FactorValue', back_populates="period")

class Factor(Base):
    """
    因子，基於公司財報基本面計算出來，用於執行換股策略
    此列表紀錄所使用的因子名稱以及他的計算方式
    """
    __tablename__ = 'factor'
    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_name = Column(String(255))
    factor_formula = Column(String(255))

    factorValue = relationship('FactorValue', back_populates="factor")

class FactorValue(Base):
    """
    因子數值：
    此列表記錄各公司的各個因子的數值，每一筆紀錄一間公司對應的一個因子的數值
    """
    __tablename__ = 'factorvalue'
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('company.id'))
    factor_id = Column(Integer, ForeignKey('factor.id'))
    date = Column(Date, nullable=False)
    release_date = Column(Date, nullable=False)
    period_id = Column(Integer, ForeignKey('period.id'))
    factor_value = Column(Float, nullable=False)

    company = relationship('Company', back_populates="factorValue")
    factor = relationship('Factor', back_populates="factorValue")
    period = relationship('Period', back_populates="factorValue")

class SingleIndicator(Base):
    """
    基本面指標：
    此列表紀錄所有使用到的基本面指標，且該指標對應到各國的名稱
    ex. eps
    """
    __tablename__ = 'singleindicator'
    id = Column(Integer, primary_key=True, autoincrement=True)
    tw_indicator = Column(String(255), nullable=True)
    us_indicator = Column(String(255), nullable=True)
    # cn_indicator = Column(String(255), nullable=True)

    financialReportIndicatorValue = relationship('FinancialReportIndicatorValue', back_populates="singleIndicator")

class FinancialReportIndicatorValue(Base):
    """
    基本面指標數值
    各個公司各個指標的數值，單一資料為單一間公司對應到的該指標數值
    ex. 台積電, eps, 10
    """
    __tablename__ = 'financialreportindicatorvalue'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('company.id'))
    date = Column(Date, nullable=False)
    release_date = Column(Date, nullable=False)
    period_id = Column(Integer, ForeignKey('period.id'))
    indicator_id = Column(Integer, ForeignKey('singleindicator.id'))
    indicator_value = Column(Float)

    company = relationship('Company', back_populates="financialReportIndicatorValue")
    period = relationship('Period', back_populates="financialReportIndicatorValue")
    singleIndicator = relationship('SingleIndicator', back_populates="financialReportIndicatorValue")

class Stock(Base):
    """
    價量資訊
    單一間公司在單一日期的開、高、低、收、量
    """
    __tablename__ = 'stock'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    market_cap = Column(Float)
    pe_ratio = Column(Float)
    beta = Column(Float)
    company_id = Column(Integer, ForeignKey('company.id'))

    company = relationship('Company', back_populates="stock")


class Taiex(Base):
    """
    調整後大盤指數：
    在單一日期的開、高、低、收、量、市值
    """
    __tablename__ = 'taiex'
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    market_cap = Column(Integer)


class AdjustedTaiex(Base):
    """
    大盤報酬指數：
    在單一日期的值
    """
    __tablename__ = 'adjustedtaiex'
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    close = Column(Float)


# class Chips(Base):
#     """
#     籌碼資訊
#     單一間公司在單一日期的外資買賣超、投信買賣超、自營買賣超
#     、融資餘額、融券餘額、融資使用率、融券使用率、券資比
#     """
#     __tablename__ = 'chips'
#     id = Column(BigInteger, primary_key=True, autoincrement=True)
#     company_id = Column(Integer, ForeignKey('company.id'))
#     date = Column(Date, nullable=False)
#     foreign_investor_buy_sell = Column(Integer, nullable=False)
#     investment_trust_buy_sell = Column(Integer, nullable=False)
#     dealer_buy_sell = Column(Integer, nullable=False)
#     margin_purchase = Column(Integer, nullable=False)
#     margin_short = Column(Integer, nullable=False)
#     margin_purchase_rate = Column(Float, nullable=False)
#     margin_short_rate = Column(Float, nullable=False)
#     margin_ratio = Column(Float, nullable=False)

#     company = relationship("Company", back_populates="chips")
