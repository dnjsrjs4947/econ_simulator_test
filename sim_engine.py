from data_model import EconomicState, PolicyInput


def update_one_year(state: EconomicState, policy: PolicyInput) -> EconomicState:
    """
    한국형 동태 거시경제 시뮬레이터 (성장률 고정 문제 해결판)
    - 잠재성장률이 매년 내생적으로 변함
    - 정책 충격이 더 크게 반영됨
    - 피드백 효과가 누적됨
    - 성장률이 고정되지 않고 자연스럽게 흔들림
    """

    # ===== 1. 기준(중립) 값 =====
    neutral_interest     = 2.0
    neutral_corp_tax     = 25.0
    neutral_elec_cost    = 100.0
    neutral_fx           = 1200.0

    neutral_gov_ratio    = 20.0
    neutral_confidence   = 100.0
    neutral_invest       = 100.0
    neutral_global       = 100.0
    neutral_oil          = 70.0
    neutral_productivity = 100.0

    # ✅ 잠재성장률을 고정값이 아니라 “내생적”으로 계산
    base_potential_growth = 2.5
    potential_growth = (
        base_potential_growth
        + 0.02 * ((policy.productivity - neutral_productivity) / 10.0)
        + 0.03 * ((policy.corporate_investment - neutral_invest) / 10.0)
        + 0.02 * ((policy.global_demand - neutral_global) / 10.0)
    )
    potential_growth = max(min(potential_growth, 6.0), 0.5)

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

    # ===== 3. 정책 → 성장률 영향 (금리 비중 ↓, 투자·수출·생산성 ↑) =====
    w_interest_growth = -0.08   # 금리 영향 크게 축소
    w_tax_growth      = -0.04
    w_elec_growth     = -0.6
    w_oil_growth      = -0.8
    w_fx_growth       = +1.0

    w_gov_growth      = +0.10
    w_conf_growth     = +0.03
    w_invest_growth   = +0.06
    w_global_growth   = +0.07
    w_prod_growth     = +0.04

    # ✅ 1차 성장률 계산
    delta_growth_1 = (
        w_interest_growth * d_interest +
        w_tax_growth      * d_tax +
        w_elec_growth     * d_elec +
        w_oil_growth      * d_oil +
        w_fx_growth       * d_fx +
        w_gov_growth      * d_gov +
        w_conf_growth     * (d_conf / 10.0) +
        w_invest_growth   * (d_invest / 10.0) +
        w_global_growth   * (d_global / 10.0) +
        w_prod_growth     * (d_prod / 10.0)
    )

    growth_1 = potential_growth + delta_growth_1

    # ===== 4. 물가 =====
    w_oil_inf    = +1.2
    w_elec_inf   = +0.8
    w_global_inf = +0.015
    w_demand_inf = +0.22

    demand_gap = growth_1 - potential_growth

    delta_infl_1 = (
        w_oil_inf    * d_oil +
        w_elec_inf   * d_elec +
        w_global_inf * (d_global / 10.0) +
        w_demand_inf * demand_gap
    )

    inflation_1 = state.inflation + delta_infl_1

    # ===== 5. 실업률 =====
    w_growth_unemp = -0.30
    w_invest_unemp = -0.02
    w_gov_unemp    = -0.03

    delta_unemp_1 = (
        w_growth_unemp * (growth_1 - state.growth) +
        w_invest_unemp * (d_invest / 10.0) +
        w_gov_unemp    * d_gov
    )

    unemp_1 = state.unemployment + delta_unemp_1

    # -------------------------------------------------
    # ✅ 6. 피드백(상호작용) — “누적형”으로 강화
    # -------------------------------------------------

    # (1) 실업률 ↑ → 소비 ↓ → 성장률 ↓
    fb_growth_from_unemp = -0.05 * (unemp_1 - state.unemployment)

    # (2) 물가 ↑ → 실질임금 ↓ → 소비 ↓ → 성장률 ↓
    fb_growth_from_infl = -0.06 * (inflation_1 - state.inflation)

    # (3) 성장률 ↓ → 투자 ↓ → 다음 해 성장률 ↓ (누적형)
    fb_growth_from_growth = -0.04 * (growth_1 - state.growth)

    # (4) 환율 ↑ → 수입물가 ↑ → 물가 ↑
    fb_infl_from_fx = 0.30 * d_fx

    # (5) 실업률 ↑ → 소비 ↓ → 물가 ↓
    fb_infl_from_unemp = -0.12 * (unemp_1 - state.unemployment)

    # (6) 성장률 ↓ → 실업률 ↑ (추가 오쿤)
    fb_unemp_from_growth = -0.20 * (growth_1 - state.growth)

    # ✅ 피드백 적용
    final_growth = growth_1 + fb_growth_from_unemp + fb_growth_from_infl + fb_growth_from_growth
    final_inflation = inflation_1 + fb_infl_from_fx + fb_infl_from_unemp
    final_unemployment = unemp_1 + fb_unemp_from_growth

    # ✅ 성장률 변동폭 제한 완화 (고정된 느낌 제거)
    final_growth = max(min(final_growth, 15.0), -10.0)

    # ===== 7. GDP 업데이트 =====
    final_gdp = state.gdp * (1 + final_growth / 100)

    return EconomicState(
        gdp=final_gdp,
        inflation=final_inflation,
        unemployment=final_unemployment,
        growth=final_growth,
    )