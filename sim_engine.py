from data_model import EconomicState, PolicyInput


def update_one_year(state: EconomicState, policy: PolicyInput) -> EconomicState:
    """
    교육용 거시경제 반응 모델 (한국형, 금리 영향 완화 + 피드백 강화).

    구조:
    1) 정책·외생 변수 → 1차 효과로 성장률/물가/실업에 영향
    2) 경제지표들 사이의 피드백(상호작용)을 한 번 더 반영
    """

    # ===== 1. 기준(중립) 값 설정 =====
    neutral_interest     = 2.0       # 중립 금리 (%)
    neutral_corp_tax     = 25.0      # 중립 법인세율 (%)
    neutral_elec_cost    = 100.0     # 기준 공업용 전기요금
    neutral_fx           = 1200.0    # 기준 환율 (원/달러)

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

    # ===== 3. 기본 반응 계수 (한국형, 금리 비중 낮춤) =====
    # 성장률: 금리 효과 ↓, 투자·글로벌·생산성·심리 효과 ↑
    w_interest_growth = -0.12  # 금리 1%p ↑ → 성장률 약 -0.12%p (이전보다 절반 이하)
    w_tax_growth      = -0.04
    w_elec_growth     = -0.7
    w_oil_growth      = -0.9
    w_fx_growth       = +1.2   # 원화 약세 → 수출↑ → 성장↑

    w_gov_growth      = +0.08
    w_conf_growth     = +0.025 # 소비자신뢰 10 ↑ → 성장률 +0.25%p
    w_invest_growth   = +0.04  # 기업투자 10 ↑ → 성장률 +0.4%p (투자 비중 강화)
    w_global_growth   = +0.045 # 글로벌 10 ↑ → 성장률 +0.45%p
    w_prod_growth     = +0.018 # 생산성 10 ↑ → 성장률 +0.18%p

    # 물가
    w_oil_inflation    = +1.3
    w_elec_inflation   = +0.9
    w_global_inflation = +0.018
    w_demand_inflation = +0.25

    # 실업률
    w_growth_unemp = -0.32
    w_invest_unemp = -0.02
    w_gov_unemp    = -0.03

    # 세금의 GDP 직접효과
    w_tax_gdp      = -0.0015

    # ===== 4. 1차 효과: 정책/외생 → 성장률 =====
    delta_growth_1 = 0.0
    delta_growth_1 += w_interest_growth * d_interest
    delta_growth_1 += w_tax_growth      * d_tax
    delta_growth_1 += w_elec_growth     * d_elec
    delta_growth_1 += w_oil_growth      * d_oil
    delta_growth_1 += w_fx_growth       * d_fx

    delta_growth_1 += w_gov_growth      * d_gov
    delta_growth_1 += w_conf_growth     * (d_conf   / 10.0)
    delta_growth_1 += w_invest_growth   * (d_invest / 10.0)
    delta_growth_1 += w_global_growth   * (d_global / 10.0)
    delta_growth_1 += w_prod_growth     * (d_prod   / 10.0)

    growth_1 = potential_growth + delta_growth_1
    growth_1 = max(min(growth_1, 10.0), -5.0)

    # ===== 5. 1차 효과: GDP =====
    gdp_after_growth = state.gdp * (1 + growth_1 / 100)
    delta_gdp_tax    = w_tax_gdp * d_tax / 100 * state.gdp
    gdp_1            = gdp_after_growth + delta_gdp_tax
    gdp_1            = max(gdp_1, 0.0)

    # ===== 6. 1차 효과: 물가 =====
    demand_gap_1    = growth_1 - potential_growth

    delta_infl_1  = 0.0
    delta_infl_1 += w_oil_inflation    * d_oil
    delta_infl_1 += w_elec_inflation   * d_elec
    delta_infl_1 += w_global_inflation * (d_global / 10.0)
    delta_infl_1 += w_demand_inflation * demand_gap_1

    inflation_1 = state.inflation + delta_infl_1
    inflation_1 = max(inflation_1, -5.0)

    # ===== 7. 1차 효과: 실업률 =====
    delta_unemp_1  = 0.0
    delta_unemp_1 += w_growth_unemp * (growth_1 - state.growth)
    delta_unemp_1 += w_invest_unemp * (d_invest / 10.0)
    delta_unemp_1 += w_gov_unemp    * d_gov

    unemp_1 = state.unemployment + delta_unemp_1
    unemp_1 = max(min(unemp_1, 50.0), 0.0)

    # -------------------------------------------------
    # ===== 8. 피드백(상호작용) 계산 =====

    # (1) 실업률 ↑ → 소비 ↓ → 물가 ↓
    fb_inf_from_unemp = -0.18 * (unemp_1 - state.unemployment)

    # (2) 물가 ↑ → 실질임금 ↓ → 소비 ↓ → 성장률 ↓
    fb_growth_from_inf_real_income = -0.09 * (inflation_1 - state.inflation)

    # (3) 성장률 변화 → 고용 (추가 오쿤)
    fb_unemp_from_growth = -0.22 * (growth_1 - state.growth)

    # (4) 환율 ↑ → 수입물가 ↑ → 물가 ↑
    fb_inf_from_fx = 0.35 * d_fx

    # (5) 물가 ↑ → 통화 긴축 기대 → 성장률 조금 더 ↓ (정책 기대 반응)
    fb_growth_from_inf_policy = -0.04 * (inflation_1 - state.inflation)

    # (6) 실업률 ↑ → 소비심리 악화 → 성장률 ↓
    fb_growth_from_unemp_conf = -0.03 * (unemp_1 - state.unemployment)

    # (7) 성장률 ↓ → 소비심리 또 악화 → 다음 해에도 여파
    fb_conf_from_growth = -0.5 * (growth_1 - state.growth)
    # 이건 직접 지표에 안 넣고, "심리가 성장에 미치는 효과"로 간접 반영
    fb_growth_from_conf_feedback = 0.015 * (fb_conf_from_growth)

    # ===== 9. 피드백 반영 후 최종 변화량 =====
    delta_infl_total = delta_infl_1 + fb_inf_from_unemp + fb_inf_from_fx
    delta_growth_total = (
        delta_growth_1
        + fb_growth_from_inf_real_income
        + fb_growth_from_inf_policy
        + fb_growth_from_unemp_conf
        + fb_growth_from_conf_feedback
    )
    delta_unemp_total = delta_unemp_1 + fb_unemp_from_growth

    # ===== 10. 최종 지표 계산 =====
    final_growth       = potential_growth + delta_growth_total
    final_growth       = max(min(final_growth, 10.0), -5.0)

    final_inflation    = state.inflation + delta_infl_total
    final_inflation    = max(final_inflation, -5.0)

    final_unemployment = state.unemployment + delta_unemp_total
    final_unemployment = max(min(final_unemployment, 50.0), 0.0)

    final_gdp = state.gdp * (1 + final_growth / 100)
    final_gdp += w_tax_gdp * d_tax / 100 * state.gdp
    final_gdp = max(final_gdp, 0.0)

    return EconomicState(
        gdp=final_gdp,
        inflation=final_inflation,
        unemployment=final_unemployment,
        growth=final_growth,
    )