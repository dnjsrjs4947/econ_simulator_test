from data_model import EconomicState, PolicyInput


def update_one_year(state: EconomicState, policy: PolicyInput, mode: str) -> EconomicState:
    """
    한국형 동태 거시경제 시뮬레이터 (모드 선택 기능 포함)
    mode:
        - "안정형": 충격에 둔감, 경제가 쉽게 무너지지 않음
        - "현실형": 충격에 적당히 반응, 실제 한국 경제 느낌
        - "위기형": 충격에 매우 민감, 정책 실수 시 경제 붕괴 가능
    """

    # ===== 1. 모드별 계수 스케일 설정 =====
    if mode == "안정형":
        shock_scale = 0.5     # 충격 절반만 반영
        feedback_scale = 0.6  # 피드백 약하게
        potential_scale = 0.7 # 잠재성장률 변화도 약하게
    elif mode == "현실형":
        shock_scale = 1.0     # 기본값
        feedback_scale = 1.0
        potential_scale = 1.0
    elif mode == "위기형":
        shock_scale = 1.8     # 충격 1.8배
        feedback_scale = 2.0  # 피드백 2배 (악순환 강화)
        potential_scale = 1.5 # 잠재성장률도 크게 흔들림
    else:
        shock_scale = 1.0
        feedback_scale = 1.0
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

    # ===== 7. 물가 =====
    w_oil_inf    = +1.2 * shock_scale
    w_elec_inf   = +0.8 * shock_scale
    w_global_inf = +0.015 * shock_scale
    w_demand_inf = +0.22 * shock_scale

    demand_gap = growth_1 - potential_growth

    inflation_1 = (
        state.inflation +
        w_oil_inf    * d_oil +
        w_elec_inf   * d_elec +
        w_global_inf * (d_global / 10.0) +
        w_demand_inf * demand_gap
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

    fb_growth_from_unemp = -0.05 * feedback_scale * (unemp_1 - state.unemployment)
    fb_growth_from_infl  = -0.06 * feedback_scale * (inflation_1 - state.inflation)
    fb_growth_from_growth = -0.04 * feedback_scale * (growth_1 - state.growth)

    fb_infl_from_fx = 0.30 * feedback_scale * d_fx
    fb_infl_from_unemp = -0.12 * feedback_scale * (unemp_1 - state.unemployment)

    fb_unemp_from_growth = -0.20 * feedback_scale * (growth_1 - state.growth)

    # ===== 10. 최종 지표 =====
    final_growth = growth_1 + fb_growth_from_unemp + fb_growth_from_infl + fb_growth_from_growth
    final_inflation = inflation_1 + fb_infl_from_fx + fb_infl_from_unemp
    final_unemployment = unemp_1 + fb_unemp_from_growth

    # 성장률 변동폭 제한
    final_growth = max(min(final_growth, 15.0), -10.0)

    # ===== 11. GDP =====
    final_gdp = state.gdp * (1 + final_growth / 100)

    return EconomicState(
        gdp=final_gdp,
        inflation=final_inflation,
        unemployment=final_unemployment,
        growth=final_growth,
    )