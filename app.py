import streamlit as st
import pandas as pd

from data_model import EconomicState, PolicyInput
from visual import plot_metric

# -------------------------------------------------------
# ✅ 엔진 선택 기능
# -------------------------------------------------------
engine_version = st.sidebar.selectbox(
    "엔진 버전 선택",
    ["기본 엔진 (v1)", "상호작용 강화 엔진 (v2)"]
)

if engine_version == "기본 엔진 (v1)":
    from sim_engine import update_one_year
else:
    from sim_engine_v2 import update_one_year


# -------------------------------------------------------
# ✅ 위기 감지 AI
# -------------------------------------------------------
def crisis_advisor(state: EconomicState):
    messages = []
    suggestions = []

    crisis = False

    if state.unemployment > 12:
        crisis = True
        messages.append("실업률이 매우 높습니다.")
        suggestions.append("금리 인하, 정부지출 확대, 기업투자 촉진이 필요합니다.")

    if state.inflation > 6:
        crisis = True
        messages.append("물가가 과도하게 상승하고 있습니다.")
        suggestions.append("금리 인상, 환율 안정, 유가 안정 정책이 필요합니다.")

    if state.growth < -1:
        crisis = True
        messages.append("성장률이 급격히 하락했습니다.")
        suggestions.append("금리 인하, 정부지출 확대, 소비자 신뢰 회복 정책이 필요합니다.")

    if not crisis:
        return "현재 위기 상황은 아닙니다.", ["정책을 안정적으로 유지해도 됩니다."]

    return "⚠️ 경제 위기 감지!", messages + suggestions


# -------------------------------------------------------
# ✅ 정책 추천 AI
# -------------------------------------------------------
def recommend_policy(goal: str):
    if goal == "성장률 상승":
        return [
            "금리를 인하하세요.",
            "정부지출을 확대하세요.",
            "기업투자 지수를 높이세요.",
            "생산성 향상 정책을 강화하세요.",
            "글로벌 수요 개선을 위한 수출 지원 정책을 고려하세요.",
        ]

    if goal == "물가 안정":
        return [
            "금리를 인상하세요.",
            "환율 안정을 위한 외환시장 개입을 고려하세요.",
            "전기요금 및 에너지 가격을 안정시키세요.",
            "정부지출을 과도하게 늘리지 마세요.",
        ]

    if goal == "실업률 감소":
        return [
            "금리를 인하하세요.",
            "기업투자 지수를 높이세요.",
            "정부지출을 확대해 고용을 창출하세요.",
            "소비자 신뢰 회복 정책을 시행하세요.",
        ]

    return ["목표를 선택해주세요."]


# -------------------------------------------------------
# ✅ 세션 상태 초기화
# -------------------------------------------------------
if "current_state" not in st.session_state:
    st.session_state.current_state = EconomicState(
        gdp=10_000_000.0,
        inflation=1.2,
        unemployment=14.5,
        growth=2.5,
    )
if "results" not in st.session_state:
    st.session_state.results = []


# -------------------------------------------------------
# ✅ 사이드바: 초기 경제지표 설정
# -------------------------------------------------------
st.sidebar.header("초기 경제지표 설정")

if "init_gdp" not in st.session_state:
    st.session_state.init_gdp          = st.session_state.current_state.gdp
    st.session_state.init_inflation    = st.session_state.current_state.inflation
    st.session_state.init_unemployment = st.session_state.current_state.unemployment
    st.session_state.init_growth       = st.session_state.current_state.growth

gdp_init = st.sidebar.number_input("초기 GDP (달러)", value=st.session_state.init_gdp, step=100_000.0)
inflation_init = st.sidebar.number_input("초기 물가상승률 (%)", value=st.session_state.init_inflation, step=0.1)
unemployment_init = st.sidebar.number_input("초기 실업률 (%)", value=st.session_state.init_unemployment, step=0.1)
growth_init = st.sidebar.number_input("초기 경제성장률 (%)", value=st.session_state.init_growth, step=0.1)

if st.sidebar.button("초기값 적용"):
    st.session_state.current_state = EconomicState(
        gdp=gdp_init,
        inflation=inflation_init,
        unemployment=unemployment_init,
        growth=growth_init,
    )
    st.session_state.results.clear()

st.sidebar.markdown("---")


# -------------------------------------------------------
# ✅ 모드 선택
# -------------------------------------------------------
mode = st.sidebar.selectbox(
    "경제 모델 모드 선택",
    ["안정형", "현실형", "위기형"],
)

st.sidebar.markdown("---")


