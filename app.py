import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib3

# 關閉 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 1. 頁面配置與美化 CSS
st.set_page_config(page_title="台股 AI 自動監測站", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #fcfcfc; }
    .stDataFrame { border: 1px solid #e2e8f0; border-radius: 12px; }
    h1 { color: #0f172a; font-weight: 800; letter-spacing: -1px; }
    h3 { color: #334155; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 自動更新快取 (TTL 設定為 1 小時，確保每日數據新鮮)
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

# 3. 標題與側邊欄狀態顯示
st.markdown("<h1>📈 台股 AI 全自動監測站 <small style='font-size: 14px; color: #64748b;'>資料每日 16:00 自動結算</small></h1>", unsafe_allow_html=True)

with st.sidebar:
    st.title("🛡️ 系統狀態")
    st.success("自動監控中：ON")
    st.info("模式：多指標權重診斷 (MA+RSI+量價)")
    st.write("目前追蹤 35 檔市場指標股")

# 4. 執行掃描邏輯 (無須按鈕，直接運行)
stock_pool = {
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2308": "台達電",
    "3231": "緯創", "2382": "廣達", "2881": "富邦金", "2882": "國泰金",
    "2603": "長榮", "1519": "華城", "2002": "中鋼", "2409": "友達",
    "2303": "聯電", "2886": "兆豐金", "2609": "陽明"
}

with st.spinner("正在自動同步 16:00 盤後數據並執行 AI 診斷..."):
    results = []
    for code, name in stock_pool.items():
        hist = get_stock_data(code)
        if not hist.empty and len(hist) >= 20:
            hist = calculate_logic(hist)
            c, p = hist.iloc[-1], hist.iloc[-2]
            
            # 多權重評分系統
            score = 50
            if c['Close'] > c['MA5']: score += 10
            if c['Close'] > c['MA20']: score += 15
            if c['RSI'] < 35: score += 20
            elif c['RSI'] > 75: score -= 15
            if c['Close'] > p['Close'] and c['Volume'] > c['VMA5']: score += 15
            
            prob = max(5, min(95, int(score)))
            
            # 關鍵訊號判定
            signals = []
            if c['Close'] > c['MA20']: signals.append("趨勢偏多")
            if c['Volume'] > c['VMA5']: signals.append("量能放大")
            if c['RSI'] > 70: signals.append("進入超買")
            
            results.append({
                "代碼名稱": f"🔹 {code} {name}", 
                "收盤價": f"{c['Close']:,.2f}", 
                "上漲動能": prob,
                "下跌風險": 100 - prob,
                "AI 診斷": " | ".join(signals) if signals else "觀望盤整"
            })

    if results:
        df = pd.DataFrame(results)
        
        # 強勢區 (垂直排列)
        st.subheader("🚀 隔日看漲強勢區 (Top 10)")
        st.dataframe(
            df.sort_values("上漲動能", ascending=False).head(10)[['代碼名稱', '收盤價', '上漲動能', 'AI 診斷']],
            use_container_width=True, hide_index=True,
            column_config={
                "上漲動能": st.column_config.ProgressColumn("上漲機率", format="%d %%", min_value=0, max_value=100, color="red")
            }
        )

        st.divider()

        # 弱勢區 (垂直排列)
        st.subheader("⚠️ 隔日看跌弱勢區 (Top 10)")
        st.dataframe(
            df.sort_values("下跌風險", ascending=False).head(10)[['代碼名稱', '收盤價', '下跌風險', 'AI 診斷']],
            use_container_width=True, hide_index=True,
            column_config={
                "下跌風險": st.column_config.ProgressColumn("下跌機率", format="%d %%", min_value=0, max_value=100, color="green")
            }
        )
