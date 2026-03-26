"""
📈 台股美股查詢 App
使用 Streamlit + yfinance 建立的股票查詢工具
支援台股 (TWSE/OTC) 與美股 (NYSE/NASDAQ) 即時查詢
"""

import streamlit as st
import json
import os
from datetime import datetime
from typing import Optional

from datetime import timedelta
import pytz

def _now_tw():
    return datetime.now(pytz.timezone("Asia/Taipei"))

from utils.stock_data import (
    get_ticker_symbol,
    get_stock_info,
    get_stock_history,
    get_index_quote,
    get_batch_index_quotes,
    get_market_status,
    format_number,
    format_volume,
)
from utils.charts import (
    create_candlestick_chart,
    create_line_chart,
    create_comparison_chart,
    create_sparkline,
    create_indices_overview_chart,
)
from utils.taifex_data import (
    get_taifex_main_contracts,
    get_taifex_session_status,
    TAIFEX_PRODUCTS,
)

# ─── 頁面設定 ───────────────────────────────────────
st.set_page_config(
    page_title="📈 台股美股查詢",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── 自訂樣式 ───────────────────────────────────────
st.markdown(
    """
    <style>
    .metric-card {
        background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%);
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #3d3d5c;
        text-align: center;
    }
    .price-up { color: #EF5350; }
    .price-down { color: #26A69A; }
    .big-price {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0;
    }
    .stock-header {
        display: flex;
        align-items: center;
        gap: 16px;
        margin-bottom: 16px;
    }
    div[data-testid="stMetric"] {
        background: rgba(30, 30, 46, 0.6);
        border: 1px solid rgba(61, 61, 92, 0.5);
        border-radius: 10px;
        padding: 12px 16px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ─── 載入台股代碼對照表 ─────────────────────────────
@st.cache_data
def load_tw_stocks():
    data_path = os.path.join(os.path.dirname(__file__), "data", "tw_stocks.json")
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


tw_stocks = load_tw_stocks()
# 反向對照：代碼 → 名稱
tw_code_to_name = {v: k for k, v in tw_stocks.items()}

# ─── 常用美股清單 ──────────────────────────────────
US_POPULAR = {
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "Google": "GOOGL",
    "Amazon": "AMZN",
    "NVIDIA": "NVDA",
    "Tesla": "TSLA",
    "Meta": "META",
    "AMD": "AMD",
    "Netflix": "NFLX",
    "Taiwan Semi (ADR)": "TSM",
    "S&P 500 ETF": "SPY",
    "NASDAQ 100 ETF": "QQQ",
    "Dow Jones ETF": "DIA",
}

# ─── 美股四大指數與期貨指數定義 ────────────────────────
US_INDICES = {
    "道瓊工業指數": {"symbol": "^DJI", "emoji": "🏭", "desc": "Dow Jones Industrial Average", "color": "#FF9800"},
    "那斯達克綜合指數": {"symbol": "^IXIC", "emoji": "💻", "desc": "NASDAQ Composite", "color": "#2196F3"},
    "S&P 500 指數": {"symbol": "^GSPC", "emoji": "📊", "desc": "S&P 500", "color": "#4CAF50"},
    "費城半導體指數": {"symbol": "^SOX", "emoji": "🔬", "desc": "PHLX Semiconductor (SOX)", "color": "#9C27B0"},
}

US_FUTURES = {
    "小道瓊 (YM)": {"symbol": "YM=F", "emoji": "🔶", "desc": "E-mini Dow Jones Futures", "color": "#FF9800", "index_ref": "^DJI"},
    "小那斯達克 (NQ)": {"symbol": "NQ=F", "emoji": "🔷", "desc": "E-mini NASDAQ 100 Futures", "color": "#2196F3", "index_ref": "^IXIC"},
    "小S&P 500 (ES)": {"symbol": "ES=F", "emoji": "🟢", "desc": "E-mini S&P 500 Futures", "color": "#4CAF50", "index_ref": "^GSPC"},
    "費半ETF (SOXX)": {"symbol": "SOXX", "emoji": "🔬", "desc": "iShares Semiconductor ETF", "color": "#9C27B0", "index_ref": "^SOX"},
}

# ─── 台股指數與期貨定義 ─────────────────────────────────
TW_INDICES = {
    "加權指數": {"symbol": "^TWII", "emoji": "🇹🇼", "desc": "TAIEX 加權股價指數", "color": "#E53935"},
    "元大台灣50": {"symbol": "0050.TW", "emoji": "📦", "desc": "元大台灣50 ETF", "color": "#1E88E5"},
    "元大高股息": {"symbol": "0056.TW", "emoji": "💰", "desc": "元大高股息 ETF", "color": "#43A047"},
    "國泰永續高股息": {"symbol": "00878.TW", "emoji": "🌟", "desc": "國泰永續高股息 ETF", "color": "#FB8C00"},
}

TW_FUTURES_PROXY = {
    "台灣50 ETF": {"symbol": "0050.TW", "emoji": "📦", "desc": "元大台灣50 (台指追蹤)", "color": "#1E88E5", "index_ref": "^TWII"},
    "台灣50正2": {"symbol": "00631L.TW", "emoji": "🚀", "desc": "元大台灣50正2 (槓桿ETF)", "color": "#D81B60", "index_ref": "^TWII"},
    "台灣50反1": {"symbol": "00632R.TW", "emoji": "📉", "desc": "元大台灣50反1 (反向ETF)", "color": "#5E35B1", "index_ref": "^TWII"},
    "復華台灣科技優息": {"symbol": "00929.TW", "emoji": "🔥", "desc": "復華台灣科技優息 ETF", "color": "#FF6F00", "index_ref": "^TWII"},
}

# ─── 台指期夜盤：使用 TAIFEX 即時 API (已替換舊版 proxy) ───

# ─── 側邊欄 ─────────────────────────────────────────
with st.sidebar:
    st.title("📈 股票查詢")
    st.markdown("---")

    # 頁面選擇
    page = st.radio(
        "📑 功能選單",
        ["🏠 指數總覽", "🔍 個股查詢"],
        horizontal=True,
    )

    st.markdown("---")

    # ⏱️ 自動刷新設定
    st.subheader("⏱️ 即時更新")
    auto_refresh = st.toggle("自動刷新", value=True, help="開啟後每 30 秒自動更新指數資料")
    refresh_interval = st.select_slider(
        "刷新間隔",
        options=[15, 30, 60, 120],
        value=30,
        format_func=lambda x: f"{x} 秒",
        help="自動刷新的時間間隔",
    )

    # 手動刷新按鈕
    if st.button("🔄 立即刷新", use_container_width=True):
        st.cache_data.clear()

    # 市場狀態
    mkt_status = get_market_status()
    st.markdown(
        f"""
        <div style='background: rgba(30,30,46,0.6); border-radius: 8px; padding: 10px; 
                    border: 1px solid rgba(61,61,92,0.5); font-size: 0.82rem;'>
            <div style='margin-bottom: 4px;'>🇺🇸 美股: {mkt_status['us_status']}</div>
            <div style='margin-bottom: 4px;'>🇹🇼 台股: {mkt_status['tw_status']}</div>
            <div style='margin-bottom: 4px;'>🌙 台指夜盤: {mkt_status['tw_night_status']}</div>
            <div style='color: #666; font-size: 0.75rem;'>🕐 {mkt_status['us_time']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # 市場選擇
    market = st.radio(
        "🌐 選擇市場",
        ["台股 (TWSE)", "美股 (US)"],
        horizontal=True,
    )

    st.markdown("---")

    # 股票代碼輸入
    if market == "台股 (TWSE)":
        st.subheader("🇹🇼 台股查詢")

        # 快速選擇
        quick_select = st.selectbox(
            "⚡ 快速選擇熱門股票",
            ["-- 自行輸入 --"] + list(tw_stocks.keys()),
        )

        if quick_select != "-- 自行輸入 --":
            stock_code = tw_stocks[quick_select]
        else:
            stock_code = st.text_input(
                "輸入股票代碼",
                placeholder="例如: 2330",
                help="輸入台股代碼，如 2330（台積電）、0050（元大台灣50）",
            )
    else:
        st.subheader("🇺🇸 美股查詢")

        quick_select = st.selectbox(
            "⚡ 快速選擇熱門股票",
            ["-- 自行輸入 --"] + list(US_POPULAR.keys()),
        )

        if quick_select != "-- 自行輸入 --":
            stock_code = US_POPULAR[quick_select]
        else:
            stock_code = st.text_input(
                "輸入股票代碼",
                placeholder="例如: AAPL",
                help="輸入美股 Ticker，如 AAPL（Apple）、NVDA（NVIDIA）",
            )

    st.markdown("---")

    # 時間區間
    period_options = {
        "1週": "5d",
        "1個月": "1mo",
        "3個月": "3mo",
        "6個月": "6mo",
        "1年": "1y",
        "2年": "2y",
        "5年": "5y",
        "年初至今": "ytd",
    }
    selected_period = st.select_slider(
        "📅 時間區間",
        options=list(period_options.keys()),
        value="1年",
    )
    period = period_options[selected_period]

    # 圖表類型
    chart_type = st.radio(
        "📊 圖表類型",
        ["K線圖", "折線圖"],
        horizontal=True,
    )

    st.markdown("---")

    # 查詢按鈕
    search_clicked = st.button(
        "🔍 查詢股票",
        use_container_width=True,
        type="primary",
    )

    st.markdown("---")

    # 股票比較功能
    st.subheader("📊 股票比較")
    compare_input = st.text_input(
        "輸入多個代碼（逗號分隔）",
        placeholder="2330,2317,2454" if market == "台股 (TWSE)" else "AAPL,MSFT,NVDA",
        help="輸入多個股票代碼以比較走勢",
    )
    compare_clicked = st.button(
        "📈 比較走勢",
        use_container_width=True,
    )


# ─── 主畫面 ─────────────────────────────────────────

# 標題
st.markdown(
    """
    <h1 style='text-align: center; margin-bottom: 5px;'>
        📈 台股美股即時查詢
    </h1>
    <p style='text-align: center; color: #888; margin-bottom: 30px;'>
        支援台灣上市櫃股票、美股四大指數與期貨指數即時行情
    </p>
    """,
    unsafe_allow_html=True,
)


# ════════════════════════════════════════════════════════
# ─── 指數看板功能 ────────────────────────────────────────
# ════════════════════════════════════════════════════════

def render_index_card(name: str, meta: dict, quote: Optional[dict]):
    """渲染單個指數/期貨卡片"""
    emoji = meta["emoji"]
    color = meta["color"]
    desc = meta["desc"]

    if quote is None:
        st.markdown(
            f"""
            <div style='background: rgba(30,30,46,0.8); border-radius: 12px; padding: 16px;
                        border: 1px solid rgba(61,61,92,0.5); min-height: 140px;'>
                <div style='font-size: 0.85rem; color: #888;'>{emoji} {desc}</div>
                <div style='font-size: 1.1rem; font-weight: bold; margin: 4px 0;'>{name}</div>
                <div style='color: #666;'>載入中...</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    price = quote["price"]
    change = quote["change"]
    change_pct = quote["change_pct"]

    if change >= 0:
        arrow = "▲"
        chg_color = "#EF5350"
        sign = "+"
    else:
        arrow = "▼"
        chg_color = "#26A69A"
        sign = ""

    # 即時 / 收盤標記
    rt_badge = ""
    if quote.get("is_realtime"):
        rt_badge = f"<span style='color: #4CAF50; font-size: 0.7rem;'>⚡ 即時 {quote.get('last_update', '')}</span>"
    else:
        rt_badge = f"<span style='color: #888; font-size: 0.7rem;'>📅 收盤 {quote.get('last_update', '')}</span>"

    st.markdown(
        f"""
        <div style='background: rgba(30,30,46,0.8); border-radius: 12px; padding: 16px;
                    border-left: 4px solid {color}; border-top: 1px solid rgba(61,61,92,0.5);
                    border-right: 1px solid rgba(61,61,92,0.5); border-bottom: 1px solid rgba(61,61,92,0.5);
                    min-height: 160px;'>
            <div style='font-size: 0.8rem; color: #888;'>{emoji} {desc}</div>
            <div style='font-size: 1.05rem; font-weight: bold; margin: 4px 0;'>{name}</div>
            <div style='font-size: 1.6rem; font-weight: bold; color: {chg_color}; margin: 6px 0;'>
                {price:,.2f}
            </div>
            <div style='font-size: 0.95rem; color: {chg_color};'>
                {arrow} {sign}{change:,.2f} ({sign}{change_pct:.2f}%)
            </div>
            <div style='margin-top: 6px;'>{rt_badge}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_taifex_card(contract: dict):
    """渲染 TAIFEX 期貨即時卡片"""
    name = contract.get("product_name", contract.get("name", ""))
    emoji = contract.get("emoji", "📊")
    color = contract.get("color", "#888")
    price = contract.get("price", 0)
    change = contract.get("change", 0)
    change_pct = contract.get("change_pct", 0)
    session_label = "夜盤" if contract.get("session") == "night" else "日盤"
    symbol_id = contract.get("symbol_id", "")

    if price == 0:
        st.markdown(
            f"""<div style='background: rgba(30,30,46,0.8); border-radius: 12px; padding: 16px;
                        border: 1px solid rgba(61,61,92,0.5); min-height: 140px;'>
                <div style='font-size: 0.85rem; color: #888;'>{emoji} {name} ({session_label})</div>
                <div style='font-size: 1.1rem; font-weight: bold; margin: 4px 0;'>{symbol_id}</div>
                <div style='color: #666;'>尚無報價</div>
            </div>""",
            unsafe_allow_html=True,
        )
        return

    if change > 0:
        arrow = "▲"
        chg_color = "#EF5350"
        sign = "+"
    elif change < 0:
        arrow = "▼"
        chg_color = "#26A69A"
        sign = ""
    else:
        arrow = "—"
        chg_color = "#999"
        sign = ""

    is_trading = contract.get("is_trading", False)
    rt_badge = (
        f"<span style='color: #4CAF50; font-size: 0.7rem;'>⚡ 交易中 {contract.get('last_update', '')}</span>"
        if is_trading
        else f"<span style='color: #888; font-size: 0.7rem;'>📅 已收盤 {contract.get('last_update', '')}</span>"
    )

    vol_str = f"量 {contract['volume']:,}" if contract.get("volume") else ""
    if contract.get("bid_price") and contract.get("ask_price"):
        bid_ask = f"買 {contract['bid_price']:,.0f} / 賣 {contract['ask_price']:,.0f}"
    else:
        bid_ask = ""

    st.markdown(
        f"""<div style='background: rgba(30,30,46,0.8); border-radius: 12px; padding: 16px;
                    border-left: 4px solid {color}; border-top: 1px solid rgba(61,61,92,0.5);
                    border-right: 1px solid rgba(61,61,92,0.5); border-bottom: 1px solid rgba(61,61,92,0.5);
                    min-height: 180px;'>
            <div style='font-size: 0.8rem; color: #888;'>{emoji} {name} ({session_label})</div>
            <div style='font-size: 0.9rem; color: #aaa; margin: 2px 0;'>{symbol_id}</div>
            <div style='font-size: 1.6rem; font-weight: bold; color: {chg_color}; margin: 6px 0;'>{price:,.0f}</div>
            <div style='font-size: 0.95rem; color: {chg_color};'>{arrow} {sign}{change:,.0f} ({sign}{change_pct:.2f}%)</div>
            <div style='font-size: 0.8rem; color: #aaa; margin-top: 4px;'>{vol_str}</div>
            <div style='font-size: 0.75rem; color: #999; margin-top: 2px;'>{bid_ask}</div>
            <div style='margin-top: 6px;'>{rt_badge}</div></div>""",
        unsafe_allow_html=True,
    )


def display_indices_dashboard():
    """顯示四大指數 + 期貨指數看板"""

    # ── 即時看板區塊（使用 fragment 自動刷新）──
    refresh_sec = refresh_interval if auto_refresh else None
    run_every_val = timedelta(seconds=refresh_sec) if refresh_sec else None

    @st.fragment(run_every=run_every_val)
    def realtime_index_panel():
        """即時指數面板 — 自動定時刷新"""
        fetch_time = _now_tw().strftime("%Y-%m-%d %H:%M:%S")

        # 狀態列
        status_col1, status_col2 = st.columns([3, 1])
        with status_col1:
            if auto_refresh:
                st.markdown(
                    f"🟢 **即時模式** — 每 **{refresh_interval} 秒**自動更新 &nbsp;|&nbsp; "
                    f"📡 最後更新: **{fetch_time}**",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"⏸️ **手動模式** — 點擊左側「🔄 立即刷新」更新 &nbsp;|&nbsp; "
                    f"📡 最後抓取: **{fetch_time}**",
                    unsafe_allow_html=True,
                )
        with status_col2:
            mkt = get_market_status()
            us_dot = "🟢" if mkt["us_open"] else "🔴"
            tw_dot = "🟢" if mkt["tw_open"] else "🔴"
            night_dot = "🌙" if mkt.get("tw_night_open") else "⬛"
            st.markdown(f"{us_dot}美股 {tw_dot}台股 {night_dot}夜盤")

        st.markdown("---")

        # ══════════════════════════════════════
        # ── 🇹🇼 台股指數 ──────────────────────
        # ══════════════════════════════════════
        st.subheader("🇹🇼 台股指數")

        all_tw_idx_symbols = [v["symbol"] for v in TW_INDICES.values()]
        tw_idx_quotes = get_batch_index_quotes(all_tw_idx_symbols)

        tw_cols = st.columns(4)
        for i, (name, meta) in enumerate(TW_INDICES.items()):
            with tw_cols[i]:
                quote = tw_idx_quotes.get(meta["symbol"])
                render_index_card(name, meta, quote)

        tw_ts = []
        for meta in TW_INDICES.values():
            q = tw_idx_quotes.get(meta["symbol"])
            if q and q.get("last_update"):
                src = "⚡即時" if q.get("is_realtime") else "📅收盤"
                tw_ts.append(f"{meta['symbol']}: {q['last_update']} ({src})")
        if tw_ts:
            st.caption(" | ".join(tw_ts))

        st.markdown("<br>", unsafe_allow_html=True)

        # ── 台指期 / 台股相關 ETF ─────────────
        st.subheader("📋 台指期 / 槓桿反向 ETF")

        all_tw_fut_symbols = [v["symbol"] for v in TW_FUTURES_PROXY.values()]
        tw_fut_quotes = get_batch_index_quotes(all_tw_fut_symbols)

        tw_fcols = st.columns(4)
        for i, (name, meta) in enumerate(TW_FUTURES_PROXY.items()):
            with tw_fcols[i]:
                quote = tw_fut_quotes.get(meta["symbol"])
                render_index_card(name, meta, quote)

        tw_fts = []
        for meta in TW_FUTURES_PROXY.values():
            q = tw_fut_quotes.get(meta["symbol"])
            if q and q.get("last_update"):
                src = "⚡即時" if q.get("is_realtime") else "📅收盤"
                tw_fts.append(f"{meta['symbol']}: {q['last_update']} ({src})")
        if tw_fts:
            st.caption(" | ".join(tw_fts))

        st.markdown("---")

        # ── 台股指數 vs 台指期對照表 ──────────
        st.subheader("📊 台股指數 vs ETF 對照")

        tw_table = []
        twii_quote = tw_idx_quotes.get("^TWII")
        for fut_name, fut_meta in TW_FUTURES_PROXY.items():
            fut_quote = tw_fut_quotes.get(fut_meta["symbol"])

            idx_price = f"{twii_quote['price']:,.2f}" if twii_quote else "N/A"
            idx_chg = f"{twii_quote['change']:+,.2f} ({twii_quote['change_pct']:+.2f}%)" if twii_quote else "N/A"
            fut_price = f"{fut_quote['price']:,.2f}" if fut_quote else "N/A"
            fut_chg = f"{fut_quote['change']:+,.2f} ({fut_quote['change_pct']:+.2f}%)" if fut_quote else "N/A"

            tw_table.append({
                "名稱": f"{fut_meta['emoji']} {fut_name}",
                "現價": fut_price,
                "漲跌": fut_chg,
                "加權指數": idx_price,
                "加權漲跌": idx_chg,
            })

        st.dataframe(tw_table, use_container_width=True, hide_index=True)

        st.markdown("---")

        # ══════════════════════════════════════
        # ── � 台指期夜盤即時追蹤 ───────────────
        # ══════════════════════════════════════
        # ── 🌙 TAIFEX 期貨即時行情 ────────────
        # ══════════════════════════════════════
        taifex_status = get_taifex_session_status()

        # --- 日盤 ---
        st.subheader("🇹🇼 台指期日盤即時行情")
        if taifex_status["day_open"]:
            st.markdown(
                f"""<div style='background: linear-gradient(135deg, rgba(30,60,30,0.9), rgba(20,50,20,0.9));
                            border-radius: 10px; padding: 14px; border: 1px solid #388E3C;
                            margin-bottom: 12px;'>
                    <span style='font-size: 1.1rem;'>{taifex_status['day_status']}</span>
                </div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""<div style='background: rgba(30,30,46,0.6); border-radius: 10px; padding: 14px;
                            border: 1px solid rgba(61,61,92,0.5); margin-bottom: 12px;'>
                    <span style='font-size: 1.1rem;'>{taifex_status['day_status']}</span>
                    &nbsp;&nbsp;<span style='color: #888; font-size: 0.85rem;'>日盤交易時段: 08:45~13:45</span>
                </div>""",
                unsafe_allow_html=True,
            )

        day_contracts = get_taifex_main_contracts(session="day")
        if day_contracts:
            day_cols = st.columns(len(day_contracts))
            for i, c in enumerate(day_contracts):
                with day_cols[i]:
                    _render_taifex_card(c)
            # 時間戳
            day_ts = [f"{c['product_name']}: {c['last_update']} ({'⚡交易中' if c['is_trading'] else '📅已收盤'})" for c in day_contracts if c.get('last_update')]
            if day_ts:
                st.caption(" | ".join(day_ts))
        else:
            st.info("⏳ 日盤資料載入中（日盤收盤後可能暫無即時報價）")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- 夜盤 ---
        st.subheader("🌙 台指期夜盤即時行情")
        if taifex_status["night_open"]:
            st.markdown(
                f"""<div style='background: linear-gradient(135deg, rgba(30,30,80,0.9), rgba(20,20,60,0.9));
                            border-radius: 10px; padding: 14px; border: 1px solid #3949AB;
                            margin-bottom: 12px;'>
                    <span style='font-size: 1.1rem;'>{taifex_status['night_status']}</span>
                </div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""<div style='background: rgba(30,30,46,0.6); border-radius: 10px; padding: 14px;
                            border: 1px solid rgba(61,61,92,0.5); margin-bottom: 12px;'>
                    <span style='font-size: 1.1rem;'>{taifex_status['night_status']}</span>
                    &nbsp;&nbsp;<span style='color: #888; font-size: 0.85rem;'>夜盤交易時段: 15:00~翌日 05:00</span>
                </div>""",
                unsafe_allow_html=True,
            )

        night_contracts = get_taifex_main_contracts(session="night")
        if night_contracts:
            night_cols = st.columns(len(night_contracts))
            for i, c in enumerate(night_contracts):
                with night_cols[i]:
                    _render_taifex_card(c)
            night_ts = [f"{c['product_name']}: {c['last_update']} ({'⚡交易中' if c['is_trading'] else '📅已收盤'})" for c in night_contracts if c.get('last_update')]
            if night_ts:
                st.caption(" | ".join(night_ts))
        else:
            st.info("⏳ 夜盤資料載入中（夜盤未開盤時可能暫無即時報價）")

        # 期貨行情明細表
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**📌 TAIFEX 期貨即時報價明細**")
        all_contracts = day_contracts + night_contracts
        if all_contracts:
            detail_rows = []
            for c in all_contracts:
                chg_color = "🔺" if c["change"] > 0 else ("🔻" if c["change"] < 0 else "⬜")
                detail_rows.append({
                    "盤別": "日盤" if c["session"] == "day" else "夜盤",
                    "商品": f"{c.get('emoji','')} {c.get('product_name', c['name'])}",
                    "代碼": c["symbol_id"],
                    "成交價": f"{c['price']:,.0f}" if c["price"] else "—",
                    "漲跌": f"{chg_color} {c['change']:+,.0f} ({c['change_pct']:+.2f}%)" if c["price"] else "—",
                    "開盤": f"{c['open']:,.0f}" if c["open"] else "—",
                    "最高": f"{c['high']:,.0f}" if c["high"] else "—",
                    "最低": f"{c['low']:,.0f}" if c["low"] else "—",
                    "成交量": f"{c['volume']:,}" if c["volume"] else "—",
                    "買價": f"{c['bid_price']:,.0f}" if c["bid_price"] else "—",
                    "賣價": f"{c['ask_price']:,.0f}" if c["ask_price"] else "—",
                    "未平倉": f"{c['open_interest']:,}" if c.get("open_interest") else "—",
                })
            st.dataframe(detail_rows, use_container_width=True, hide_index=True)

        st.markdown("---")

        # ══════════════════════════════════════
        # ── �🇺🇸 美股四大指數 ─────────────────
        # ══════════════════════════════════════
        st.subheader("🇺🇸 美股四大指數")

        all_index_symbols = [v["symbol"] for v in US_INDICES.values()]
        index_quotes = get_batch_index_quotes(all_index_symbols)

        cols = st.columns(4)
        for i, (name, meta) in enumerate(US_INDICES.items()):
            with cols[i]:
                quote = index_quotes.get(meta["symbol"])
                render_index_card(name, meta, quote)

        # 顯示資料來源時間
        ts_parts = []
        for meta in US_INDICES.values():
            q = index_quotes.get(meta["symbol"])
            if q and q.get("last_update"):
                src = "⚡即時" if q.get("is_realtime") else "📅收盤"
                ts_parts.append(f"{meta['symbol']}: {q['last_update']} ({src})")
        if ts_parts:
            st.caption(" | ".join(ts_parts))

        st.markdown("<br>", unsafe_allow_html=True)

        # ── 期貨指數 ──────────────────────────
        st.subheader("📋 期貨指數（E-mini）")

        all_futures_symbols = [v["symbol"] for v in US_FUTURES.values()]
        futures_quotes = get_batch_index_quotes(all_futures_symbols)

        cols2 = st.columns(4)
        for i, (name, meta) in enumerate(US_FUTURES.items()):
            with cols2[i]:
                quote = futures_quotes.get(meta["symbol"])
                render_index_card(name, meta, quote)

        ts_parts2 = []
        for meta in US_FUTURES.values():
            q = futures_quotes.get(meta["symbol"])
            if q and q.get("last_update"):
                src = "⚡即時" if q.get("is_realtime") else "📅收盤"
                ts_parts2.append(f"{meta['symbol']}: {q['last_update']} ({src})")
        if ts_parts2:
            st.caption(" | ".join(ts_parts2))

        st.markdown("---")

        # ── 指數 vs 期貨 對照表 ───────────────
        st.subheader("📊 美股指數 vs 期貨即時對照")

        return index_quotes, futures_quotes

    result = realtime_index_panel()
    if result and isinstance(result, tuple):
        index_quotes, futures_quotes = result
    else:
        all_index_symbols = [v["symbol"] for v in US_INDICES.values()]
        all_futures_symbols = [v["symbol"] for v in US_FUTURES.values()]
        index_quotes = get_batch_index_quotes(all_index_symbols)
        futures_quotes = get_batch_index_quotes(all_futures_symbols)

    table_data = []
    for idx_name, idx_meta in US_INDICES.items():
        idx_quote = index_quotes.get(idx_meta["symbol"])
        # 找對應期貨
        fut_name = None
        fut_meta = None
        for fn, fm in US_FUTURES.items():
            if fm.get("index_ref") == idx_meta["symbol"]:
                fut_name = fn
                fut_meta = fm
                break

        fut_quote = futures_quotes.get(fut_meta["symbol"]) if fut_meta else None

        idx_price = f"{idx_quote['price']:,.2f}" if idx_quote else "N/A"
        idx_chg = f"{idx_quote['change']:+,.2f} ({idx_quote['change_pct']:+.2f}%)" if idx_quote else "N/A"
        fut_price = f"{fut_quote['price']:,.2f}" if fut_quote else "N/A"
        fut_chg = f"{fut_quote['change']:+,.2f} ({fut_quote['change_pct']:+.2f}%)" if fut_quote else "N/A"

        # 計算溢價/折價
        if idx_quote and fut_quote and idx_quote["price"] > 0:
            premium = fut_quote["price"] - idx_quote["price"]
            premium_pct = (premium / idx_quote["price"]) * 100
            premium_str = f"{premium:+,.2f} ({premium_pct:+.2f}%)"
        else:
            premium_str = "N/A"

        table_data.append({
            "指數名稱": f"{idx_meta['emoji']} {idx_name}",
            "指數現價": idx_price,
            "指數漲跌": idx_chg,
            "期貨名稱": f"{fut_name}" if fut_name else "N/A",
            "期貨現價": fut_price,
            "期貨漲跌": fut_chg,
            "期貨溢/折價": premium_str,
        })

    st.dataframe(table_data, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── 走勢比較圖 ────────────────────────
    st.subheader("📈 走勢比較圖")

    chart_tab1, chart_tab2, chart_tab3, chart_tab4, chart_tab5 = st.tabs(
        ["🇹🇼 台股指數走勢", "🇹🇼 台指期/ETF走勢", "🇺🇸 四大指數走勢", "🇺🇸 期貨指數走勢", "🔀 指數 vs 期貨"]
    )

    idx_period_options = {
        "1週": "5d",
        "1個月": "1mo",
        "3個月": "3mo",
        "6個月": "6mo",
        "1年": "1y",
        "年初至今": "ytd",
    }
    idx_selected = st.select_slider(
        "📅 指數走勢時間區間",
        options=list(idx_period_options.keys()),
        value="3個月",
        key="idx_period",
    )
    idx_period = idx_period_options[idx_selected]

    with chart_tab1:
        with st.spinner("載入台股指數走勢..."):
            tw_idx_hist = {}
            for name, meta in TW_INDICES.items():
                hist = get_stock_history(meta["symbol"], period=idx_period)
                if hist is not None:
                    tw_idx_hist[meta["symbol"]] = hist

        if tw_idx_hist:
            fig = create_indices_overview_chart(tw_idx_hist, title=f"台股指數 - {idx_selected}走勢比較")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ 無法取得台股指數走勢資料")

    with chart_tab2:
        with st.spinner("載入台指期/ETF走勢..."):
            tw_fut_hist = {}
            for name, meta in TW_FUTURES_PROXY.items():
                hist = get_stock_history(meta["symbol"], period=idx_period)
                if hist is not None:
                    tw_fut_hist[meta["symbol"]] = hist

        if tw_fut_hist:
            fig = create_indices_overview_chart(tw_fut_hist, title=f"台指期 / 槓桿反向ETF - {idx_selected}走勢比較")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ 無法取得台指期走勢資料")

    with chart_tab3:
        with st.spinner("載入四大指數走勢..."):
            idx_hist = {}
            for name, meta in US_INDICES.items():
                hist = get_stock_history(meta["symbol"], period=idx_period)
                if hist is not None:
                    idx_hist[meta["symbol"]] = hist

        if idx_hist:
            fig = create_indices_overview_chart(idx_hist, title=f"美股四大指數 - {idx_selected}走勢比較")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ 無法取得指數走勢資料")

    with chart_tab4:
        with st.spinner("載入期貨指數走勢..."):
            fut_hist = {}
            for name, meta in US_FUTURES.items():
                hist = get_stock_history(meta["symbol"], period=idx_period)
                if hist is not None:
                    fut_hist[meta["symbol"]] = hist

        if fut_hist:
            fig = create_indices_overview_chart(fut_hist, title=f"期貨指數 (E-mini) - {idx_selected}走勢比較")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ 無法取得期貨走勢資料")

    with chart_tab5:
        compare_idx = st.selectbox(
            "選擇指數",
            list(US_INDICES.keys()),
            key="idx_vs_fut_select",
        )
        selected_idx_meta = US_INDICES[compare_idx]
        # 找對應的期貨
        corresponding_fut = None
        for fn, fm in US_FUTURES.items():
            if fm.get("index_ref") == selected_idx_meta["symbol"]:
                corresponding_fut = fm
                break

        if corresponding_fut:
            with st.spinner(f"載入 {compare_idx} vs 期貨走勢..."):
                compare_data = {}
                h1 = get_stock_history(selected_idx_meta["symbol"], period=idx_period)
                h2 = get_stock_history(corresponding_fut["symbol"], period=idx_period)
                if h1 is not None:
                    compare_data[selected_idx_meta["symbol"]] = h1
                if h2 is not None:
                    compare_data[corresponding_fut["symbol"]] = h2

            if compare_data:
                fig = create_indices_overview_chart(
                    compare_data,
                    title=f"{compare_idx} vs 期貨 - {idx_selected}走勢比較",
                )
                st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ── 個別指數詳細查詢 ─────────────────
    st.subheader("🔎 查看個別指數/期貨詳情")

    all_options = {}
    for name, meta in TW_INDICES.items():
        all_options[f"🇹🇼 {name} ({meta['symbol']})"] = meta["symbol"]
    for name, meta in TW_FUTURES_PROXY.items():
        all_options[f"🇹🇼 {name} ({meta['symbol']})"] = meta["symbol"]
    for name, meta in US_INDICES.items():
        all_options[f"🇺🇸 {name} ({meta['symbol']})"] = meta["symbol"]
    for name, meta in US_FUTURES.items():
        all_options[f"🇺🇸 {name} ({meta['symbol']})"] = meta["symbol"]

    detail_select = st.selectbox(
        "選擇指數或期貨",
        list(all_options.keys()),
        key="idx_detail_select",
    )

    if st.button("📊 查看詳細走勢", key="idx_detail_btn", use_container_width=True):
        detail_symbol = all_options[detail_select]
        with st.spinner(f"正在查詢 {detail_symbol}..."):
            detail_info = get_stock_info(detail_symbol)
            detail_hist = get_stock_history(detail_symbol, period=idx_period)

        if detail_info:
            display_stock_info(detail_info, detail_hist)
        else:
            st.error("❌ 無法取得資料")


def display_stock_info(info: dict, history):
    """顯示股票詳細資訊"""
    if not info:
        st.error("❌ 查無此股票資料，請確認代碼是否正確")
        return

    # 股票標題區
    name = info["name"]
    symbol = info["symbol"]
    price = info["price"]
    change = info["change"]
    change_pct = info["change_pct"]

    # 判斷漲跌
    if change >= 0:
        arrow = "🔺"
        color = "#EF5350"
        sign = "+"
    else:
        arrow = "🔻"
        color = "#26A69A"
        sign = ""

    # 如果是台股，顯示中文名
    code_only = symbol.replace(".TW", "").replace(".TWO", "")
    display_name = tw_code_to_name.get(code_only, name)

    st.markdown(
        f"""
        <div style='margin-bottom: 20px;'>
            <h2 style='margin: 0;'>{display_name} <span style='color: #888; font-size: 1rem;'>({symbol})</span></h2>
            <div style='display: flex; align-items: baseline; gap: 12px; margin-top: 4px;'>
                <span class='big-price' style='color: {color};'>{price}</span>
                <span style='color: {color}; font-size: 1.3rem;'>
                    {arrow} {sign}{change} ({sign}{change_pct}%)
                </span>
            </div>
            <span style='color: #888; font-size: 0.85rem;'>
                幣別: {info['currency']} | 交易所: {info['exchange']}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 關鍵指標卡片
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.metric("開盤", format_number(info["open"]))
    with col2:
        st.metric("最高", format_number(info["high"]))
    with col3:
        st.metric("最低", format_number(info["low"]))
    with col4:
        st.metric("前收", format_number(info["prev_close"]))
    with col5:
        st.metric("成交量", format_volume(info["volume"]))
    with col6:
        market_cap = info.get("market_cap")
        st.metric("市值", format_number(market_cap, is_currency=True) if market_cap else "N/A")

    st.markdown("---")

    # 圖表
    if history is not None and not history.empty:
        if chart_type == "K線圖":
            fig = create_candlestick_chart(
                history,
                title=f"{display_name} ({symbol}) - {selected_period}走勢",
            )
        else:
            fig = create_line_chart(
                history,
                title=f"{display_name} ({symbol}) - {selected_period}走勢",
            )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("⚠️ 無法取得歷史資料")

    st.markdown("---")

    # 詳細資訊
    st.subheader("📋 詳細資訊")

    detail_col1, detail_col2, detail_col3 = st.columns(3)

    with detail_col1:
        st.markdown("**📊 價格指標**")
        st.write(f"- 本益比 (P/E): {format_number(info.get('pe_ratio'))}")
        dividend = info.get("dividend_yield")
        if dividend:
            st.write(f"- 殖利率: {dividend * 100:.2f}%")
        else:
            st.write("- 殖利率: N/A")
        st.write(f"- 52週最高: {format_number(info.get('52w_high'))}")
        st.write(f"- 52週最低: {format_number(info.get('52w_low'))}")

    with detail_col2:
        st.markdown("**🏢 公司資訊**")
        st.write(f"- 產業: {info.get('sector', 'N/A')}")
        st.write(f"- 行業: {info.get('industry', 'N/A')}")
        st.write(f"- 交易所: {info.get('exchange', 'N/A')}")

    with detail_col3:
        st.markdown("**📈 技術指標**")
        if history is not None and len(history) > 0:
            close = history["Close"]
            high_val = close.max()
            low_val = close.min()
            avg_val = close.mean()
            st.write(f"- 區間最高: {high_val:.2f}")
            st.write(f"- 區間最低: {low_val:.2f}")
            st.write(f"- 區間均價: {avg_val:.2f}")

            if len(close) > 20:
                ma20 = close.rolling(20).mean().iloc[-1]
                st.write(f"- MA20: {ma20:.2f}")


def display_comparison(symbols_str: str, market: str, period: str):
    """顯示多檔股票比較"""
    symbols = [s.strip() for s in symbols_str.split(",") if s.strip()]

    if len(symbols) < 2:
        st.warning("⚠️ 請至少輸入 2 個股票代碼進行比較")
        return

    if len(symbols) > 8:
        st.warning("⚠️ 最多支援 8 檔股票比較")
        symbols = symbols[:8]

    data_dict = {}
    info_list = []

    with st.spinner("正在載入資料..."):
        for code in symbols:
            ticker_sym = get_ticker_symbol(code, market)
            hist = get_stock_history(ticker_sym, period=period)
            info = get_stock_info(ticker_sym)
            if hist is not None:
                data_dict[ticker_sym] = hist
            if info:
                info_list.append(info)

    if not data_dict:
        st.error("❌ 無法取得任何股票資料")
        return

    # 比較圖表
    fig = create_comparison_chart(data_dict, title=f"股票比較 - {selected_period}")
    st.plotly_chart(fig, use_container_width=True)

    # 比較表格
    if info_list:
        st.subheader("📊 比較數據")
        compare_data = []
        for info in info_list:
            code_only = info["symbol"].replace(".TW", "").replace(".TWO", "")
            display_name = tw_code_to_name.get(code_only, info["name"])
            compare_data.append(
                {
                    "股票": f"{display_name} ({info['symbol']})",
                    "現價": info["price"],
                    "漲跌": info["change"],
                    "漲跌幅%": info["change_pct"],
                    "成交量": format_volume(info["volume"]),
                    "本益比": format_number(info.get("pe_ratio")),
                    "市值": format_number(info.get("market_cap"), is_currency=True),
                }
            )
        st.dataframe(
            compare_data,
            use_container_width=True,
            hide_index=True,
        )


# ─── 主要邏輯 ────────────────────────────────────────

if page == "🏠 指數總覽":
    # ═══ 指數總覽頁面 ═══
    display_indices_dashboard()

elif page == "🔍 個股查詢":
    # ═══ 個股查詢頁面 ═══
    if compare_clicked and compare_input:
        display_comparison(compare_input, market, period)

    elif search_clicked and stock_code:
        ticker_symbol = get_ticker_symbol(stock_code, market)

        with st.spinner(f"🔄 正在查詢 {ticker_symbol}..."):
            info = get_stock_info(ticker_symbol)
            history = get_stock_history(ticker_symbol, period=period)

        display_stock_info(info, history)

    elif not stock_code:
        # 預設顯示歡迎頁面
        st.markdown(
            """
            <div style='text-align: center; padding: 60px 20px;'>
                <h2>👋 歡迎使用股票查詢系統</h2>
                <p style='color: #888; font-size: 1.1rem; max-width: 600px; margin: 0 auto;'>
                    請在左側選擇市場，輸入股票代碼後按「查詢股票」開始使用
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 顯示熱門股票快速入口
        st.markdown("---")

        tab1, tab2 = st.tabs(["🇹🇼 台股熱門", "🇺🇸 美股熱門"])

        with tab1:
            tw_popular = ["2330", "2317", "2454", "2308", "0050", "00878"]
            cols = st.columns(len(tw_popular))
            for i, code in enumerate(tw_popular):
                with cols[i]:
                    name = tw_code_to_name.get(code, code)
                    st.markdown(
                        f"""
                        <div style='text-align: center; padding: 12px;
                                    background: rgba(30,30,46,0.6);
                                    border-radius: 10px; border: 1px solid rgba(61,61,92,0.5);'>
                            <div style='font-size: 0.85rem; color: #888;'>{code}.TW</div>
                            <div style='font-size: 1.1rem; font-weight: bold;'>{name}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        with tab2:
            us_popular = ["AAPL", "MSFT", "NVDA", "GOOGL", "TSLA", "META"]
            us_names = {
                "AAPL": "Apple",
                "MSFT": "Microsoft",
                "NVDA": "NVIDIA",
                "GOOGL": "Google",
                "TSLA": "Tesla",
                "META": "Meta",
            }
            cols = st.columns(len(us_popular))
            for i, code in enumerate(us_popular):
                with cols[i]:
                    st.markdown(
                        f"""
                        <div style='text-align: center; padding: 12px;
                                    background: rgba(30,30,46,0.6);
                                    border-radius: 10px; border: 1px solid rgba(61,61,92,0.5);'>
                            <div style='font-size: 0.85rem; color: #888;'>{code}</div>
                            <div style='font-size: 1.1rem; font-weight: bold;'>{us_names.get(code, code)}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

# ─── 頁尾 ────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align: center; color: #666; font-size: 0.8rem;'>
        📈 台股美股查詢系統 v1.3 | 資料來源: Yahoo Finance + TAIFEX | 
        最後更新: {_now_tw().strftime('%Y-%m-%d %H:%M')}
        <br>⚠️ 本系統僅供參考，投資有風險，請自行判斷
    </div>
    """,
    unsafe_allow_html=True,
)
