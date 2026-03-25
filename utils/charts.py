"""
圖表模組 - 使用 Plotly 建立互動式股票圖表
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Optional


def create_sparkline(data: list[float], color: str = "#2196F3", height: int = 60) -> go.Figure:
    """
    建立迷你走勢圖 (sparkline)，用於指數看板卡片
    """
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            y=data,
            mode="lines",
            line=dict(color=color, width=2),
            fill="tozeroy",
            fillcolor=color.replace(")", ", 0.1)").replace("rgb", "rgba")
            if "rgb" in color
            else f"rgba{tuple(list(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + [0.15])}",
        )
    )
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


def create_indices_overview_chart(
    data_dict: dict[str, pd.DataFrame],
    title: str = "四大指數走勢比較",
) -> go.Figure:
    """
    建立指數總覽比較圖（標準化百分比）
    """
    fig = go.Figure()

    colors = {
        # US
        "^DJI": "#FF9800",
        "^IXIC": "#2196F3",
        "^GSPC": "#4CAF50",
        "^SOX": "#9C27B0",
        "YM=F": "#FF9800",
        "NQ=F": "#2196F3",
        "ES=F": "#4CAF50",
        "SOXX": "#9C27B0",
        # TW
        "^TWII": "#E53935",
        "0050.TW": "#1E88E5",
        "0056.TW": "#43A047",
        "00878.TW": "#FB8C00",
        "00631L.TW": "#D81B60",
        "00632R.TW": "#5E35B1",
        "00929.TW": "#FF6F00",
        # TW Night Session
        "EWT": "#E53935",
        "TSM": "#1E88E5",
    }

    name_map = {
        # US
        "^DJI": "道瓊工業指數",
        "^IXIC": "那斯達克綜合指數",
        "^GSPC": "S&P 500 指數",
        "^SOX": "費城半導體指數",
        "YM=F": "小道瓊期貨",
        "NQ=F": "小那斯達克期貨",
        "ES=F": "小S&P 500期貨",
        "SOXX": "費半ETF (SOXX)",
        # TW
        "^TWII": "加權指數",
        "0050.TW": "元大台灣50",
        "0056.TW": "元大高股息",
        "00878.TW": "國泰永續高股息",
        "00631L.TW": "台灣50正2",
        "00632R.TW": "台灣50反1",
        "00929.TW": "復華科技優息",
        # TW Night Session
        "EWT": "MSCI台灣ETF",
        "TSM": "台積電ADR",
    }

    for symbol, df in data_dict.items():
        if df is not None and not df.empty:
            normalized = (df["Close"] / df["Close"].iloc[0] - 1) * 100
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=normalized,
                    mode="lines",
                    name=name_map.get(symbol, symbol),
                    line=dict(
                        color=colors.get(symbol, "#FFFFFF"),
                        width=2.5,
                    ),
                )
            )

    fig.update_layout(
        title=dict(text=title, font=dict(size=18)),
        height=500,
        template="plotly_dark",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=12),
        ),
        margin=dict(l=60, r=40, t=80, b=50),
        yaxis_title="漲跌幅 (%)",
        xaxis_title="日期",
        hovermode="x unified",
    )

    fig.update_xaxes(
        rangebreaks=[dict(bounds=["sat", "mon"])]
    )

    return fig


def create_candlestick_chart(
    df: pd.DataFrame,
    title: str = "股價走勢",
    show_volume: bool = True,
) -> go.Figure:
    """
    建立 K 線圖（蠟燭圖）含成交量
    """
    if show_volume and "Volume" in df.columns:
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            subplot_titles=(title, "成交量"),
            row_heights=[0.7, 0.3],
        )
    else:
        fig = make_subplots(rows=1, cols=1, subplot_titles=(title,))

    # K 線
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="K線",
            increasing_line_color="#EF5350",   # 紅漲 (台股慣例)
            decreasing_line_color="#26A69A",   # 綠跌
            increasing_fillcolor="#EF5350",
            decreasing_fillcolor="#26A69A",
        ),
        row=1,
        col=1,
    )

    # 移動平均線
    if len(df) >= 5:
        ma5 = df["Close"].rolling(window=5).mean()
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=ma5,
                name="MA5",
                line=dict(color="#FF9800", width=1),
            ),
            row=1,
            col=1,
        )

    if len(df) >= 20:
        ma20 = df["Close"].rolling(window=20).mean()
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=ma20,
                name="MA20",
                line=dict(color="#2196F3", width=1),
            ),
            row=1,
            col=1,
        )

    if len(df) >= 60:
        ma60 = df["Close"].rolling(window=60).mean()
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=ma60,
                name="MA60",
                line=dict(color="#9C27B0", width=1),
            ),
            row=1,
            col=1,
        )

    # 成交量
    if show_volume and "Volume" in df.columns:
        colors = [
            "#EF5350" if df["Close"].iloc[i] >= df["Open"].iloc[i] else "#26A69A"
            for i in range(len(df))
        ]
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df["Volume"],
                name="成交量",
                marker_color=colors,
                opacity=0.7,
            ),
            row=2,
            col=1,
        )

    # 版面設定
    fig.update_layout(
        height=600,
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        margin=dict(l=50, r=50, t=80, b=50),
    )

    fig.update_xaxes(
        rangebreaks=[
            dict(bounds=["sat", "mon"]),  # 隱藏週末
        ]
    )

    return fig


def create_line_chart(
    df: pd.DataFrame,
    title: str = "股價走勢",
    column: str = "Close",
) -> go.Figure:
    """
    建立簡潔的收盤價折線圖
    """
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[column],
            mode="lines",
            name="收盤價",
            line=dict(color="#2196F3", width=2),
            fill="tozeroy",
            fillcolor="rgba(33, 150, 243, 0.1)",
        )
    )

    fig.update_layout(
        title=title,
        height=400,
        template="plotly_dark",
        showlegend=False,
        margin=dict(l=50, r=50, t=80, b=50),
        yaxis_title="價格",
        xaxis_title="日期",
    )

    fig.update_xaxes(
        rangebreaks=[dict(bounds=["sat", "mon"])]
    )

    return fig


def create_comparison_chart(
    data_dict: dict[str, pd.DataFrame],
    title: str = "股票比較（標準化）",
) -> go.Figure:
    """
    建立多檔股票比較圖（以百分比變化標準化）
    data_dict: {symbol: DataFrame}
    """
    fig = go.Figure()

    colors = [
        "#2196F3", "#EF5350", "#4CAF50", "#FF9800",
        "#9C27B0", "#00BCD4", "#FF5722", "#8BC34A",
    ]

    for i, (symbol, df) in enumerate(data_dict.items()):
        if df is not None and not df.empty:
            # 標準化為百分比變化
            normalized = (df["Close"] / df["Close"].iloc[0] - 1) * 100
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=normalized,
                    mode="lines",
                    name=symbol,
                    line=dict(color=colors[i % len(colors)], width=2),
                )
            )

    fig.update_layout(
        title=title,
        height=500,
        template="plotly_dark",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        margin=dict(l=50, r=50, t=80, b=50),
        yaxis_title="漲跌幅 (%)",
        xaxis_title="日期",
    )

    fig.update_xaxes(
        rangebreaks=[dict(bounds=["sat", "mon"])]
    )

    return fig
