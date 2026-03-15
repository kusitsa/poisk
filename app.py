import streamlit as st
import requests
import uuid
import pytz
from datetime import datetime
from urllib.parse import urlparse
import streamlit.components.v1 as components

# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ
st.set_page_config(page_title="КУСИЦА — Поисковая Система", page_icon="🔍", layout="wide")

# 2. УЛЬТРА CSS (Яндекс-стайл + Виджеты)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #fff; }
    
    /* Логотип-кнопка */
    .stButton > button[key="logo_btn"] {
        background: none !important; border: none !important; padding: 0 !important;
        font-size: 38px !important; font-weight: 900 !important; letter-spacing: -2.5px !important;
        color: #000 !important; cursor: pointer !important; text-align: left !important;
    }
    
    /* Информеры */
    .informer-box { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }
    .informer-pill { background: #f2f2f4; padding: 4px 12px; border-radius: 12px; font-size: 11px; color: #555; white-space: nowrap; }
    .currency-red { border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; padding: 2px 10px; border-radius: 10px; font-size: 11px; }
    
    /* Поиск */
    .stTextInput > div > div > input { font-size: 18px !important; padding: 18px 22px !important; border-radius: 30px !important; border: 2px solid #ffdb4d !important; }
    .stButton > button:not([key="logo_btn"]) { height: 50px; width: 100%; border-radius: 25px; background-color: #ffdb4d !important; color: black !important; font-size: 18px; font-weight: bold; }
    
    /* Переводчик */
    .translator-box { background: #f8f9fa; padding: 20px; border-radius: 25px; border: 2px solid #ffdb4d; margin-bottom: 25px; }
    
    /* Результаты */
    .favicon { width: 18px; height: 18px; vertical-align: middle; margin-right: 8px; border-radius: 3px; }
    .result-item { margin-bottom: 25px; padding: 10px; border-radius: 15px; }
    .result-title { font-size: 20px; color: #1a0dab; text-decoration: none; font-weight: 500; }
    
    /* Квадраты */
    .img-square { width: 100%; aspect-ratio: 1 / 1; object-fit: cover; border-radius: 15px; border: 1px solid #eee; margin-bottom: 5px; }
    .video-row { display: flex; gap: 15px; background: #fff; padding: 10px; border-radius: 15px; border-bottom: 1px solid #f0f0f0; align-items: center; margin-bottom: 10px; }
    .video-thumb { width: 100px; height: 100px; min-width: 100px; object-fit: cover; border-radius: 12px; background: #000; }

    .alice-card { background: #fdfdff; padding: 25px; border-radius: 25px; box-shadow: 0 10px 40px rgba(0,0,0,0.05); border-left: 8px solid #8e44ad; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# 3. ИНИЦИАЛИЗАЦИЯ ПАМЯТИ
state = st.session_state
for k in ['links', 'images', 'videos', 'ai_history', 'last_q', 'page', 'view_img_idx']:
    if k not in state: state[k] = [] if 's' in k or 'history' in k else (1 if k=='page' else None)

# 4. ФУНКЦИИ API
def get_ai_res(msgs):
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", 
                          headers={"Authorization": f"Bearer {api_key}"}, 
                          json={"model": "llama-3.1-8b-instant", "messages": msgs, "temperature": 0.7}, timeout=20).json()
        return res['choices'][0]['message']['content']
    except: return "Ошибка ассистента."

@st.cache_data(ttl=600)
def get_header_data():
    try:
        tz_m = pytz.timezone('Europe/Moscow')
        now = datetime.now(tz_m)
        w = requests.get("https://wttr.in/Moscow?format=%t", timeout=2).text.strip()
        c = requests.get("https://open.er-api.com/v6/latest/USD", timeout=2).json()
        usd = round(c['rates']['RUB'], 1)
        eur = round(usd / (c['rates']['EUR'] / c['rates']['USD']), 1)
        return now.strftime("%d.%m"), now.strftime("%H:%M"), w, usd, eur
    except: return "??.??", "??:??", "?", "??", "??"

def perform_search(q, p=1):
    if not q: return
    s_key = st.secrets["SERPER_API_KEY"]
    h = {'X-API-KEY': s_key, 'Content-Type': 'application/json'}
    if p == 1: state.links, state.images, state.videos, state.page, state.ai_history = [], [], [], 1, []
    
    try:
        r_t = requests.post("https://google.serper.dev/search", headers=h, json={"q": q, "hl": "ru", "gl": "ru", "page": p}).json()
        state.links.extend(r_t.get('organic', []))
        r_i = requests.post("https://google.serper.dev/images", headers=h, json={"q": q, "hl": "ru", "gl": "ru", "page": p}).json()
        state.images.extend(r_i.get('images', []))
        video_q = f"{q} site:rutube.ru OR site:vk.com OR site:dzen.ru"
        r_v = requests.post("https://google.serper.dev/videos", headers=h, json={"q": video_q, "hl": "ru", "gl": "ru", "page": p}).json()
        state.videos.extend(r_v.get('videos', []))
        
        if p == 1 and state.links:
            ctx = "\n".join([l.get('snippet','') for l in state.links[:3]])
            ans = get_ai_res([{"role":"system","content":"Ты Кусица. Отвечай подробно."}, {"role":"user","content":f"Вопрос: {q}\nИнфо: {ctx}"}])
            state.ai_history = [{"content": ans}]
        state.last_q, state.page = q, p
    except: st.error("Ошибка сети")

# --- ШАПКА ---
d, tm, w_msk, usd_r, eur_r = get_header_data()
col_l, col_i = st.columns([1, 4])
with col_l:
    if st.button("КУСИЦА", key="logo_btn"):
        for k in ['links', 'images', 'videos', 'ai_history', 'last_q', 'page']: state[k] = [] if 's' in k or 'history' in k else 1
        st.query_params.clear()
        st.rerun()

with col_i:
    st.markdown(f"""
    <div class="informer-box">
        <div class="informer-pill">📅 {d}</div>
        <div class="informer-pill">🕒 {tm} МСК</div>
        <div class="informer-pill">🌡️ МСК {w_msk}</div>
        <div class="currency-red">USD {usd_r}₽</div>
        <div class="currency-red">EUR {eur_r}₽</div>
    </div>
    """, unsafe_allow_html=True)

# --- ПОИСК ---
url_query = st.query_params.get("q")
if url_query and state.last_q != url_query: perform_search(url_query, 1)

q_input = st.text_input("", value=url_query if url_query and not state.last_q else "", placeholder="Найдётся всё...", key="main_search", label_visibility="collapsed")
if st.button("Найти ответ ➔") or (q_input and q_input != state.last_q):
    perform_search(q_input, 1)

# --- ВИДЖЕТ ПЕРЕВОДЧИКА ---
if q_input and "переводчик" in q_input.lower():
    st.markdown('<div class="translator-box">', unsafe_allow_html=True)
    st.markdown("### 🌐 КУСИЦА ПЕРЕВОДЧИК")
    langs = ["Русский", "English", "Deutsch", "Français", "Қазақша", "中文", "日本語"]
    c1, c2 = st.columns(2)
    with c1:
        l_from = st.selectbox("Из", langs, index=0)
        t_in = st.text_area("Текст", height=100, key="t_in")
    with c2:
        l_to = st.selectbox("В", langs, index=1)
        if t_in:
            res_trans = get_ai_res([{"role":"user", "content":f"Переведи с {l_from} на {l_to}: {t_in}. Выдай только перевод."}])
            st.text_area("Результат", value=res_trans, height=100, key="t_out")
        else:
            st.text_area("Результат", value="", height=100, disabled=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- ВЫВОД РЕЗУЛЬТАТОВ ---
if state.links:
    t1, t2, t3 = st.tabs(["🔍 Поиск", "🖼️ Картинки", "📺 Видео"])
    
    with t1:
        if state.ai_history:
            st.markdown(f'<div class="alice-card"><b>🟣 КУСИЦА АССИСТЕНТ</b><br><br>{state.ai_history[0]["content"]}</div>', unsafe_allow_html=True)
        st.write("---")
        for l in state.links:
            dom = urlparse(l['link']).netloc
            fav = f"https://www.google.com/s2/favicons?sz=64&domain_url={dom}"
            st.markdown(f"""
            <div class="result-item">
                <span style="color:green; font-size:13px;">{dom}</span><br>
                <img src="{fav}" class="favicon">
                <a href="{l["link"]}" target="_blank" class="result-title">{l["title"]}</a>
                <div style="font-size:14px; color:#444; margin-top:5px;">{l.get("snippet","")}</div>
            </div>
            """, unsafe_allow_html=True)
        if st.button("Показать еще ссылки"): perform_search(state.last_q, state.page + 1); st.rerun()

    with t2:
        if state.view_img_idx is not None:
            idx = state.view_img_idx
            img = state.images[idx]
            st.button("⬅️ Назад", on_click=lambda: setattr(state, 'view_img_idx', None))
            st.image(img['imageUrl'], use_container_width=True)
            st.subheader(img.get('title',''))
            st.link_button(f"🌐 На сайт", img['link'])
            c1, c2 = st.columns(2)
            with c1: 
                if idx > 0 and st.button("◀️"): state.view_img_idx -= 1; st.rerun()
            with c2:
                if idx < len(state.images)-1 and st.button("▶️"): state.view_img_idx += 1; st.rerun()
        else:
            cols = st.columns(2)
