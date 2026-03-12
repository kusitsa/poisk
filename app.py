import streamlit as st
import requests
import uuid
import pytz
import re
from datetime import datetime
import google.generativeai as genai
import streamlit.components.v1 as components

# 1. КОНФИГУРАЦИЯ
st.set_page_config(page_title="КУСИЦА", page_icon="🔍", layout="wide")

# 2. CSS ДИЗАЙН
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #fff; color: #000; }
    .logo { font-size: 38px; font-weight: 900; letter-spacing: -2.5px; color: #000; margin-bottom: 5px; }
    .informer-box { display: flex; flex-wrap: wrap; gap: 8px; font-size: 11px; margin-bottom: 20px; }
    .informer-pill { background: #f2f2f4; padding: 4px 10px; border-radius: 12px; display: flex; align-items: center; gap: 4px; color: #555; }
    .currency-red { border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; padding: 2px 8px; border-radius: 10px; }
    .stTextInput > div > div > input { font-size: 18px !important; padding: 20px 25px !important; border-radius: 28px !important; border: 2px solid #ffdb4d !important; }
    .stButton > button { height: 56px; width: 100%; border-radius: 28px; background-color: #ffdb4d !important; color: black !important; font-weight: bold !important; }
    .alice-card { background: #fdfdff; padding: 25px; border-radius: 22px; box-shadow: 0 10px 40px rgba(0,0,0,0.05); border-left: 6px solid #8e44ad; margin-top: 15px; font-size: 18px; }
    .converter-card { background: #fff; padding: 25px; border-radius: 20px; border: 2px solid #ffdb4d; text-align: center; margin: 15px 0; }
    </style>
    """, unsafe_allow_html=True)

# 3. ПАМЯТЬ ПРИЛОЖЕНИЯ
if 'res' not in st.session_state: st.session_state.res = None
if 'history' not in st.session_state: st.session_state.history = []
if 'limits' not in st.session_state: st.session_state.limits = {"links": 3, "imgs": 8, "vids": 4}
if 'view_img_idx' not in st.session_state: st.session_state.view_img_idx = None

# 4. ФУНКЦИИ
@st.cache_data(ttl=600)
def get_header_data():
    try:
        tz_m, tz_k = pytz.timezone('Europe/Moscow'), pytz.timezone('Asia/Almaty')
        now = datetime.now(tz_m)
        w_m = requests.get("https://wttr.in/Moscow?format=%t", timeout=3).text.strip()
        curr = requests.get("https://open.er-api.com/v6/latest/USD", timeout=3).json()
        return now.strftime("%d.%m"), now.strftime("%H:%M"), datetime.now(tz_k).strftime("%H:%M"), w_m, round(curr['rates']['RUB'], 2)
    except: return "??", "??", "??", "?", "??"

def get_ai_res(prompt_text):
    try:
        if "GEMINI_API_KEY" not in st.secrets:
            return "ОШИБКА: Ключ GEMINI_API_KEY не найден в Secrets."
        
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # Используем современную универсальную модель
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt_text)
        return response.text
    except Exception as e:
        # ВЫВОДИМ ТОЧНУЮ ОШИБКУ ДЛЯ ДИАГНОСТИКИ
        return f"КРИТИЧЕСКАЯ ОШИБКА ИИ: {str(e)}"

@st.cache_data(ttl=1800)
def fetch_news(key):
    try:
        r = requests.post("https://google.serper.dev/news", headers={'X-API-KEY': key}, json={"q": "новости сегодня Россия", "gl": "ru", "hl": "ru"}).json()
        return r.get('news', [])[:5]
    except: return []

# --- ШАПКА ---
d, tm, tk, wm, usd_r = get_header_data()
st.markdown('<div class="logo">КУСИЦА</div>', unsafe_allow_html=True)
st.markdown(f'<div class="informer-box"><div class="informer-pill">📅 {d}</div><div class="informer-pill">🕒 МСК {tm}</div><div class="informer-pill">🇰🇿 КЗ {tk}</div><div class="informer-pill">🌡️ {wm}</div><div class="currency-red">USD {usd_r}₽</div></div>', unsafe_allow_html=True)

# --- ПОИСК ---
q = st.text_input("", placeholder="Найдётся всё...", key="main_search", label_visibility="collapsed")
btn = st.button("➔")

if (btn or q) and q:
    if st.session_state.get('last_q') != q:
        with st.spinner("КУСИЦА ищет..."):
            try:
                s_key = st.secrets["SERPER_API_KEY"]
                sr = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': s_key}, json={"q": q, "hl": "ru"}).json()
                ir = requests.post("https://google.serper.dev/images", headers={'X-API-KEY': s_key}, json={"q": q}).json()
                links = sr.get('organic', [])
                
                # Запрос к ИИ
                prompt = f"Ты — Кусица, эрудированный ассистент. Ответь подробно на вопрос: {q}. Данные поиска: {links[:5]}"
                ans = get_ai_res(prompt)
                
                st.session_state.res = {"ans": ans, "links": links, "imgs": ir.get('images', []), "q": q}
                st.session_state.last_q = q
            except Exception as e:
                st.error(f"Ошибка поиска: {e}")

# --- ВЫВОД ---
if st.session_state.res:
    res = st.session_state.res
    st.markdown(f'<div class="alice-card"><b>🟣 КУСИЦА:</b><br><br>{res["ans"]}</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔍 Поиск", "🖼️ Картинки"])
    with tab1:
        for l in res['links'][:st.session_state.limits['links']]:
            st.markdown(f'<div style="margin-bottom:20px;"><a href="{l["link"]}" target="_blank" style="font-size:18px; color:#1a0dab; text-decoration:none; font-weight:500;">{l["title"]}</a><br><small style="color:#006621;">{l["link"][:80]}...</small><div>{l.get("snippet","")}</div></div>', unsafe_allow_html=True)
        if st.button("Показать еще"): st.session_state.limits['links'] += 5; st.rerun()
    with tab2:
        cols = st.columns(2)
        for i, img in enumerate(res['imgs'][:10]):
            with cols[i % 2]: st.image(img['imageUrl'], use_container_width=True)
else:
    st.write("---")
    st.subheader("Главное сегодня")
    for n in fetch_news(st.secrets.get("SERPER_API_KEY", "")):
        st.markdown(f"📰 [{n['title']}]({n['link']})")
