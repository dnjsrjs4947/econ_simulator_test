import streamlit as st
import pandas as pd

from data_model import EconomicState, PolicyInput
from sim_engine import update_one_year
from visual import plot_metric

st.set_page_config(page_title="거시경제 정책 시뮬레이터 (한국형)", layout="wide")

# 1) 세션 상태 초기화
if "current_state" not in st.session_state:
    st.session_state.current_state = EconomicState(
        gdp=10_000_000.0,   # 초기 GDP
        inflation=1.2,      # 초기 물가상승률 (%)
        unemployment=14.5,  # 초기 실업률 (%)
        growth=2.5,         # 초기 성장률 (%)
    )
if "results" not in st.session_state:
    st.session_state.results = []

# 2) 사이드바: 초기 경제지표 설정
st.sidebar.header("초기 경제지표 설정")

if "init_gdp" not in st.session_state:
    st.session_state.init_gdp          = st.session_state.current_state.gdp
    st.session_state.init_inflation    = st.session_state.current_state.inflation
    st.session_state.init_unemployment = st.session_state.current_state.unemployment
    st.session_state.init_growth       = st.session_state.current_state.growth

gdp_init = st.sidebar.number_input(
    "초기 GDP (달러)",
    value=st.session_state.init_gdp,
    step=100_000.0,
    key="init_gdp",
)
inflation_init = st.sidebar.number_input(
    "초기 물가상승률 (%)",
    value=st.session_state.init_inflation,
    step=0.1,
    key="init_inflation",
)
unemployment_init = st.sidebar.number_input(
    "초기 실업률 (%)",
    value=st.session_state.init_unemployment,
    step=0.1,
    key="init_unemployment",
)
growth_init = st.sidebar.number_input(
    "초기 경제성장률 (%)",
    value=st.session_state.init_growth,
    step=0.1,
    key="init_growth",
)

if st.sidebar.button("초기값 적용"):
    st.session_state.current_state = EconomicState(
        gdp=gdp_init,
        inflation=inflation_init,
        unemployment=unemployment_init,
        growth=growth_init,
    )
    st.session_state.results.clear()

st.sidebar.markdown("---")

# ✅ 3) 모드 선택 기능 추가
mode = st.sidebar.selectbox(
    "경제 모델 모드 선택",
    ["안정형", "현실형", "위기형"]
)

st.sidebar.markdown("---")

# 4) 사이드바: 정책 파라미터 입력
st.sidebar.header("정책 및 외생 변수")

st.sidebar.subheader("통화·세제·비용·환율")
interest_rate = st.sidebar.number_input("기준금리 (%)", value=1.5, step=0.1)
corporate_tax = st.sidebar.number_input("법인세율 (%)", value=25.0, step=0.5)
electricity_cost = st.sidebar.number_input(
    "공업용 전기요금 (원/kWh)", value=100.0, step=1.0
)
exchange_rate = st.sidebar.number_input(
    "원-달러 환율", value=1200.0, step=10.0
)

st.sidebar.subheader("재정·심리·투자")
government_spending_ratio = st.sidebar.number_input(
    "정부지출 비율 (GDP 대비 %)", value=20.0, step=1.0
)
consumer_confidence = st.sidebar.slider(
    "소비자 신뢰지수 (0~200, 100=보통)",
    min_value=0,
    max_value=200,
    value=100,
    step=5,
)
corporate_investment = st.sidebar.slider(
    "기업 투자지수 (0~200, 100=보통)",
    min_value=0,
    max_value=200,
    value=100,
    step=5,
)

st.sidebar.subheader("대외 환경·생산성")
global_demand = st.sidebar.slider(
    "글로벌 수요 (0~200, 100=보통)",
    min_value=0,
    max_value=200,
    value=100,
    step=5,
)
oil_price = st.sidebar.number_input(
    "유가 (달러/배럴)", value=70.0, step=5.0
)
productivity = st.sidebar.slider(
    "생산성 지수 (0~200, 100=보통)",
    min_value=0,
    max_value=200,
    value=100,
    step=5,
)

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

# 5) 버튼: 시뮬레이션 실행 / 전체 초기화
col1, col2 = st.columns(2)
with col1:
    if st.button("1년 시뮬레이션 진행"):
        next_state = update_one_year(st.session_state.current_state, policy, mode)
        st.session_state.results.append(
            next_state.to_series(len(st.session_state.results) + 1)
        )
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

# 6) 메인 영역: 결과 테이블 & 개별 그래프
st.header("시뮬레이션 결과 (연 단위)")
st.caption("※ 모드에 따라 경제 반응 강도가 달라집니다.")

if st.session_state.results:
    df = pd.DataFrame(st.session_state.results)
    st.dataframe(df.set_index("year"), use_container_width=True)

    st.subheader("GDP 추이")
    st.plotly_chart(
        plot_metric(df, "gdp", title="GDP 추이", color="royalblue"),
        use_container_width=True,
    )

    st.subheader("물가상승률 추이")
    st.plotly_chart(
        plot_metric(df, "inflation", title="물가상승률 추이", color="firebrick"),
        use_container_width=True,
    )

    st.subheader("실업률 추이")
    st.plotly_chart(
        plot_metric(df, "unemployment", title="실업률 추이", color="forestgreen"),
        use_container_width=True,
    )

    st.subheader("경제성장률 추이")
    st.plotly_chart(
        plot_metric(df, "growth", title="경제성장률 추이", color="darkorange"),
        use_container_width=True,
    )

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "CSV 다운로드",
        data=csv,
        file_name="simulation_results.csv",
        mime="text/csv",
    )
else:
    st.write("아직 시뮬레이션이 실행되지 않았습니다.")