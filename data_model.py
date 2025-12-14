from dataclasses import dataclass


@dataclass
class EconomicState:
    """
    한 시점의 거시 경제 상태.
    단위:
    - gdp: 통화 단위 (예: 달러)
    - inflation: %
    - unemployment: %
    - growth: % (실질 성장률)
    """
    gdp: float
    inflation: float
    unemployment: float
    growth: float

    def to_series(self, year: int):
        """
        시뮬레이션 결과를 테이블/그래프용 dict로 변환.
        """
        return {
            "year": year,
            "gdp": self.gdp,
            "inflation": self.inflation,
            "unemployment": self.unemployment,
            "growth": self.growth,
        }


@dataclass
class PolicyInput:
    """
    정책 및 외생 변수 입력.
    - interest_rate: 기준금리 (%)
    - corporate_tax: 법인세율 (%)
    - electricity_cost: 공업용 전기요금 (원/kWh)
    - exchange_rate: 원-달러 환율

    - government_spending_ratio: GDP 대비 정부지출 비율 (%)
    - consumer_confidence: 소비자 신뢰지수 (0~200, 100=중립)
    - corporate_investment: 기업 투자지수 (0~200, 100=중립)
    - global_demand: 글로벌 수요 (0~200, 100=중립)
    - oil_price: 유가 (달러/배럴)
    - productivity: 생산성 지수 (0~200, 100=중립)
    """
    interest_rate: float
    corporate_tax: float
    electricity_cost: float
    exchange_rate: float

    government_spending_ratio: float
    consumer_confidence: float
    corporate_investment: float
    global_demand: float
    oil_price: float
    productivity: float