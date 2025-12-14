import plotly.graph_objs as go
import pandas as pd


def plot_time_series(df: pd.DataFrame):
    """
    여러 지표를 한 그래프에 그리는 통합 그래프.
    필요하면 메인 화면에서 호출해서 사용할 수 있다.
    """
    fig = go.Figure()
    metrics = ["gdp", "inflation", "unemployment", "growth"]
    for m in metrics:
        fig.add_trace(
            go.Scatter(
                x=df["year"],
                y=df[m],
                name=m,
                mode="lines+markers",
            )
        )
    fig.update_layout(
        title="시뮬레이션 결과 추이 (통합)",
        xaxis_title="Year",
        yaxis_title="값",
        legend_title="지표",
    )
    return fig


def plot_metric(
    df: pd.DataFrame,
    metric: str,
    title: str = None,
    color: str = "blue",
):
    """
    단일 지표 라인+마커 그래프.
    color 파라미터로 선과 마커 색 지정 가능.
    """
    title = title or f"{metric} 추이"
    fig = go.Figure(
        data=go.Scatter(
            x=df["year"],
            y=df[metric],
            mode="lines+markers",
            name=metric,
            line=dict(color=color),
            marker=dict(color=color),
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title="Year",
        yaxis_title=metric,
    )
    return fig