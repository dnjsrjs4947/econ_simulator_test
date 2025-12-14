from data_model import EconomicState, PolicyInput


def update_one_year(state: EconomicState, policy: PolicyInput, mode: str) -> EconomicState:
    """
    한국형 동태 거시경제 시뮬레이터 (완전판)
    - 안정형 / 현실형 / 위기형 모드 지원
    - 성장률·물가·실업률·GDP가 모두 좋아질 수도, 나빠질 수도 있음
    - 악순환(위기) / 선순환(호황) 구조 포함
    - 잠재성장률이 내생적으로 변함
    - 기준금리 인상 → 물가 하락 효과 반영
    """

    # ===== 1. 모드별 계수 스케일 =====
    if mode == "안정형":
        shock_scale = 0.5
        feedback_scale = 0.6
        crisis_trigger_scale = 0.5
        potential_scale = 0.7
    elif mode == "현실형":
        shock_scale = 1.0
        feedback_scale = 1.0
        crisis_trigger_scale = 1.0
        potential_scale = 1.0
    elif mode == "위기형":
        shock_scale = 1.8
        feedback_scale = 2.0
        crisis_trigger_scale = 2.0
        potential_scale = 1.5
    else:
        shock_scale = 1.0
        feedback_scale = 1.0
        crisis_trigger_scale = 1.0
        potential_scale = 1.0

    # ===== 2. 기준값 =====
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

    # ===== 3. 잠재성장률을 내생적으로 계산 =====
    base_potential_growth = 2.5
    potential_growth = (
        base_potential_growth
        + potential_scale * 0.02 * ((policy.productivity - neutral_productivity) / 10.0)
        + potential_scale * 0.03 * ((policy.corporate_investment - neutral_invest) / 10.0)
        + potential_scale * 0.02 * ((policy.global_demand - neutral_global) / 10.0)
    )
    potential_growth = max(min(potential_growth, 6.0), 0.5)

    # ===== 4. 편차 계산 =====
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

    # ===== 5. 정책 → 성장률 영향 (shock_scale 적용) =====
    w_interest_growth = -0.08 * shock_scale
    w_tax_growth      = -0.04 * shock_scale
    w_elec_growth     = -0.6  * shock_scale
    w_oil_growth      = -0.8  * shock_scale
    w_fx_growth       = +1.0  * shock_scale

    w_gov_growth      = +0.10 * shock_scale
    w_conf_growth     = +0.03 * shock_scale
    w_invest_growth   = +0.06 * shock_scale
    w_global_growth   = +0.07 * shock_scale
    w_prod_growth     = +0.04 * shock_scale

    # ===== 6. 1차 성장률 =====
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

    # ===== 7. 물가 (수요 + 비용 + 금리 효과) =====
    w_oil_inf    = +1.2 * shock_scale
    w_elec_inf   = +0.8 * shock_scale
    w_global_inf = +0.015 * shock_scale
    w_demand_inf = +0.22 * shock_scale

    demand_gap = growth_1 - potential_growth

    # 금리 인상 → 물가 하락 (수요 위축 + 기대 인플 하락)
    w_interest_inflation = -0.25 * shock_scale
    delta_inflation_interest = w_interest_inflation * d_interest

    inflation_1 = (
        state.inflation +
        w_oil_inf    * d_oil +
        w_elec_inf   * d_elec +
        w_global_inf * (d_global / 10.0) +
        w_demand_inf * demand_gap +
        delta_inflation_interest
    )

    # ===== 8. 실업률 =====
    w_growth_unemp = -0.30 * shock_scale
    w_invest_unemp = -0.02 * shock_scale
    w_gov_unemp    = -0.03 * shock_scale

    unemp_1 = (
        state.unemployment +
        w_growth_unemp * (growth_1 - state.growth) +
        w_invest_unemp * (d_invest / 10.0) +
        w_gov_unemp    * d_gov
    )

    # -------------------------------------------------
    # ✅ 9. 피드백(상호작용) — feedback_scale 적용
    # -------------------------------------------------

    # 실업률 ↑ → 소비 ↓ → 성장률 ↓
    fb_growth_from_unemp = -0.05 * feedback_scale * (unemp_1 - state.unemployment)
    # 물가 ↑ → 실질임금 ↓ → 소비 ↓ → 성장률 ↓
    fb_growth_from_infl  = -0.06 * feedback_scale * (inflation_1 - state.inflation)
    # 성장률 변화의 자기 강화/악화
    fb_growth_from_growth = -0.04 * feedback_scale * (growth_1 - state.growth)

    # 환율 ↑ → 수입물가 ↑ → 물가 ↑
    fb_infl_from_fx = 0.30 * feedback_scale * d_fx
    # 실업률 ↑ → 소비 ↓ → 물가 ↓
    fb_infl_from_unemp = -0.12 * feedback_scale * (unemp_1 - state.unemployment)

    # 성장률 ↓ → 실업률 ↑ (추가 오쿤)
    fb_unemp_from_growth = -0.20 * feedback_scale * (growth_1 - state.growth)

    # -------------------------------------------------
    # ✅ 10. 위기 트리거 (crisis_trigger_scale 적용)
    # -------------------------------------------------
    crisis_growth_penalty = 0.0
    crisis_inflation_spike = 0.0
    crisis_unemployment_spike = 0.0

    # 실업률 위기
    if unemp_1 > 12:
        crisis_growth_penalty        -= 0.5 * crisis_trigger_scale
        crisis_unemployment_spike    += 0.3 * crisis_trigger_scale

    # 물가 위기
    if inflation_1 > 6:
        crisis_growth_penalty        -= 0.4 * crisis_trigger_scale
        crisis_inflation_spike       += 0.5 * crisis_trigger_scale

    # 성장률 위기
    if growth_1 < -1:
        crisis_growth_penalty        -= 0.6 * crisis_trigger_scale
        crisis_unemployment_spike    += 0.4 * crisis_trigger_scale

    # ===== 11. 최종 지표 =====
    final_growth = (
        growth_1 +
        fb_growth_from_unemp +
        fb_growth_from_infl +
        fb_growth_from_growth +
        crisis_growth_penalty
    )

    final_inflation = (
        inflation_1 +
        fb_infl_from_fx +
        fb_infl_from_unemp +
        crisis_inflation_spike
    )

    final_unemployment = (
        unemp_1 +
        fb_unemp_from_growth +
        crisis_unemployment_spike
    )

    # 성장률 변동폭 제한
    final_growth = max(min(final_growth, 15.0), -10.0)

    # ===== 12. GDP =====
    final_gdp = state.gdp * (1 + final_growth / 100)

    return EconomicState(
        gdp=final_gdp,
        inflation=final_inflation,
        unemployment=final_unemployment,
        growth=final_growth,
    )