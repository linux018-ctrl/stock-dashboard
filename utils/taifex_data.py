"""
台灣期貨交易所 (TAIFEX) 即時行情模組
直接從期交所 MIS API 抓取即時期貨報價
支援一般盤 (日盤) 與盤後盤 (夜盤/電子盤)
"""

import requests
from datetime import datetime
from typing import Optional
import pytz


TAIFEX_API_URL = "https://mis.taifex.com.tw/futures/api/getQuoteList"

# 期貨商品代碼對照
TAIFEX_PRODUCTS = {
    "台指期": {"CID": "TXF", "emoji": "🇹🇼", "color": "#E53935"},
    "小台指": {"CID": "MXF", "emoji": "🔸", "color": "#FF6F00"},
    "電子期": {"CID": "EXF", "emoji": "💻", "color": "#1E88E5"},
    "金融期": {"CID": "FXF", "emoji": "🏦", "color": "#43A047"},
    "台灣50期": {"CID": "T5F", "emoji": "📦", "color": "#7B1FA2"},
    "非金電期": {"CID": "XIF", "emoji": "🏭", "color": "#FF9800"},
}


def _fetch_taifex_quotes(market_type: str = "0", cid: str = "") -> list[dict]:
    """
    從 TAIFEX MIS API 取得報價
    market_type: "0" = 一般盤(日盤), "1" = 盤後盤(夜盤)
    cid: 商品代碼，空字串=全部
    """
    try:
        body = {
            "MarketType": market_type,
            "SymbolType": "F",
            "KindID": "1",
            "CID": cid,
            "ExpireMonth": "",
            "RowSize": "全部",
            "PageNo": "",
            "SortColumn": "",
            "AscDesc": "A",
        }
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        r = requests.post(TAIFEX_API_URL, json=body, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("RtData", {}).get("QuoteList", [])
    except Exception as e:
        print(f"TAIFEX API error: {e}")
        return []


def _parse_quote(raw: dict) -> dict:
    """解析單筆 TAIFEX 報價為標準格式"""
    def safe_float(val, default=0.0):
        try:
            return float(val) if val and val.strip() else default
        except (ValueError, AttributeError):
            return default

    def safe_int(val, default=0):
        try:
            return int(val) if val and val.strip() else default
        except (ValueError, AttributeError):
            return default

    price = safe_float(raw.get("CLastPrice"))
    ref_price = safe_float(raw.get("CRefPrice"))
    diff = safe_float(raw.get("CDiff"))
    diff_rate = safe_float(raw.get("CDiffRate"))
    open_price = safe_float(raw.get("COpenPrice"))
    high_price = safe_float(raw.get("CHighPrice"))
    low_price = safe_float(raw.get("CLowPrice"))
    volume = safe_int(raw.get("CTotalVolume"))
    bid_price = safe_float(raw.get("CBidPrice1"))
    ask_price = safe_float(raw.get("CAskPrice1"))
    bid_size = safe_int(raw.get("CBidSize1"))
    ask_size = safe_int(raw.get("CAskSize1"))
    settle_price = safe_float(raw.get("SettlementPrice"))
    oi = safe_int(raw.get("OpenInterest"))

    # 解析時間
    cdate = raw.get("CDate", "")
    ctime = raw.get("CTime", "")
    if cdate and ctime and len(ctime) >= 6:
        time_str = f"{cdate[:4]}-{cdate[4:6]}-{cdate[6:8]} {ctime[:2]}:{ctime[2:4]}:{ctime[4:6]}"
    elif cdate:
        time_str = f"{cdate[:4]}-{cdate[4:6]}-{cdate[6:8]}"
    else:
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    status = raw.get("Status", "")

    return {
        "symbol_id": raw.get("SymbolID", ""),
        "name": raw.get("DispCName", ""),
        "name_en": raw.get("DispEName", ""),
        "price": price,
        "ref_price": ref_price,
        "change": diff,
        "change_pct": diff_rate,
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "volume": volume,
        "bid_price": bid_price,
        "ask_price": ask_price,
        "bid_size": bid_size,
        "ask_size": ask_size,
        "settle_price": settle_price,
        "open_interest": oi,
        "last_update": time_str,
        "status": status,
        "is_trading": status not in ("TC", ""),  # TC = Trading Closed
    }


def get_taifex_futures(session: str = "day", products: list[str] = None) -> dict[str, list[dict]]:
    """
    取得 TAIFEX 期貨即時報價

    session: "day" = 一般盤(日盤), "night" = 盤後盤(夜盤/電子盤), "both" = 兩者
    products: 指定商品代碼列表，如 ["TXF", "MXF"]，None = 全部

    返回: {商品代碼: [近月, 次月, ...]} 只回傳期貨合約（排除現貨）
    """
    market_types = []
    if session in ("day", "both"):
        market_types.append(("0", "day"))
    if session in ("night", "both"):
        market_types.append(("1", "night"))

    result = {}
    for mt, label in market_types:
        quotes = _fetch_taifex_quotes(market_type=mt)
        for q in quotes:
            sid = q.get("SymbolID", "")
            # 跳過現貨 (SymbolID 以 -S 或 -P 結尾的是現貨)
            if sid.endswith("-S") or sid.endswith("-P"):
                continue

            parsed = _parse_quote(q)
            parsed["session"] = label

            # 根據 CID 分組
            cid_prefix = ""
            for prod_name, prod_info in TAIFEX_PRODUCTS.items():
                if sid.startswith(prod_info["CID"]):
                    cid_prefix = prod_info["CID"]
                    break

            if not cid_prefix:
                # 嘗試從 SymbolID 提取前綴
                cid_prefix = sid.split("D")[0] if "D" in sid else sid[:3]

            key = f"{cid_prefix}_{label}"
            if products and cid_prefix not in products:
                continue

            if key not in result:
                result[key] = []
            result[key].append(parsed)

    return result


def get_taifex_main_contracts(session: str = "day") -> list[dict]:
    """
    取得主要期貨近月合約報價（最常用）
    返回: [台指期近月, 小台指近月, 電子期近月, 金融期近月]
    """
    market_type = "1" if session == "night" else "0"
    main_cids = ["TXF", "MXF", "EXF", "FXF"]

    results = []
    for cid in main_cids:
        quotes = _fetch_taifex_quotes(market_type=market_type, cid=cid)
        # 找到近月合約（第一筆非現貨的就是近月）
        for q in quotes:
            sid = q.get("SymbolID", "")
            if sid.endswith("-S") or sid.endswith("-P") or sid.endswith("-F") == False:
                if "-S" in sid or "-P" in sid:
                    continue
            parsed = _parse_quote(q)
            parsed["session"] = session
            parsed["cid"] = cid

            # 只取近月（有成交量的第一筆）
            if parsed["price"] > 0:
                # 加上 emoji 和 color
                for prod_name, prod_info in TAIFEX_PRODUCTS.items():
                    if prod_info["CID"] == cid:
                        parsed["emoji"] = prod_info["emoji"]
                        parsed["color"] = prod_info["color"]
                        parsed["product_name"] = prod_name
                        break
                results.append(parsed)
                break

    return results


def get_taifex_session_status() -> dict:
    """取得期交所盤別狀態"""
    tw = pytz.timezone("Asia/Taipei")
    now = datetime.now(tw)
    hour = now.hour
    minute = now.minute
    weekday = now.weekday()

    if weekday >= 5:
        return {
            "day_open": False,
            "night_open": False,
            "day_status": "🔴 休市（週末）",
            "night_status": "🔴 休市（週末）",
            "current_session": "closed",
        }

    # 日盤: 8:45 ~ 13:45
    day_open = (hour == 8 and minute >= 45) or (9 <= hour < 13) or (hour == 13 and minute <= 45)
    # 夜盤: 15:00 ~ 隔日 05:00
    night_open = (15 <= hour <= 23) or (0 <= hour < 5)

    if day_open:
        day_status = "🟢 日盤交易中 (08:45~13:45)"
        current = "day"
    else:
        day_status = "🔴 日盤已收"
        current = "closed"

    if night_open:
        night_status = "🌙 夜盤交易中 (15:00~05:00)"
        current = "night"
    else:
        night_status = "🔴 夜盤已收"

    return {
        "day_open": day_open,
        "night_open": night_open,
        "day_status": day_status,
        "night_status": night_status,
        "current_session": current,
        "time": now.strftime("%Y-%m-%d %H:%M:%S"),
    }
