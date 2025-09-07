from dataclasses import dataclass, asdict
import pandas as pd

@dataclass
class EconomicState:
    gdp: float               # 국내총생산 (달러)
    inflation: float         # 물가상승률 (%)
    unemployment: float      # 실업률 (%)
    growth: float            # 경제성장률 (%)

    def to_series(self, year: int) -> pd.Series:
        data = asdict(self)
        data["year"] = year
        return pd.Series(data)

@dataclass
class PolicyInput:
    interest_rate: float     # 기준금리 (%)
    corporate_tax: float     # 법인세율 (%)
    electricity_cost: float  # 공업용 전기요금 (원)
    exchange_rate: float     # 원-달러 환율
