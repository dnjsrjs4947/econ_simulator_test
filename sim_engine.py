# sim_engine.py
from data_model import EconomicState, PolicyInput

def update_one_year(state: EconomicState, policy: PolicyInput) -> EconomicState:
    """
    현실적인 반응 계수(임의 조정):
    - 금리 1%p 상승 → 성장률 -0.1%p, 실업률 +0.05%p, 물가 +0.02%p
    - 법인세 1%p 상승 → 성장률 -0.05%p, GDP 소폭 감소
    - 공업용 전기요금 1%p 상승 → 성장률 -0.05%p  ← 변경된 가중치
    - 환율 1% 상승(원화 약세) → 수출↑로 성장률 +0.05%p
    """
    # 반응 계수
    w_interest_growth    = -0.1
    w_interest_unemploy  = +0.05
    w_interest_inflation = +0.02

    w_tax_growth         = -0.05
    w_tax_gdp            = -0.002

    # 전기요금이 산업 전반에 미치는 영향 증대
    w_elec_growth        = -0.05

    w_fx_growth          = +0.05

    # 성장률 변화 계산
    delta_growth = (
        w_interest_growth   * (policy.interest_rate   - 2.0) +
        w_tax_growth        * (policy.corporate_tax   - 25.0) +
        w_elec_growth       * ((policy.electricity_cost - 100.0) / 100.0) +
        w_fx_growth         * ((policy.exchange_rate   - 1200.0) / 1200.0)
    )
    new_growth = max(min(state.growth + delta_growth, 10.0), -5.0)

    # GDP 업데이트 (세금 영향 포함)
    gdp_after_growth = state.gdp * (1 + new_growth / 100)
    delta_gdp_tax    = w_tax_gdp * (policy.corporate_tax - 25.0) / 100 * state.gdp
    new_gdp          = gdp_after_growth + delta_gdp_tax

    # 물가·실업 업데이트
    new_inflation    = max(state.inflation   + w_interest_inflation * (policy.interest_rate - 2.0), 0.0)
    new_unemployment = max(state.unemployment + w_interest_unemploy   * (policy.interest_rate - 2.0), 0.0)

    return EconomicState(
        gdp=new_gdp,
        inflation=new_inflation,
        unemployment=new_unemployment,
        growth=new_growth
    )
