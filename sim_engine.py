from data_model import EconomicState, PolicyInput


def update_one_year(state: EconomicState, policy: PolicyInput) -> EconomicState:
    """
    단순화된 거시경제 반응 모델 (교육용).

    아이디어:
    - 성장률은 금리, 세금, 공업용 전기요금, 유가, 환율, 정부지출, 소비자심리,
      기업투자, 글로벌 수요, 생산성의 영향을 받는다.
    - 물가는 원가(유가·전기요금)와 수요압력(성장률-잠재성장률), 글로벌 수요에 반응한다.
    - 실업률은 성장률 변화, 기업투자, 정부지출에 의해 움직인다.
    - GDP는 성장률을 통해 업데이트되고, 법인세는 약하게 감속효과를 준다.

    실제 계수는 임의값이며, 방향성과 상호작용을 직관적으로 느끼기 위한 용도이다.
    """

    # ===== 1. 기준(중립) 값 설정 =====
    neutral_interest     = 2.0       # 중립 금리
    neutral_corp_tax     = 25.0      # 중립 법인세율
    neutral_elec_cost    = 100.0     # 기준 공업용 전기요금
    neutral_fx           = 1200.0    # 기준 환율

    neutral_gov_ratio    = 20.0      # GDP 대비 정부지출 비율 (%)
    neutral_confidence   = 100.0     # 소비자 신뢰 (0~200, 100=중립)
    neutral_invest       = 100.0     # 기업 투자지수
    neutral_global       = 100.0     # 글로벌 수요
    neutral_oil          = 70.0      # 유가 (달러/배럴)
    neutral_productivity = 100.0     # 생산성 지수

    potential_growth     = 2.5       # 잠재 성장률 (%)

    # ===== 2. 편차 계산 =====
    d_interest   = policy.interest_rate - neutral_interest
    d_tax        = policy.corporate_tax - neutral_corp_tax
    d_elec       = (policy.electricity_cost - neutral_elec_cost) / neutral_elec_cost
    d_fx         = (policy.exchange_rate   - neutral_fx)        / neutral_fx

    d_gov        = policy.government_spending_ratio - neutral_gov_ratio
    d_conf       = policy.consumer_confidence       - neutral_confidence
    d_invest     = policy.corporate_investment      - neutral_invest
    d_global     = policy.global_demand             - neutral_global
    d_oil        = (policy.oil_price - neutral_oil) / neutral_oil
    d_prod       = policy.productivity              - neutral_productivity

    # ===== 3. 반응 계수 =====
    # 성장률에 대한 영향 계수
    w_interest_growth = -0.3   # 금리 1%p ↑ → 성장률 약 -0.3%p
    w_tax_growth      = -0.05  # 법인세 1%p ↑ → 성장률 약 -0.05%p
    w_elec_growth     = -1.0   # 전기요금 100% ↑ → 성장률 -1%p
    w_oil_growth      = -1.2   # 유가 100% ↑ → 성장률 -1.2%p
    w_fx_growth       = +2.0   # 환율 100% ↑(원화 약세) → 수출↑ → 성장률 +2%p (교육용 단순화)

    w_gov_growth      = +0.08  # 정부지출 비율 1%p ↑ → 성장률 +0.08%p
    w_conf_growth     = +0.02  # 소비자신뢰 10 ↑ → 성장률 +0.2%p
    w_invest_growth   = +0.03  # 기업투자 10 ↑ → 성장률 +0.3%p
    w_global_growth   = +0.04  # 글로벌수요 10 ↑ → 성장률 +0.4%p
    w_prod_growth     = +0.015 # 생산성 10 ↑ → 성장률 +0.15%p

    # 물가에 대한 영향
    w_oil_inflation    = +1.5  # 유가 100% ↑ → 물가 +1.5%p
    w_elec_inflation   = +1.0  # 전기요금 100% ↑ → 물가 +1.0%p
    w_global_inflation = +0.02 # 글로벌 수요 10 ↑ → 물가 +0.2%p
    w_demand_inflation = +0.3  # 성장률이 잠재성장률보다 1%p 높을 때 → 물가 +0.3%p

    # 실업률에 대한 영향
    w_growth_unemp = -0.4      # 성장률 1%p ↑ → 실업률 -0.4%p (오쿤의 법칙 느낌)
    w_invest_unemp = -0.02     # 기업투자 10 ↑ → 실업률 -0.2%p
    w_gov_unemp    = -0.03     # 정부지출 비율 1%p ↑ → 실업률 -0.03%p

    # 세금이 GDP에 미치는 직접 효과 (기업 활동 부담)
    w_tax_gdp      = -0.002    # 세율 1%p ↑ → GDP 약 -0.2% (단순 가감)

    # ===== 4. 성장률 계산 =====
    delta_growth = 0.0
    delta_growth += w_interest_growth * d_interest
    delta_growth += w_tax_growth      * d_tax
    delta_growth += w_elec_growth     * d_elec
    delta_growth += w_oil_growth      * d_oil
    delta_growth += w_fx_growth       * d_fx

    delta_growth += w_gov_growth      * d_gov
    delta_growth += w_conf_growth     * (d_conf / 10.0)
    delta_growth += w_invest_growth   * (d_invest / 10.0)
    delta_growth += w_global_growth   * (d_global / 10.0)
    delta_growth += w_prod_growth     * (d_prod / 10.0)

    # 잠재성장률을 중심으로 움직이게
    new_growth = potential_growth + delta_growth
    new_growth = max(min(new_growth, 10.0), -5.0)

    # ===== 5. GDP 업데이트 =====
    gdp_after_growth = state.gdp * (1 + new_growth / 100)
    delta_gdp_tax    = w_tax_gdp * d_tax / 100 * state.gdp
    new_gdp          = gdp_after_growth + delta_gdp_tax
    new_gdp          = max(new_gdp, 0.0)

    # ===== 6. 물가 업데이트 =====
    demand_gap       = new_growth - potential_growth

    delta_inflation  = 0.0
    delta_inflation += w_oil_inflation    * d_oil
    delta_inflation += w_elec_inflation   * d_elec
    delta_inflation += w_global_inflation * (d_global / 10.0)
    delta_inflation += w_demand_inflation * demand_gap

    new_inflation    = state.inflation + delta_inflation
    new_inflation    = max(new_inflation, -5.0)

    # ===== 7. 실업률 업데이트 =====
    delta_unemp  = 0.0
    # 성장률 변화에 따른 실업률 변화
    delta_unemp += w_growth_unemp * (new_growth - state.growth)
    # 기업투자, 정부지출의 고용효과
    delta_unemp += w_invest_unemp * (d_invest / 10.0)
    delta_unemp += w_gov_unemp    * d_gov

    new_unemployment = state.unemployment + delta_unemp
    new_unemployment = max(min(new_unemployment, 50.0), 0.0)

    return EconomicState(
        gdp=new_gdp,
        inflation=new_inflation,
        unemployment=new_unemployment,
        growth=new_growth,
    )