# -------------------------------------------------------
# ✅ 정책 입력
# -------------------------------------------------------
st.sidebar.header("정책 및 외생 변수")

st.sidebar.subheader("통화·세제·비용·환율")
interest_rate = st.sidebar.number_input("기준금리 (%)", value=1.5, step=0.1)
corporate_tax = st.sidebar.number_input("법인세율 (%)", value=25.0, step=0.5)
electricity_cost = st.sidebar.number_input("공업용 전기요금 (원/kWh)", value=100.0, step=1.0)
exchange_rate = st.sidebar.number_input("원-달러 환율", value=1200.0, step=10.0)

st.sidebar.subheader("재정·심리·투자")
government_spending_ratio = st.sidebar.number_input("정부지출 비율 (GDP 대비 %)", value=20.0, step=1.0)
consumer_confidence = st.sidebar.slider("소비자 신뢰지수 (0~200)", 0, 200, 100, 5)
corporate_investment = st.sidebar.slider("기업 투자지수 (0~200)", 0, 200, 100, 5)

st.sidebar.subheader("대외 환경·생산성")
global_demand = st.sidebar.slider("글로벌 수요 (0~200)", 0, 200, 100, 5)
oil_price = st.sidebar.number_input("유가 (달러/배럴)", value=70.0, step=5.0)
productivity = st.sidebar.slider("생산성 지수 (0~200)", 0, 200, 100, 5)

policy = PolicyInput(
    interest_rate=interest_rate,
    corporate_tax=corporate_tax,
    electricity_cost=electricity_cost,
    exchange_rate=exchange_rate,
    government_spending_ratio=government_spending_ratio,
    consumer_confidence=consumer_confidence,
    corporate_investment=corporate_investment,
    global_demand=global_demand,
    oil_price=oil_price,
    productivity=productivity,
)


# -------------------------------------------------------
# ✅ 시뮬레이션 실행 / 초기화 버튼
# -------------------------------------------------------
col1, col2 = st.columns(2)
with col1:
    if st.button("1년 시뮬레이션 진행"):
        next_state = update_one_year(st.session_state.current_state, policy, mode)
        st.session_state.results.append(next_state.to_series(len(st.session_state.results) + 1))
        st.session_state.current_state = next_state

with col2:
    if st.button("전체 초기화"):
        st.session_state.current_state = EconomicState(
            gdp=gdp_init,
            inflation=inflation_init,
            unemployment=unemployment_init,
            growth=growth_init,
        )
        st.session_state.results.clear()


# -------------------------------------------------------
# ✅ 메인 화면: 결과 출력
# -------------------------------------------------------
st.header("시뮬레이션 결과 (연 단위)")
st.info(f"현재 사용 중인 엔진: {engine_version}")

if st.session_state.results:
    df = pd.DataFrame(st.session_state.results)
    st.dataframe(df.set_index("year"), use_container_width=True)

    st.subheader("GDP 추이")
    st.plotly_chart(plot_metric(df, "gdp", "GDP 추이", "royalblue"), use_container_width=True)

    st.subheader("물가상승률 추이")
    st.plotly_chart(plot_metric(df, "inflation", "물가상승률 추이", "firebrick"), use_container_width=True)

    st.subheader("실업률 추이")
    st.plotly_chart(plot_metric(df, "unemployment", "실업률 추이", "forestgreen"), use_container_width=True)

    st.subheader("경제성장률 추이")
    st.plotly_chart(plot_metric(df, "growth", "경제성장률 추이", "darkorange"), use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("CSV 다운로드", data=csv, file_name="simulation_results.csv", mime="text/csv")

    # ---------------------------------------------------
    # ✅ 위기 감지 AI
    # ---------------------------------------------------
    st.markdown("---")
    st.subheader("🛑 위기 감지 및 대응 AI")

    crisis_title, crisis_msgs = crisis_advisor(st.session_state.current_state)
    st.write(f"### {crisis_title}")
    for msg in crisis_msgs:
        st.write("- " + msg)

    # ---------------------------------------------------
    # ✅ 정책 추천 AI
    # ---------------------------------------------------
    st.markdown("---")
    st.subheader("🎯 정책 추천 AI")

    goal = st.selectbox("정책 목표를 선택하세요:", ["성장률 상승", "물가 안정", "실업률 감소"])

    if st.button("정책 추천 받기"):
        recs = recommend_policy(goal)
        st.write("### ✅ 추천 정책")
        for r in recs:
            st.write("- " + r)

else:
    st.write("아직 시뮬레이션이 실행되지 않았습니다.")