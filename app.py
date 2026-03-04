import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib3
from datetime import datetime

# 關閉 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 1. 頁面配置與手機端 CSS 優化
st.set_page_config(page_title="台股 AI 診斷站", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    /* 調整下拉選單標題的字體與間距 */
    .stExpander { border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 5px; }
    .stMetric { background-color: #f8fafc; padding: 10px; border-radius: 5px; }
    h3 { padding-top: 20px; color: #1e293b; }
    </style>
    """, unsafe_allow_html=True)

# 2. 數據分析核心邏輯
@st.cache_data(ttl=3600)
def get_full_analysis(symbol):
    s = f"{symbol.strip().upper()}.TW"
    h = yf.Ticker(s).history(period="2mo")
    if h.empty:
        s = f"{symbol.strip().upper()}.TWO"
        h = yf.Ticker(s).history(period="2mo")
    
    if not h.empty and len(h) >= 20:
        # 計算技術指標
        h['MA5'] = h['Close'].rolling(5).mean()
        h['MA20'] = h['Close'].rolling(20).mean()
        h['VMA5'] = h['Volume'].rolling(5).mean()
        delta = h['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        h['RSI'] = 100 - (100 / (1 + gain / loss))
        return h
    return pd.DataFrame()

# 3. 系統標題
st.title("📈 台股 AI 智慧監測站")
st.caption(f"數據自動更新：每日 16:00 | 目前診斷時間：{datetime.now().strftime('%H:%M')}")

# 觀測池清單
stock_pool = {
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2308": "台達電",
    "3231": "緯創", "2382": "廣達", "2881": "富邦金", "2882": "國泰金",
    "2603": "長榮", "1519": "華城", "2002": "中鋼", "2409": "友達",
    "3037": "欣興", "2303": "聯電", "2609": "陽明"
}

# 4. 全自動執行分析並分類
with st.spinner("正在自動同步數據並計算指標..."):
    all_data = []
    for code, name in stock_pool.items():
        hist = get_full_analysis(code)
        if not hist.empty:
            c, p = hist.iloc[-1], hist.iloc[-2]
            
            # --- 權重評分判定 ---
            score = 50
            m5, m20, rsi, vol = c['Close'] > c['MA5'], c['Close'] > c['MA20'], c['RSI'], c['Volume'] > c['VMA5'] and c['Close'] > p['Close']
            
            if m5: score += 10
            if m20: score += 15
            if rsi < 35: score += 20
            elif rsi > 75: score -= 15
            if vol: score += 15
            
            prob = max(5, min(95, int(score)))
            all_data.append({
                "label": f"【{prob}%】 {code} {name} (價: {c['Close']:.2f})",
                "prob": prob,
                "metrics": {
                    "MA5": "站上均線 (多)" if m5 else "跌破均線 (空)",
                    "MA20": "月線上方 (強)" if m20 else "月線下方 (弱)",
                    "RSI": f"{rsi:.2f}",
                    "量價": "價漲量增 (實)" if vol else "量縮/價跌 (虛)"
                }
            })

    if all_data:
        # 5. 展示區塊：強勢與弱勢垂直排列
        
        # --- 看漲強勢區 ---
        st.subheader("🚀 隔日看漲強勢區 (Top 10)")
        strong_list = sorted(all_data, key=lambda x: x['prob'], reverse=True)[:10]
        for item in strong_list:
            # 使用 Expander 製作下拉選單
            with st.expander(item['label']):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("MA5", item['metrics']['MA5'])
                c2.metric("MA20", item['metrics']['MA20'])
                c3.metric("RSI", item['metrics']['RSI'])
                c4.metric("量價", item['metrics']['量價'])
        
        st.divider()
        
        # --- 看跌弱勢區 ---
        st.subheader("⚠️ 隔日看跌弱勢區 (Top 10)")
        # 按得分從低到高排（空頭強度最高）
        weak_list = sorted(all_data, key=lambda x: x['prob'])[:10]
        for item in weak_list:
            # 顯示「下跌機率」標籤
            bear_label = item['label'].replace(f"【{item['prob']}%】", f"【{100-item['prob']}%】")
            with st.expander(bear_label):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("MA5", item['metrics']['MA5'])
                c2.metric("MA20", item['metrics']['MA20'])
                c3.metric("RSI", item['metrics']['RSI'])
                c4.metric("量價", item['metrics']['量價'])
