from data_model import EconomicState, PolicyInput


def update_one_year(state: EconomicState, policy: PolicyInput, mode: str) -> EconomicState:
    """
    한국형 동태 거시경제 시뮬레이터 (상호작용 강화 완전판)

    - 모드: 안정형 / 현실형 / 위기형
    - 핵심 아이디어:
        1) 정책이 먼저 '소비(C)'와 '투자(I)'에 영향을 줌
        2) C, I, 글로벌 수요 등으로 성장률을 결정
        3) 성장률, 실업률, 인플레이션, 환율 등이 서로 피드백
        4) 위기 트리거(고물가, 고실업, 역성장)가 악순환을 강화
        5) 기대 인플레이션(단순형)을 반영해 금리 정책의 효과를 더 현실적으로 만듦
    """

    # ===== 1. 모드별 계수 스케일 =====
    if mode == "안정형":
        shock_scale = 0.5
        feedback_scale = 0.6
        crisis_trigger_scale = 0.5
        potential_scale = 0.7
        expectation_scale = 0.5
    elif mode == "현실형":
        shock_scale = 1.0
        feedback_scale = 1.0
        crisis_trigger_scale = 1.0
        potential_scale = 1.0
        expectation_scale = 1.0
    elif mode == "위기형":
        shock_scale = 1.8
        feedback_scale = 2.0
        crisis_trigger_scale = 2.0
        potential_scale = 1.5
        expectation_scale = 1.5
    else:
        shock_scale = 1.0
        feedback_scale = 1.0
        crisis_trigger_scale = 1.0
        potential_scale = 1.0
        expectation_scale = 1.0

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

    # ===== 3. 편차 계산 =====
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

    # ===== 4. 잠재성장률 계산 (장기 구조) =====
    base_potential_growth = 2.5
    potential_growth = (
        base_potential_growth
        + potential_scale * 0.02 * ((policy.productivity - neutral_productivity) / 10.0)
        + potential_scale * 0.03 * ((policy.corporate_investment - neutral_invest) / 10.0)
        + potential_scale * 0.02 * ((policy.global_demand - neutral_global) / 10.0)
    )
    potential_growth = max(min(potential_growth, 6.0), 0.5)

    # ===== 5. 기대 인플레이션 (단순형) =====
    # 이전 인플레이션과 잠재성장률을 섞어서 "앞으로의 물가 기대"를 만듦
    expected_inflation = (
        0.7 * state.inflation
        + 0.3 * max(state.inflation, potential_growth)
    ) * expectation_scale + state.inflation * (1 - expectation_scale)
    # 위 식은 모드에 따라 기대의 민감도가 달라지는 효과

    # ===== 6. 소비 함수 C =====
    # 기준: 100을 "정상 소비"라고 보고, 그 주변에서 위아래로 움직인다고 생각
    # 영향 요인:
    #   - 실업률 ↑ → 소비 ↓
    #   - 금리 ↑ → 소비 ↓
    #   - 소비자 신뢰 ↑ → 소비 ↑
    #   - 기대 인플레이션 ↑ → (미리 소비) + / 실질소득 ↓ - -> 적당히 절충
    base_consumption_index = 100.0

    w_unemp_cons   = -1.2 * shock_scale     # 실업률 1%p ↑ → 소비 지수 약 1.2 ↓
    w_rate_cons    = -2.0 * shock_scale     # 금리 1%p ↑ → 소비 지수 2 ↓
    w_conf_cons    = +0.4 * shock_scale     # 신뢰지수 10 ↑ → 소비 지수 4 ↑
    w_expinf_cons  = +0.3 * shock_scale     # 기대 인플레이션 ↑ → 미리 소비 약간 ↑ (짧은 시계로 가정)

    cons_index = (
        base_consumption_index
        + w_unemp_cons  * (state.unemployment - 5.0)      # 5%를 자연실업률 근처로 가정
        + w_rate_cons   * d_interest
        + w_conf_cons   * (d_conf / 10.0)
        + w_expinf_cons * (expected_inflation - 2.0)      # 2%를 목표 물가로 가정
    )
    # 과도한 폭주 방지
    cons_index = max(min(cons_index, 160.0), 40.0)

    # 소비 성장 기여분 (0을 기준으로 ±)
    cons_gap = cons_index - base_consumption_index

    # ===== 7. 투자 함수 I =====
    # 영향 요인:
    #   - 금리 ↑ → 투자 ↓
    #   - 성장률 ↑ → 투자 ↑
    #   - 기업 투자 지수 ↑ → 투자 ↑
    #   - 글로벌 수요 ↑ → 투자 ↑
    base_invest_index = 100.0

    w_rate_inv    = -3.0 * shock_scale     # 금리 1%p ↑ → 투자 지수 3 ↓
    w_growth_inv  = +1.0 * shock_scale     # 성장률 1%p ↑ → 투자 지수 1 ↑
    w_inv_policy  = +0.8 * shock_scale     # 기업투자지수 10 ↑ → 투자 지수 8 ↑
    w_global_inv  = +0.5 * shock_scale     # 글로벌 수요 10 ↑ → 투자 지수 5 ↑

    inv_index = (
        base_invest_index
        + w_rate_inv   * d_interest
        + w_growth_inv * (state.growth - potential_growth)
        + w_inv_policy * (d_invest / 10.0)
        + w_global_inv * (d_global / 10.0)
    )
    inv_index = max(min(inv_index, 180.0), 30.0)

    inv_gap = inv_index - base_invest_index

    # ===== 8. 1차 성장률: C, I, G, 글로벌 수요, 생산성 반영 =====
    # 여기서는 "총수요 성장률" 느낌으로 구성
    w_cons_growth   = 0.04 * shock_scale   # 소비 지수 10 ↑ → 성장률 0.4%p ↑
    w_inv_growth    = 0.05 * shock_scale   # 투자 지수 10 ↑ → 성장률 0.5%p ↑
    w_gov_growth    = 0.12 * shock_scale   # 정부지출 1%p ↑ → 성장률 0.12%p ↑
    w_global_growth = 0.08 * shock_scale
    w_prod_growth   = 0.05 * shock_scale

    # 비용 측면 (금리, 세금, 전기요금, 유가, 환율)
    w_interest_growth = -0.08 * shock_scale
    w_tax_growth      = -0.04 * shock_scale
    w_elec_growth     = -0.6  * shock_scale
    w_oil_growth      = -0.8  * shock_scale
    w_fx_growth       = +1.0  * shock_scale  # 원화 약세(환율↑)가 수출을 통해 성장률 ↑

    delta_growth_demand = (
        w_cons_growth   * (cons_gap / 10.0) +
        w_inv_growth    * (inv_gap  / 10.0) +
        w_gov_growth    * d_gov +
        w_global_growth * (d_global / 10.0) +
        w_prod_growth   * (d_prod   / 10.0)
    )

    delta_growth_cost = (
        w_interest_growth * d_interest +
        w_tax_growth      * d_tax +
        w_elec_growth     * d_elec +
        w_oil_growth      * d_oil +
        w_fx_growth       * d_fx
    )

    growth_1 = potential_growth + delta_growth_demand + delta_growth_cost

    # ===== 9. 물가 (비용 + 수요 + 금리 효과 + 기대 인플레이션) =====
    w_oil_inf      = +1.2   * shock_scale
    w_elec_inf     = +0.8   * shock_scale
    w_global_inf   = +0.015 * shock_scale
    w_demand_inf   = +0.22  * shock_scale
    w_expinf_inf   = +0.5   * shock_scale  # 기대 인플레이션이 실제 인플에 반영

    demand_gap = growth_1 - potential_growth

    # 금리 인상 → 수요 위축 → 물가 하락
    w_interest_inflation = -0.25 * shock_scale
    delta_inflation_interest = w_interest_inflation * d_interest

    inflation_1 = (
        state.inflation +
        w_oil_inf      * d_oil +
        w_elec_inf     * d_elec +
        w_global_inf   * (d_global / 10.0) +
        w_demand_inf   * demand_gap +
        w_expinf_inf   * (expected_inflation - state.inflation) +
        delta_inflation_interest
    )

    # ===== 10. 실업률 =====
    # 성장률 ↑ → 실업률 ↓, 투자 ↑ → 고용 ↑, 정부지출 ↑ → 고용 ↑
    w_growth_unemp = -0.35 * shock_scale
    w_invest_unemp = -0.03 * shock_scale
    w_gov_unemp    = -0.03 * shock_scale

    unemp_1 = (
        state.unemployment +
        w_growth_unemp * (growth_1 - state.growth) +
        w_invest_unemp * (inv_gap / 10.0) +
        w_gov_unemp    * d_gov
    )

    # -------------------------------------------------
    # 11. 피드백(상호작용) — feedback_scale 적용
    # -------------------------------------------------

    # 실업률 ↑ → 소비 ↓ → 성장률 ↓ (간접 효과를 단순화해서 성장률에 반영)
    fb_growth_from_unemp = -0.05 * feedback_scale * (unemp_1 - state.unemployment)

    # 물가 ↑ → 실질임금 ↓ → 소비 ↓ → 성장률 ↓
    fb_growth_from_infl  = -0.06 * feedback_scale * (inflation_1 - state.inflation)

    # 성장률 변화의 자기 강화/조정
    fb_growth_from_growth = -0.04 * feedback_scale * (growth_1 - state.growth)

    # 환율 ↑ → 수입물가 ↑ → 물가 ↑
    fb_infl_from_fx = 0.30 * feedback_scale * d_fx

    # 실업률 ↑ → 수요 ↓ → 물가 ↓
    fb_infl_from_unemp = -0.12 * feedback_scale * (unemp_1 - state.unemployment)

    # 성장률 ↓ → 실업률 ↑ (추가 오쿤의 법칙 효과)
    fb_unemp_from_growth = -0.20 * feedback_scale * (growth_1 - state.growth)

    # -------------------------------------------------
    # 12. 위기 트리거 (crisis_trigger_scale 적용)
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

    # ===== 13. 최종 지표 =====
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

    # 성장률 변동폭 제한 (너무 폭주 방지)
    final_growth = max(min(final_growth, 15.0), -10.0)

    # ===== 14. GDP =====
    final_gdp = state.gdp * (1 + final_growth / 100)

    return EconomicState(
        gdp=final_gdp,
        inflation=final_inflation,
        unemployment=final_unemployment,
        growth=final_growth,
    )