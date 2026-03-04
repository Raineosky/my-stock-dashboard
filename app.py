import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib3
from datetime import datetime

# 關閉 SSL 警告 (針對公務環境阻擋)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 1. 頁面配置：專為手機優化
st.set_page_config(page_title="台股 AI 監測站", layout="wide", initial_sidebar_state="collapsed")

# 2. 注入 CSS：美化卡片並確保手機端字體清晰
st.markdown("""
    <style>
    .stDataFrame { border-radius: 10px; }
    h1 { font-size: 1.8rem !important; color: #1e293b; }
    h3 { font-size: 1.2rem !important; color: #334155; }
    /* 針對手機螢幕縮小表格間距 */
    [data-testid="stMetric"] { padding: 10px; border: 1px solid #f0f2f6; border-radius: 8px; background: #ffffff; }
    </style>
    """, unsafe_allow_html=True)

# 3. 核心數據抓取：TTL 設為 1 小時 (確保 16:00 後能刷出新數據)
@st.cache_data(ttl=3600)
def get_stock_data(symbol):
    s = f"{symbol.strip().upper()}.TW"
    h = yf.Ticker(s).history(period="2mo")
    if h.empty:
        s = f"{symbol.strip().upper()}.TWO"
        h = yf.Ticker(s).history(period="2mo")
    return h

def calculate_logic(df):
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA20'] = df['Close'].rolling(20).mean()
    df['VMA5'] = df['Volume'].rolling(5).mean()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + gain / loss))
    return df

# 4. 主介面展示
st.title("📈 台股 AI 全自動監測站")
st.caption(f"系統自動更新時間：每日 16:00 | 目前時間：{datetime.now().strftime('%H:%M')}")

# 觀測清單
stock_pool = {
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2308": "台達電",
    "3231": "緯創", "2382": "廣達", "2881": "富邦金", "2882": "國泰金",
    "2603": "長榮", "1519": "華城", "2002": "中鋼", "2409": "友達"
}

# --- 一進入頁面立即執行掃描 ---
with st.spinner("AI 正在分析今日最新數據..."):
    results = []
    for code, name in stock_pool.items():
        hist = get_stock_data(code)
        if not hist.empty and len(hist) >= 20:
            hist = calculate_logic(hist)
            c, p = hist.iloc[-1], hist.iloc[-2]
            
            # 多權重評分
            score = 50
            if c['Close'] > c['MA5']: score += 10
            if c['Close'] > c['MA20']: score += 15
            if c['RSI'] < 35: score += 20
            elif c['RSI'] > 75: score -= 15
            if c['Close'] > p['Close'] and c['Volume'] > c['VMA5']: score += 15
            
            prob = max(5, min(95, int(score)))
            results.append({
                "代碼名稱": f"{code} {name}", 
                "收盤價": f"{c['Close']:.2f}", 
                "上漲動能": prob,
                "下跌風險": 100 - prob,
                "狀態": "強勢" if prob > 70 else "盤整" if prob > 40 else "弱勢"
            })

    if results:
        df = pd.DataFrame(results)
        
        # 垂直排列，手機端好滑動
        st.subheader("🚀 看漲強勢區 (Top 10)")
        st.dataframe(
            df.sort_values("上漲動能", ascending=False).head(10)[['代碼名稱', '收盤價', '上漲動能', '狀態']],
            use_container_width=True, hide_index=True,
            column_config={
                "上漲動能": st.column_config.ProgressColumn("上漲機率", format="%d %%", min_value=0, max_value=100, color="red")
            }
        )

        st.divider()

        st.subheader("⚠️ 看跌弱勢區 (Top 10)")
        st.dataframe(
            df.sort_values("下跌風險", ascending=False).head(10)[['代碼名稱', '收盤價', '下跌風險', '狀態']],
            use_container_width=True, hide_index=True,
            column_config={
                "下跌風險": st.column_config.ProgressColumn("下跌機率", format="%d %%", min_value=0, max_value=100, color="green")
            }
        )
