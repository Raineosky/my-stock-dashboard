import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 1. 頁面配置
st.set_page_config(page_title="台股 AI 診斷站", layout="wide", initial_sidebar_state="collapsed")

# 2. 視覺美化：強化高對比度與診斷框
st.markdown("""
    <style>
    .stApp { background-color: #0f172a; }
    [data-testid="stExpander"] { background-color: #1e293b; border-radius: 12px; margin-bottom: 10px; border: 1px solid #334155; }
    .diag-card { background: #334155; padding: 12px; border-radius: 8px; margin: 5px 0; border-left: 4px solid #475569; }
    .score-item { display: flex; justify-content: space-between; font-size: 0.9rem; color: #cbd5e1; padding: 2px 0; }
    .score-plus { color: #f87171; font-weight: bold; } /* 紅色代表多頭加分 */
    .score-minus { color: #4ade80; font-weight: bold; } /* 綠色代表空頭扣分 */
    h1, h3 { color: #38bdf8 !important; }
    </style>
    """, unsafe_allow_html=True)

# 3. 數據與指標邏輯 (TTL 1小時)
@st.cache_data(ttl=3600)
def get_analysis(symbol):
    s = f"{symbol.strip().upper()}.TW"
    h = yf.Ticker(s).history(period="2mo")
    if h.empty:
        s = f"{symbol.strip().upper()}.TWO"
        h = yf.Ticker(s).history(period="2mo")
    if not h.empty and len(h) >= 20:
        h['MA5'] = h['Close'].rolling(5).mean()
        h['MA20'] = h['Close'].rolling(20).mean()
        h['VMA5'] = h['Volume'].rolling(5).mean()
        delta = h['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        h['RSI'] = 100 - (100 / (1 + gain / loss))
        return h
    return pd.DataFrame()

st.title("📈 台股 AI 智慧監測站")
st.caption(f"自動結算：每日 16:00 | 診斷時間：{datetime.now().strftime('%H:%M')}")

stock_pool = {
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2308": "台達電",
    "3231": "緯創", "2382": "廣達", "2881": "富邦金", "2882": "國泰金",
    "2603": "長榮", "1519": "華城", "2002": "中鋼", "2409": "友達"
}

with st.spinner("AI 正在拆解指標權重..."):
    results = []
    for code, name in stock_pool.items():
        hist = get_analysis(code)
        if not hist.empty:
            c, p = hist.iloc[-1], hist.iloc[-2]
            
            # --- AI 評分與拆解邏輯 ---
            score = 50
            details = [("初始基礎分", 50, "neutral")]
            
            # MA5 判定
            if c['Close'] > c['MA5']:
                score += 10
                details.append(("短期(MA5) 站上均線", "+10", "plus"))
            else:
                details.append(("短期(MA5) 低於均線", "0", "neutral"))
                
            # MA20 判定
            if c['Close'] > c['MA20']:
                score += 15
                details.append(("中期(MA20) 趨勢偏多", "+15", "plus"))
            else:
                details.append(("中期(MA20) 趨勢偏弱", "0", "neutral"))
            
            # RSI 判定 (捕捉中鋼這類超跌股)
            if c['RSI'] < 35:
                score += 20
                details.append(("RSI 低檔超跌 (反彈預期)", "+20", "plus"))
            elif c['RSI'] > 75:
                score -= 15
                details.append(("RSI 高檔過熱 (回檔風險)", "-15", "minus"))
            else:
                details.append((f"RSI 數值: {c['RSI']:.1f}", "0", "neutral"))
                
            # 量價判定
            if c['Volume'] > c['VMA5'] and c['Close'] > p['Close']:
                score += 15
                details.append(("量價協同 (攻擊動能)", "+15", "plus"))
            else:
                details.append(("量價關係平淡", "0", "neutral"))
            
            prob = max(5, min(95, int(score)))
            results.append({"label": f"【{prob}%】 {code} {name}", "prob": prob, "breakdown": details, "price": f"{c['Close']:.2f}"})

    if results:
        # 4. 分區展示
        for title, is_strong in [("🚀 隔日看漲強勢區", True), ("⚠️ 隔日看跌弱勢區", False)]:
            st.subheader(title)
            sorted_list = sorted(results, key=lambda x: x['prob'], reverse=is_strong)[:10]
            for item in sorted_list:
                # 標籤顯示
                display_label = item['label'] if is_strong else item['label'].replace(f"【{item['prob']}%】", f"【{100-item['prob']}%】")
                with st.expander(f"{display_label} (價: {item['price']})"):
                    st.markdown("**🔍 AI 評分拆解原因：**")
                    for d_title, d_val, d_type in item['breakdown']:
                        color_class = "score-plus" if d_type == "plus" else "score-minus" if d_type == "minus" else ""
                        st.markdown(f"""
                            <div class="score-item">
                                <span>{d_title}</span>
                                <span class="{color_class}">{d_val}</span>
                            </div>
                        """, unsafe_allow_html=True)
                    st.write("---")
            st.divider()
