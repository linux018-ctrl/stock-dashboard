"""
股票資料模組 - 封裝 yfinance 查詢邏輯
支援台股 (.TW / .TWO) 和美股查詢
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import pytz


def get_ticker_symbol(code: str, market: str) -> str:
    """
    根據市場類型組合完整的 ticker symbol
    台股: 加上 .TW 後綴 (上市) 或 .TWO (上櫃)
    美股: 直接使用代碼
    """
    code = code.strip().upper()
    if market == "台股 (TWSE)":
        if not code.endswith(".TW") and not code.endswith(".TWO"):
            return f"{code}.TW"
    return code


def get_stock_info(ticker_symbol: str) -> Optional[dict]:
    """
    取得股票基本資訊
    返回: 包含名稱、價格、漲跌幅等資訊的 dict
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info

        if not info or "regularMarketPrice" not in info:
            # 嘗試從歷史資料取得
            hist = ticker.history(period="5d")
            if hist.empty:
                return None

            last_close = hist["Close"].iloc[-1]
            prev_close = hist["Close"].iloc[-2] if len(hist) > 1 else last_close
            change = last_close - prev_close
            change_pct = (change / prev_close) * 100 if prev_close != 0 else 0

            return {
                "symbol": ticker_symbol,
                "name": info.get("shortName", info.get("longName", ticker_symbol)),
                "price": round(last_close, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "prev_close": round(prev_close, 2),
                "open": round(hist["Open"].iloc[-1], 2) if "Open" in hist else None,
                "high": round(hist["High"].iloc[-1], 2) if "High" in hist else None,
                "low": round(hist["Low"].iloc[-1], 2) if "Low" in hist else None,
                "volume": int(hist["Volume"].iloc[-1]) if "Volume" in hist else None,
                "currency": info.get("currency", "N/A"),
                "market_cap": info.get("marketCap", None),
                "pe_ratio": info.get("trailingPE", None),
                "dividend_yield": info.get("dividendYield", None),
                "52w_high": info.get("fiftyTwoWeekHigh", None),
                "52w_low": info.get("fiftyTwoWeekLow", None),
                "sector": info.get("sector", "N/A"),
                "industry": info.get("industry", "N/A"),
                "exchange": info.get("exchange", "N/A"),
            }

        # 正常情況從 info 取得資料
        price = info.get("regularMarketPrice", info.get("currentPrice", 0))
        prev_close = info.get("regularMarketPreviousClose", info.get("previousClose", 0))
        change = price - prev_close if price and prev_close else 0
        change_pct = (change / prev_close * 100) if prev_close else 0

        return {
            "symbol": ticker_symbol,
            "name": info.get("shortName", info.get("longName", ticker_symbol)),
            "price": round(price, 2) if price else 0,
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "prev_close": round(prev_close, 2) if prev_close else 0,
            "open": info.get("regularMarketOpen", info.get("open", None)),
            "high": info.get("regularMarketDayHigh", info.get("dayHigh", None)),
            "low": info.get("regularMarketDayLow", info.get("dayLow", None)),
            "volume": info.get("regularMarketVolume", info.get("volume", None)),
            "currency": info.get("currency", "N/A"),
            "market_cap": info.get("marketCap", None),
            "pe_ratio": info.get("trailingPE", None),
            "dividend_yield": info.get("dividendYield", None),
            "52w_high": info.get("fiftyTwoWeekHigh", None),
            "52w_low": info.get("fiftyTwoWeekLow", None),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "exchange": info.get("exchange", "N/A"),
        }

    except Exception as e:
        print(f"Error fetching stock info for {ticker_symbol}: {e}")
        return None


def get_stock_history(
    ticker_symbol: str,
    period: str = "1y",
    interval: str = "1d",
) -> Optional[pd.DataFrame]:
    """
    取得股票歷史資料
    
    period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
    interval: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period=period, interval=interval)

        if hist.empty:
            return None

        hist.index = hist.index.tz_localize(None) if hist.index.tz else hist.index
        return hist

    except Exception as e:
        print(f"Error fetching history for {ticker_symbol}: {e}")
        return None


def get_multiple_stocks_info(symbols: list[str]) -> list[dict]:
    """
    批次取得多檔股票資訊
    """
    results = []
    for symbol in symbols:
        info = get_stock_info(symbol)
        if info:
            results.append(info)
    return results


def format_number(num: Optional[float], is_currency: bool = False) -> str:
    """格式化數字顯示"""
    if num is None:
        return "N/A"
    if is_currency:
        if abs(num) >= 1e12:
            return f"{num/1e12:.2f}兆"
        elif abs(num) >= 1e8:
            return f"{num/1e8:.2f}億"
        elif abs(num) >= 1e4:
            return f"{num/1e4:.2f}萬"
        return f"{num:,.2f}"
    return f"{num:,.2f}"


def is_us_market_open() -> bool:
    """判斷美股是否在開盤時間（含盤前盤後延伸時段）"""
    et = pytz.timezone("US/Eastern")
    now_et = datetime.now(et)
    weekday = now_et.weekday()  # 0=Monday
    hour = now_et.hour
    minute = now_et.minute

    # 週末休市
    if weekday >= 5:
        return False

    # 盤前 4:00 AM ~ 盤後 8:00 PM ET（涵蓋期貨幾乎全天交易）
    if 4 <= hour < 20:
        return True
    return False


def is_us_futures_open() -> bool:
    """判斷美股期貨是否在交易時間（幾乎 24 小時）
    交易時段: 週日 18:00 ET ~ 週五 17:00 ET
    每日維護: 17:00~18:00 ET (Mon-Fri)
    """
    et = pytz.timezone("US/Eastern")
    now_et = datetime.now(et)
    weekday = now_et.weekday()  # 0=Mon
    hour = now_et.hour

    # 週六全天休市
    if weekday == 5:
        return False
    # 週日 18:00 前休市
    if weekday == 6 and hour < 18:
        return False
    # 週一~五 每日 17:00~18:00 維護
    if weekday < 5 and hour == 17:
        return False
    # 週五 17:00 後休市
    if weekday == 4 and hour >= 17:
        return False
    return True


def is_tw_market_open() -> bool:
    """判斷台股是否在開盤時間"""
    tw = pytz.timezone("Asia/Taipei")
    now_tw = datetime.now(tw)
    weekday = now_tw.weekday()
    hour = now_tw.hour
    minute = now_tw.minute

    if weekday >= 5:
        return False
    # 台股 9:00 ~ 13:30
    if hour == 9 or (hour >= 10 and hour < 13) or (hour == 13 and minute <= 30):
        return True
    return False


def get_market_status() -> dict:
    """取得各市場開盤狀態"""
    et = pytz.timezone("US/Eastern")
    tw = pytz.timezone("Asia/Taipei")
    now_et = datetime.now(et)
    now_tw = datetime.now(tw)

    us_open = is_us_market_open()
    tw_open = is_tw_market_open()

    # 判斷美股詳細狀態
    hour_et = now_et.hour
    if now_et.weekday() >= 5:
        us_status = "🔴 休市（週末）"
    elif 4 <= hour_et < 9 or (hour_et == 9 and now_et.minute < 30):
        us_status = "🟡 盤前交易中"
    elif (hour_et == 9 and now_et.minute >= 30) or (9 < hour_et < 16):
        us_status = "🟢 正常交易中"
    elif 16 <= hour_et < 20:
        us_status = "🟡 盤後交易中"
    else:
        us_status = "🔴 已收盤"

    if now_tw.weekday() >= 5:
        tw_status = "🔴 休市（週末）"
    elif tw_open:
        tw_status = "🟢 正常交易中"
    else:
        tw_status = "🔴 已收盤"

    # 台指期夜盤狀態: 15:00~翻日05:00 台灣時間
    tw_hour = now_tw.hour
    tw_min = now_tw.minute
    if now_tw.weekday() >= 5:
        tw_night_open = False
        tw_night_status = "🔴 休市（週末）"
    elif 15 <= tw_hour < 24 or 0 <= tw_hour < 5:
        tw_night_open = True
        tw_night_status = "🌙 夜盤交易中"
    elif tw_hour == 5 and tw_min == 0:
        tw_night_open = True
        tw_night_status = "🌙 夜盤交易中"
    else:
        tw_night_open = False
        tw_night_status = "🔴 夜盤已收"

    return {
        "us_open": us_open,
        "tw_open": tw_open,
        "tw_night_open": tw_night_open,
        "us_status": us_status,
        "tw_status": tw_status,
        "tw_night_status": tw_night_status,
        "us_time": now_et.strftime("%Y-%m-%d %H:%M:%S ET"),
        "tw_time": now_tw.strftime("%Y-%m-%d %H:%M:%S"),
        "fetch_time": datetime.now(pytz.timezone("Asia/Taipei")).strftime("%Y-%m-%d %H:%M:%S"),
    }


def get_index_quote(ticker_symbol: str) -> Optional[dict]:
    """
    取得指數/期貨的即時報價
    盤中使用 1 分鐘線取得最新價格，收盤後使用日線
    """
    try:
        ticker = yf.Ticker(ticker_symbol)

        # 判斷是否盤中 — 盤中用分鐘線取最新價
        is_tw_ticker = ticker_symbol.endswith(".TW") or ticker_symbol.endswith(".TWO") or ticker_symbol == "^TWII"
        is_futures = ticker_symbol.endswith("=F")
        if is_tw_ticker:
            market_open = is_tw_market_open()
        elif is_futures:
            market_open = is_us_futures_open()
        else:
            market_open = is_us_market_open()

        if market_open:
            # 盤中：用 1 分鐘間距取最近 1 天資料
            hist_intraday = ticker.history(period="1d", interval="1m")
            hist_daily = ticker.history(period="5d", interval="1d")

            if hist_intraday is not None and not hist_intraday.empty:
                latest_price = float(hist_intraday["Close"].iloc[-1])
                latest_high = float(hist_intraday["High"].max())
                latest_low = float(hist_intraday["Low"].min())
                latest_open = float(hist_intraday["Open"].iloc[0])
                latest_volume = int(hist_intraday["Volume"].sum()) if "Volume" in hist_intraday else None
                last_update = hist_intraday.index[-1]

                # 前一日收盤從日線取得
                if hist_daily is not None and len(hist_daily) >= 2:
                    prev_close = float(hist_daily["Close"].iloc[-2])
                else:
                    prev_close = latest_price

                change = latest_price - prev_close
                change_pct = (change / prev_close) * 100 if prev_close != 0 else 0

                # sparkline 用分鐘線最近的數據點（每 5 分鐘取樣）
                sparkline_raw = hist_intraday["Close"].tolist()
                step = max(1, len(sparkline_raw) // 50)
                sparkline_data = sparkline_raw[::step]

                # 格式化時間戳
                if hasattr(last_update, 'tz') and last_update.tz:
                    ts_str = last_update.strftime("%H:%M:%S %Z")
                else:
                    ts_str = last_update.strftime("%H:%M:%S")

                return {
                    "symbol": ticker_symbol,
                    "price": round(latest_price, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "prev_close": round(prev_close, 2),
                    "open": round(latest_open, 2),
                    "high": round(latest_high, 2),
                    "low": round(latest_low, 2),
                    "volume": latest_volume,
                    "sparkline": sparkline_data,
                    "is_realtime": True,
                    "last_update": ts_str,
                    "data_source": "1min intraday",
                }

        # 收盤後 or 抓不到分鐘線：用日線
        hist = ticker.history(period="5d", interval="1d")

        if hist.empty:
            return None

        last_close = float(hist["Close"].iloc[-1])
        prev_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else last_close
        change = last_close - prev_close
        change_pct = (change / prev_close) * 100 if prev_close != 0 else 0

        sparkline_data = hist["Close"].tolist()

        last_date = hist.index[-1]
        if hasattr(last_date, 'strftime'):
            ts_str = last_date.strftime("%Y-%m-%d")
        else:
            ts_str = str(last_date)

        return {
            "symbol": ticker_symbol,
            "price": round(last_close, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "prev_close": round(prev_close, 2),
            "open": round(float(hist["Open"].iloc[-1]), 2),
            "high": round(float(hist["High"].iloc[-1]), 2),
            "low": round(float(hist["Low"].iloc[-1]), 2),
            "volume": int(hist["Volume"].iloc[-1]) if hist["Volume"].iloc[-1] > 0 else None,
            "sparkline": sparkline_data,
            "is_realtime": False,
            "last_update": ts_str,
            "data_source": "daily close",
        }
    except Exception as e:
        print(f"Error fetching index quote for {ticker_symbol}: {e}")
        return None


def get_batch_index_quotes(symbols: list[str]) -> dict[str, Optional[dict]]:
    """
    批次取得多個指數/期貨報價
    返回 {symbol: quote_dict}
    """
    results = {}
    for symbol in symbols:
        results[symbol] = get_index_quote(symbol)
    return results


def format_volume(vol: Optional[int]) -> str:
    """格式化成交量顯示"""
    if vol is None:
        return "N/A"
    if vol >= 1e8:
        return f"{vol/1e8:.2f}億"
    elif vol >= 1e4:
        return f"{vol/1e4:.0f}萬"
    return f"{vol:,}"
