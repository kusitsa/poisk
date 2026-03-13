import streamlit as st
import requests
import uuid
import pytz
import re
from datetime import datetime
import streamlit.components.v1 as components

# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ
st.set_page_config(page_title="КУСИЦА", page_icon="🔍", layout="wide")

# 2. УЛЬТРА CSS (Полировка интерфейса)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #fff; }
    
    .logo { font-size: 40px; font-weight: 900; letter-spacing: -2px; color: #000; margin-bottom: 5px; }
    
    /* Шапка */
    .informer-box { display: flex; flex-wrap: wrap; gap: 6px; font-size: 11px; margin-bottom: 15px; }
    .informer-pill { background: #f2f2f4; padding: 5px 12px; border-radius: 12px; display: flex; align-items: center; gap: 4px; color: #555; white-space: nowrap; }
    .currency-red { border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; padding: 2px 8px; border-radius: 10px; }

    /* Поисковая строка */
    .stTextInput > div > div > input { font-size: 18px !important; padding: 20px 25px !important; border-radius: 30px !important; border: 2px solid #ffdb4d !important; box-shadow: 0 4px 20px rgba(0,0,0,0.06); }
    .stButton > button { height: 60px; width: 100%; border-radius: 30px; background-color: #ffdb4d !important; color: black !important; font-size: 24px; font-weight: bold; border: none !important; }

    /* Ответ ИИ (Алиса стайл) */
    .alice-card { 
        background: #fdfdff; padding: 25px; border-radius: 22px; 
        box-shadow: 0 10px 40px rgba(0,0,0,0.05); border-left: 6px solid #8e44ad; margin-bottom: 20px;
        line-height: 1.6; font-size: 17px;
    }

    /* Результаты */
    .result-item { margin-bottom: 25px; border-bottom: 1px solid #f0f0f0; padding-bottom: 15px; max-width: 800px; }
    .result-title { font-size: 20px; color: #1a0dab; text-decoration: none; font-weight: 500; }
    .result-url { color: #006621; font-size: 13px; display: block; margin-top: 2px; }

    /* Мобильная сетка картинок */
    .img-box { border: 1px solid #eee; border-radius: 12px; padding: 5px; text-align: center; background: #fff; margin-bottom: 10px; }
    
    @media (max-width: 640px) {
        .logo { font-size: 30px; text-align: center; }
        .informer-box { justify-content: center; }
        .stTabs [data-baseweb="tab"] { font-size: 14px; padding: 10px 5px; }
    }
    </style>
    """, unsafe_allow_html=True)

# 3. ПАМЯТЬ ПРИЛОЖЕНИЯ
if 'all_links' not in st.session_state: st.session_state.all_links = []
if 'all_images' not in st.session_state: st.session_state.all_images = []
if 'ai_answer' not in st.session_state: st.session_state.ai_answer = ""
if 'chat_log' not in st.session_state: st.session_state.chat_log = []
if 'page' not in st.session_state: st.session_state.page = 1
if 'last_query' not in st.session_state: st.session_state.last_query = ""
if 'view_idx' not in st.session_state: st.session_state.view_idx = None

# 4. ФУНКЦИИ API
@st.cache_data(ttl=900)
def get_header_data():
    try:
        tz = pytz.timezone('Europe/Moscow')
        w = requests.get("https://wttr.in/Moscow?format=%t", timeout=2).text.strip()
        curr = requests.get("https://open.er-api.com/v6/latest/USD", timeout=2).json()
        return datetime.now(tz).strftime("%d.%m"), datetime.now(tz).strftime("%H:%M"), w, round(curr['rates']['RUB'], 2)
    except: return "??", "??", "?", "??"

def get_ai(msgs):
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        payload = {"model": "llama-3.1-8b-instant", "messages": msgs, "temperature": 0.6}
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {api_key}"}, json=payload, timeout=20).json()
        return res['choices'][0]['message']['content']
    except: return "Кусица призадумалась. Попробуйте еще раз."

@st.cache_data(ttl=3600)
def get_suggestions(q):
    try:
        # Бесплатные подсказки Google
        r = requests.get(f"http://suggestqueries.google.com/complete/search?client=firefox&q={q}", timeout=2).json()
        return r[1][:5]
    except: return []

# 5. ЛОГИКА ПОИСКА
def run_search(query, page=1):
    s_key = st.secrets["SERPER_API_KEY"]
    headers = {'X-API-KEY': s_key, 'Content-Type': 'application/json'}
    if page == 1:
        st.session_state.all_links, st.session_state.all_images = [], []
        st.session_state.page, st.session_state.ai_answer, st.session_state.chat_log = 1, "", []

    with st.spinner(" "):
        try:
            # Текст
            res_t = requests.post("https://google.serper.dev/search", headers=headers, json={"q": query, "hl": "ru", "page": page}).json()
            # Картинки
            res_i = requests.post("https://google.serper.dev/images", headers=headers, json={"q": query, "page": page}).json()
            
            st.session_state.all_links.extend(res_t.get('organic', []))
            st.session_state.all_images.extend(res_i.get('images', []))
            
            if page == 1:
                ctx = "\n".join([l.get('snippet','') for l in res_t.get('organic', [])[:3]])
                st.session_state.ai_answer = get_ai([{"role":"system","content":"Ты Кусица. Отвечай подробно."}, {"role":"user","content":f"Вопрос: {query}\nИнфо: {ctx}"}])
            
            st.session_state.last_query = query
            st.session_state.page = page
        except: st.error("Ошибка поиска")

# --- ШАПКА ---
d, tm, w, usd_r = get_header_data()
st.markdown(f'<div class="logo">КУСИЦА</div>', unsafe_allow_html=True)
st.markdown(f'<div class="informer-box"><div class="informer-pill">📅 {d}</div><div class="informer-pill">🕒 МСК {tm}</div><div class="informer-pill">🌡️ {w}</div><div class="currency-red">USD {usd_r}₽</div></div>', unsafe_allow_html=True)

# --- ПОИСК И ПОДСКАЗКИ ---
url_q = st.query_params.get("q")
q_in = st.text_input("", value=url_q if url_q and not st.session_state.last_query else "", placeholder="Найдётся всё...", key="main_search", label_visibility="collapsed")

# Показываем подсказки, если начали писать
if q_in and q_in != st.session_state.last_query:
    suggs = get_suggestions(q_in)
    if suggs:
        st.caption("Возможно, вы имели в виду: " + ", ".join(suggs))

col_btn, col_share = st.columns([5, 1])
with col_btn:
    if st.button("Найти ответ ➔") or (url_q and not st.session_state.last_query):
        run_search(q_in if q_in else url_q, page=1)
with col_share:
    if st.session_state.last_query:
        share_url = f"https://kusitsa.streamlit.app/?q={st.session_state.last_query.replace(' ', '+')}"
        st.link_button("🔗 Ссылка", share_url)

# --- ВЫВОД ---
if st.session_state.all_links:
    # Виджет КАРТ (если нужно)
    if any(word in st.session_state.last_query.lower() for word in ["где", "адрес", "карта", "город"]):
        st.info(f"🗺️ [Открыть '{st.session_state.last_query}' на Яндекс Картах](https://yandex.ru/maps/?text={st.session_state.last_query})")

    t1, t2 = st.tabs(["🔍 Поиск", "🖼️ Картинки"])
    
    with t1:
        st.markdown(f'<div class="alice-card"><b>🟣 КУСИЦА:</b><br><br>{st.session_state.ai_answer}</div>', unsafe_allow_html=True)
        
        # ЧАТ-УТОЧНЕНИЕ
        u_q = st.text_input("Уточнить у Кусицы...")
        if u_q:
            with st.spinner(" "):
                chat_ans = get_ai([{"role":"assistant","content":st.session_state.ai_answer}, {"role":"user","content":u_q}])
                st.session_state.chat_log.append({"q": u_q, "a": chat_ans})
        
        for chat in st.session_state.chat_log:
            st.write(f"❓ *{chat['q']}*")
            st.info(chat['a'])

        st.write("---")
        for l in st.session_state.all_links:
            st.markdown(f'<div class="result-item"><a class="result-title" href="{l["link"]}" target="_blank">{l["title"]}</a><span class="result-url">{l["link"]}</span><div style="font-size:14px; color:#444;">{l.get("snippet","")}</div></div>', unsafe_allow_html=True)
        
        if st.button("Показать еще результаты ⬇️"):
            run_search(st.session_state.last_query, page=st.session_state.page + 1)
            st.rerun()

    with t2:
        if st.session_state.view_idx is not None:
            idx = st.session_state.view_idx
            img = st.session_state.all_images[idx]
            st.button("⬅️ Назад", on_click=lambda: setattr(st.session_state, 'view_idx', None))
            st.image(img['imageUrl'], use_container_width=True)
            st.subheader(img.get('title',''))
            c1, c2 = st.columns(2)
            with c1: st.link_button("🌐 На сайт", img['link'])
            with c2: 
                if st.button("📩 В Мессенджер"): st.code(img['imageUrl'])
            cp1, cp2 = st.columns(2)
            with cp1: 
                if idx > 0 and st.button("◀️ Назад"): st.session_state.view_idx -= 1; st.rerun()
            with cp2:
                if idx < len(st.session_state.all_images)-1 and st.button("Дальше ▶️"): st.session_state.view_idx += 1; st.rerun()
        else:
            cols = st.columns(2)
            for i, img in enumerate(st.session_state.all_images):
                with cols[i % 2]:
                    st.markdown(f'<div class="img-box"><img src="{img["imageUrl"]}" style="width:100%; border-radius:10px;"></div>', unsafe_allow_html=True)
                    if st.button(f"Увеличить #{i+1}", key=f"img_{i}"):
                        st.session_state.view_idx = i; st.rerun()
            if st.button("Загрузить еще картинки 🖼️"):
                run_search(st.session_state.last_query, page=st.session_state.page + 1)
                st.rerun()
else:
    # ГЛАВНАЯ (НОВОСТИ)
    st.write("---")
    st.subheader("Главное сегодня")
    try:
        n_res = requests.post("https://google.serper.dev/news", headers={'X-API-KEY': st.secrets["SERPER_API_KEY"]}, json={"q": "новости России", "hl": "ru"}).json()
        for n in n_res.get('news', [])[:5]:
            st.markdown(f"📰 [{n['title']}]({n['link']})")
    except: st.write("Новости загружаются...")

st.markdown("<br><hr><center style='color:#ccc; font-size:10px;'>КУСИЦА • 2024</center>", unsafe_allow_html=True)
