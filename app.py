import streamlit as st
import requests
import uuid
import pytz
from datetime import datetime
from urllib.parse import urlparse
from duckduckgo_search import DDGS

# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ
st.set_page_config(page_title="КУСИЦА — Поисковая Система", page_icon="🔍", layout="wide")

# 2. УЛЬТРА CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #fff; }
    
    /* Кликабельный логотип */
    .stButton > button[key="logo_btn"] {
        background: none !important; border: none !important; padding: 0 !important;
        font-size: 38px !important; font-weight: 900 !important; letter-spacing: -2.5px !important;
        color: #000 !important; cursor: pointer !important;
    }
    
    .informer-box { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }
    .informer-pill { background: #f2f2f4; padding: 4px 12px; border-radius: 12px; font-size: 11px; color: #555; white-space: nowrap; }
    .currency-red { border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; padding: 2px 10px; border-radius: 10px; font-size: 11px; }
    
    .stTextInput > div > div > input { font-size: 18px !important; padding: 18px 22px !important; border-radius: 30px !important; border: 2px solid #ffdb4d !important; }
    .stButton > button:not([key="logo_btn"]) { height: 50px; width: 100%; border-radius: 25px; background-color: #ffdb4d !important; color: black !important; font-size: 18px; font-weight: bold; }
    
    .translator-box { background: #f8f9fa; padding: 20px; border-radius: 25px; border: 2px solid #ffdb4d; margin-bottom: 25px; }
    .favicon { width: 18px; height: 18px; vertical-align: middle; margin-right: 8px; border-radius: 3px; }
    .result-item { margin-bottom: 25px; padding: 10px; border-radius: 15px; }
    .result-title { font-size: 20px; color: #1a0dab; text-decoration: none; font-weight: 500; }
    
    .img-square { width: 100%; aspect-ratio: 1 / 1; object-fit: cover; border-radius: 15px; border: 1px solid #eee; margin-bottom: 5px; background: #f9f9f9; }
    .video-row { display: flex; gap: 15px; background: #fff; padding: 10px; border-radius: 15px; border-bottom: 1px solid #f0f0f0; align-items: center; margin-bottom: 10px; }
    .video-thumb { width: 110px; height: 110px; min-width: 110px; object-fit: cover; border-radius: 12px; background: #000; }

    .alice-card { background: #fdfdff; padding: 25px; border-radius: 25px; box-shadow: 0 10px 40px rgba(0,0,0,0.05); border-left: 8px solid #8e44ad; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# 3. ИНИЦИАЛИЗАЦИЯ ПАМЯТИ
state = st.session_state
init_keys = ['links', 'images', 'videos', 'ai_history', 'last_q', 'chat_extra', 'view_img_idx']
for k in init_keys:
    if k not in state: state[k] = [] if 's' in k or 'history' in k or 'extra' in k else None

# 4. ФУНКЦИИ API
def get_ai_res(msgs):
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", 
                          headers={"Authorization": f"Bearer {api_key}"}, 
                          json={"model": "llama-3.1-8b-instant", "messages": msgs, "temperature": 0.7}, timeout=20).json()
        return res['choices'][0]['message']['content']
    except: return "Кусица задумалась. Попробуйте еще раз."

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

def perform_search(q):
    if not q: return
    state.links, state.images, state.videos, state.ai_history, state.chat_extra = [], [], [], [], []
    
    with st.spinner("КУСИЦА ищет в сети..."):
        try:
            with DDGS() as ddgs:
                # Поиск только на русском (region='ru-ru')
                state.links = [r for r in ddgs.text(q, region='ru-ru', max_results=20)]
                state.images = [r for r in ddgs.images(q, region='ru-ru', max_results=15)]
                state.videos = [r for r in ddgs.videos(q, region='ru-ru', max_results=12)]
            
            if state.links:
                ctx = "\n".join([l.get('body','') for l in state.links[:3]])
                ans = get_ai_res([{"role":"system","content":"Ты Кусица. Отвечай максимально подробно и только на русском."}, {"role":"user","content":f"Вопрос: {q}\nИнфо: {ctx}"}])
                state.ai_history = [{"content": ans}]
            
            state.last_q = q
        except: st.error("Ошибка поиска. Попробуйте снова через пару секунд.")

# --- ШАПКА ---
d_s, t_s, w_m, u_v, e_v = get_header_data()
col_l, col_i = st.columns([1, 4])
with col_l:
    if st.button("КУСИЦА", key="logo_btn"):
        for k in init_keys: state[k] = [] if 's' in k or 'history' in k or 'extra' in k else None
        st.query_params.clear(); st.rerun()

with col_i:
    st.markdown(f"""
    <div class="informer-box">
        <div class="informer-pill">📅 {d_s}</div>
        <div class="informer-pill">🕒 {t_s} МСК</div>
        <div class="informer-pill">🌡️ МСК {w_m}</div>
        <div class="currency-red">USD {u_v}₽</div>
        <div class="currency-red">EUR {e_v}₽</div>
    </div>
    """, unsafe_allow_html=True)

# --- ПОИСК ---
url_query = st.query_params.get("q")
if url_query and state.last_q != url_query: perform_search(url_query)

q_input = st.text_input("", value=url_query if url_query and not state.last_q else "", placeholder="Найдётся всё...", key="main_search", label_visibility="collapsed")
if st.button("Найти ответ ➔") or (q_input and q_input != state.last_q):
    perform_search(q_input)

# --- ПЕРЕВОДЧИК ---
if q_input and "переводчик" in q_input.lower():
    st.markdown('<div class="translator-box">', unsafe_allow_html=True)
    st.markdown("### 🌐 КУСИЦА ПЕРЕВОДЧИК")
    langs = ["Русский", "English", "Deutsch", "Français", "Қазақша", "中文"]
    c1, c2 = st.columns(2)
    with c1:
        lf = st.selectbox("Из", langs, index=0)
        ti = st.text_area("Текст", height=100, key="ti")
    with c2:
        lt = st.selectbox("В", langs, index=1)
        if ti:
            res_t = get_ai_res([{"role":"user", "content":f"Переведи с {lf} на {lt}: {ti}. Выдай только перевод."}])
            st.text_area("Результат", value=res_t, height=100, key="to")
    st.markdown('</div>', unsafe_allow_html=True)

# --- ВЫВОД ---
if state.links:
    t1, t2, t3 = st.tabs(["🔍 Поиск", "🖼️ Картинки", "📺 Видео"])
    with t1:
        if state.ai_history:
            st.markdown(f'<div class="alice-card"><b>🟣 КУСИЦА АССИСТЕНТ</b><br><br>{state.ai_history[0]["content"]}</div>', unsafe_allow_html=True)
            for chat in state.chat_extra:
                st.markdown(f'<div style="background:#f0f2f5; padding:15px; border-radius:15px; margin-top:10px; border-left:4px solid #8e44ad;"><b>Вы:</b> {chat["q"]}<br><b>Кусица:</b> {chat["a"]}</div>', unsafe_allow_html=True)
            u_q = st.text_input("Уточнить запрос...", key="follow_up")
            if st.button("Спросить"):
                if u_q:
                    new_a = get_ai_res([{"role":"assistant","content":state.ai_history[0]["content"]},{"role":"user","content":u_q}])
                    state.chat_extra.append({"q": u_q, "a": new_a}); st.rerun()

        st.write("---")
        for l in state.links:
            dom = urlparse(l['href']).netloc
            fav = f"https://www.google.com/s2/favicons?sz=64&domain_url={dom}"
            st.markdown(f"""
            <div class="result-item">
                <span style="color:green; font-size:13px;">{dom}</span><br>
                <img src="{fav}" class="favicon">
                <a href="{l["href"]}" target="_blank" class="result-title">{l["title"]}</a>
                <div style="font-size:14px; color:#444; margin-top:5px;">{l.get("body","")}</div>
            </div>
            """, unsafe_allow_html=True)

    with t2:
        if state.view_img_idx is not None:
            idx = state.view_img_idx
            img = state.images[idx]
            st.button("⬅️ Назад", on_click=lambda: setattr(state, 'view_img_idx', None))
            st.image(img['image'], use_container_width=True)
            st.subheader(img.get('title',''))
            st.link_button(f"🌐 На сайт", img['url'])
            c1, c2 = st.columns(2)
            with c1: 
                if idx > 0 and st.button("◀️ Назад"): state.view_img_idx -= 1; st.rerun()
            with c2:
                if idx < len(state.images)-1 and st.button("Вперед ▶️"): state.view_img_idx += 1; st.rerun()
        else:
            cols = st.columns(2)
            for i, img in enumerate(state.images):
                with cols[i % 2]:
                    st.markdown(f'<img src="{img["image"]}" class="img-square">', unsafe_allow_html=True)
                    if st.button(f"Увеличить #{i+1}", key=f"z_{i}"): state.view_img_idx = i; st.rerun()

    with t3:
        for v in state.videos:
            st.markdown(f'<div class="video-row"><img src="{v.get("image","https://via.placeholder.com/110")}" class="video-thumb"><div><div style="font-size:16px; font-weight:bold;">{v["title"]}</div><div style="color:green; font-size:12px;">{v.get("source","Видео")}</div><a href="{v["content"]}" target="_blank" style="color:#1a0dab; font-size:14px; font-weight:bold;">▶️ Смотреть</a></div></div>', unsafe_allow_html=True)

else:
    # НОВОСТИ
    st.write("---")
    st.subheader("Главное сегодня в России")
    try:
        with DDGS() as ddgs:
            news = [r for r in ddgs.news("новости России сегодня", region='ru-ru', max_results=6)]
            for n in news:
                st.markdown(f'<div style="padding:10px; border-bottom:1px solid #eee;"><a href="{n.get("url")}" target="_blank" style="color:#000; text-decoration:none;">📰 {n.get("title")}</a></div>', unsafe_allow_html=True)
    except: st.write("Новости загружаются...")

st.markdown("<br><hr><center style='color:#ccc; font-size:10px;'>КУСИЦА 2024</center>", unsafe_allow_html=True)
