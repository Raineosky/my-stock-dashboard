import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 1. 頁面與手機視覺配置
st.set_page_config(page_title="台股 AI 診斷站", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    .report-card { border: 1px solid #e2e8f0; border-radius: 12px; padding: 15px; margin-bottom: 10px; background: white; }
    .metric-label { font-size: 0.9rem; color: #64748b; }
    .metric-value { font-size: 1.1rem; font-weight: bold; color: #1e293b; }
    </style>
    """, unsafe_allow_html=True)

# 2. 核心抓取與指標計算邏輯
@st.cache_data(ttl=3600)
def get_analysis_data(symbol):
    s = f"{symbol.strip().upper()}.TW"
    h = yf.Ticker(s).history(period="2mo")
    if h.empty:
        s = f"{symbol.strip().upper()}.TWO"
        h = yf.Ticker(s).history(period="2mo")
    
    if not h.empty:
        # 計算 MA
        h['MA5'] = h['Close'].rolling(5).mean()
        h['MA20'] = h['Close'].rolling(20).mean()
        # 計算 RSI
        delta = h['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        h['RSI'] = 100 - (100 / (1 + gain / loss))
        # 量價均線
        h['VMA5'] = h['Volume'].rolling(5).mean()
    return h

# 3. 標題區
st.title("📈 台股 AI 智慧診斷監測站")
st.caption(f"自動同步 16:00 盤後數據 | 診斷時間：{datetime.now().strftime('%H:%M')}")

stock_pool = {
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2308": "台達電",
    "3231": "緯創", "2382": "廣達", "2881": "富邦金", "2882": "國泰金",
    "2603": "長榮", "1519": "華城", "2002": "中鋼", "2409": "友達"
}

# 4. 自動掃描並生成診斷清單
with st.spinner("正在逐一解析技術指標..."):
    full_results = []
    for code, name in stock_pool.items():
        hist = get_analysis_data(code)
        if not hist.empty and len(hist) >= 20:
            c, p = hist.iloc[-1], hist.iloc[-2]
            
            # --- 多重指標評分判定 ---
            score = 50
            ma5_check = c['Close'] > c['MA5']
            ma20_check = c['Close'] > c['MA20']
            rsi_value = c['RSI']
            volume_check = c['Volume'] > c['VMA5'] and c['Close'] > p['Close']
            
            if ma5_check: score += 10
            if ma20_check: score += 15
            if rsi_value < 35: score += 20
            elif rsi_value > 75: score -= 15
            if volume_check: score += 15
            
            prob = max(5, min(95, int(score)))
            
            # 儲存所有細節用於下拉選單
            full_results.append({
                "name": f"{code} {name}",
                "price": c['Close'],
                "prob": prob,
                "details": {
                    "MA5": "高於均線 (偏多)" if ma5_check else "低於均線 (偏空)",
                    "MA20": "站上月線 (趨勢強)" if ma20_check else "月線下方 (趨勢弱)",
                    "RSI": f"{rsi_value:.2f}",
                    "量價": "價漲量增 (動能足)" if volume_check else "量能不足/價跌"
                }
            })

    # 5. UI 呈現：改用卡片與下拉選單
    if full_results:
        # 先按分數排序
        sorted_res = sorted(full_results, key=lambda x: x['prob'], reverse=True)
        
        st.subheader("🚀 今日動能診斷報告 (由強至弱)")
        
        for item in sorted_res:
            # 標題列：顯示名稱與動能進度條
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write(f"**{item['name']}** (最新價: {item['price']:.2f})")
            with col2:
                # 簡單進度條顯示
                st.progress(item['prob'] / 100, text=f"動能: {item['prob']}%")
            
            # --- 下拉選單：顯示分析結果 ---
            with st.expander("🔍 查看詳細技術分析診斷"):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("短期(MA5)", item['details']['MA5'])
                c2.metric("中期(MA20)", item['details']['MA20'])
                c3.metric("強弱(RSI)", item['details']['RSI'])
                c4.metric("量價關係", item['details']['量價'])
            st.write("---")
