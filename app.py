import streamlit as st
import requests
import uuid
import pytz
import re
from datetime import datetime
import streamlit.components.v1 as components

# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ
st.set_page_config(page_title="КУСИЦА", page_icon="🔍", layout="wide")

# 2. УЛЬТРА CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #fff; }
    .logo { font-size: 42px; font-weight: 900; letter-spacing: -2.5px; color: #000; }
    .informer-box { display: flex; flex-wrap: wrap; gap: 8px; font-size: 11px; margin-bottom: 20px; }
    .informer-pill { background: #f2f2f4; padding: 4px 10px; border-radius: 12px; display: flex; align-items: center; gap: 4px; color: #555; }
    .currency-red { border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; padding: 2px 10px; border-radius: 10px; }
    
    /* Стили мессенджера */
    .messenger-box {
        background: #f0f2f5; padding: 20px; border-radius: 20px;
        border: 2px solid #007bff; margin: 15px 0;
    }
    .messenger-header { color: #007bff; font-weight: bold; margin-bottom: 10px; display: flex; align-items: center; gap: 5px; }

    /* Поиск и кнопки */
    .stTextInput > div > div > input { font-size: 18px !important; padding: 20px 25px !important; border-radius: 35px !important; border: 2.5px solid #ffdb4d !important; }
    .stButton > button { height: 55px; width: 100%; border-radius: 35px; background-color: #ffdb4d !important; color: black !important; font-size: 20px; font-weight: bold; border: none !important; }
    .alice-card { background: #fdfdff; padding: 25px; border-radius: 22px; box-shadow: 0 10px 40px rgba(0,0,0,0.05); border-left: 6px solid #8e44ad; margin-top: 15px; font-size: 18px; }
    .search-title { font-size: 19px; color: #1a0dab; text-decoration: none; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

# 3. ПАМЯТЬ ПРИЛОЖЕНИЯ
if 'res' not in st.session_state: st.session_state.res = None
if 'history' not in st.session_state: st.session_state.history = []
if 'limits' not in st.session_state: st.session_state.limits = {"links": 3, "imgs": 8}
if 'view_img_idx' not in st.session_state: st.session_state.view_img_idx = None
if 'messenger_link' not in st.session_state: st.session_state.messenger_link = None

# 4. ФУНКЦИИ
@st.cache_data(ttl=600)
def get_header_data():
    try:
        tz_m = pytz.timezone('Europe/Moscow')
        now = datetime.now(tz_m)
        w_m = requests.get("https://wttr.in/Moscow?format=%t", timeout=2).text.strip()
        curr = requests.get("https://open.er-api.com/v6/latest/USD", timeout=2).json()
        return now.strftime("%d.%m"), now.strftime("%H:%M"), w_m, round(curr['rates']['RUB'], 2)
    except: return "??", "??", "?", "??"

def get_ai_res(msgs):
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": "llama-3.1-8b-instant", "messages": msgs, "temperature": 0.6}
        response = requests.post(url, headers=headers, json=payload, timeout=20).json()
        return response['choices'][0]['message']['content']
    except: return "Кусица задумалась..."

@st.cache_data(ttl=1800)
def fetch_news(key):
    try:
        r = requests.post("https://google.serper.dev/news", headers={'X-API-KEY': key}, json={"q": "новости сегодня", "gl": "ru", "hl": "ru"}).json()
        return r.get('news', [])[:5]
    except: return []

# --- ШАПКА ---
d, tm, wm, usd_r = get_header_data()
st.markdown(f'<div class="logo">КУСИЦА</div>', unsafe_allow_html=True)
st.markdown(f"""<div class="informer-box"><div class="informer-pill">📅 {d}</div><div class="informer-pill">🕒 МСК {tm}</div><div class="informer-pill">🌡️ МСК {wm}</div><div class="currency-red">USD {usd_r}₽</div></div>""", unsafe_allow_html=True)

# --- ПОИСК ---
q = st.text_input("", placeholder="Найдётся всё...", key="main_search", label_visibility="collapsed")
if st.button("Найти ответ ➔") or (q and st.session_state.get('last_q') != q):
    if q:
        with st.spinner(" "):
            try:
                s_key = st.secrets["SERPER_API_KEY"]
                sr = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': s_key}, json={"q": q, "hl": "ru"}).json()
                ir = requests.post("https://google.serper.dev/images", headers={'X-API-KEY': s_key}, json={"q": q}).json()
                links = sr.get('organic', [])
                ans = get_ai_res([{"role":"user","content":f"Вопрос: {q}. Инфо: {links[:3]}"}])
                st.session_state.res = {"ans": ans, "links": links, "imgs": ir.get('images', []), "q": q}
                if q not in st.session_state.history: st.session_state.history.append(q)
                st.session_state.last_q = q
                st.session_state.view_img_idx = None
            except: st.error("Ошибка сети")

# --- ВЫВОД ---
if st.session_state.res:
    tab1, tab2 = st.tabs(["🔍 Поиск", "🖼️ Картинки"])
    
    with tab1:
        st.markdown(f'<div class="alice-card"><b>🟣 КУСИЦА:</b><br><br>{st.session_state.res["ans"]}</div>', unsafe_allow_html=True)
        st.write("---")
        for l in st.session_state.res['links'][:st.session_state.limits['links']]:
            st.markdown(f'<div style="margin-bottom:20px;"><a href="{l["link"]}" target="_blank" class="search-title">{l["title"]}</a><br><small style="color:#006621;">{l["link"][:80]}...</small><div>{l.get("snippet","")}</div></div>', unsafe_allow_html=True)
        if st.button("Показать еще ссылки"): st.session_state.limits['links'] += 5; st.rerun()

    with tab2:
        imgs = st.session_state.res['imgs']
        if st.session_state.view_img_idx is not None:
            # УВЕЛИЧЕННЫЙ РЕЖИМ
            idx = st.session_state.view_img_idx
            curr = imgs[idx]
            st.button("⬅️ Назад к списку", on_click=lambda: setattr(st.session_state, 'view_img_idx', None))
            
            st.image(curr['imageUrl'], use_container_width=True)
            st.subheader(curr.get('title', 'Без названия'))
            
            # КНОПКИ ДЕЙСТВИЙ
            col1, col2 = st.columns(2)
            with col1:
                st.link_button("🌐 Перейти на сайт", curr['link'])
            with col2:
                if st.button("📩 Отправить в Мессенджер"):
                    st.session_state.messenger_link = curr['imageUrl']
            
            # ОКНО МЕССЕНДЖЕРА (ПОЯВЛЯЕТСЯ ПО НАЖАТИЮ)
            if st.session_state.messenger_link:
                st.markdown("""
                <div class="messenger-box">
                    <div class="messenger-header">💬 КУСИЦА МЕССЕНДЖЕР</div>
                    <p style="color:#555; font-size:14px;">Ссылка на изображение готова к копированию:</p>
                </div>
                """, unsafe_allow_html=True)
                st.code(st.session_state.messenger_link)
                if st.button("Закрыть мессенджер"):
                    st.session_state.messenger_link = None
                    st.rerun()

            # СТРЕЛОЧКИ
            c_prev, c_next = st.columns(2)
            with c_prev:
                if idx > 0: st.button("◀️ Предыдущая", on_click=lambda: setattr(st.session_state, 'view_img_idx', idx-1))
            with c_next:
                if idx < len(imgs)-1: st.button("Следующая ▶️", on_click=lambda: setattr(st.session_state, 'view_img_idx', idx+1))
        
        else:
            # СЕТКА КАРТИНОК
            cols = st.columns(2)
            for i, img in enumerate(imgs[:st.session_state.limits['imgs']]):
                with cols[i % 2]:
                    st.image(img['imageUrl'])
                    if st.button(f"Увеличить #{i+1}", key=f"img_{i}"):
                        st.session_state.view_img_idx = i
                        st.rerun()
            if st.button("Больше картинок"): st.session_state.limits['imgs'] += 10; st.rerun()
else:
    # НОВОСТИ
    st.write("---")
    st.subheader("Главное сегодня")
    for n in fetch_news(st.secrets.get("SERPER_API_KEY", "")):
        st.markdown(f"📰 [{n['title']}]({n['link']})")

st.markdown("<br><hr><center style='color:#ccc; font-size:10px;'>КУСИЦА • 2024</center>", unsafe_allow_html=True)
