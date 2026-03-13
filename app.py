import streamlit as st
import requests
import uuid
import pytz
import re
import math
from datetime import datetime
from urllib.parse import urlparse
import streamlit.components.v1 as components

# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ
st.set_page_config(page_title="КУСИЦА — Super App", page_icon="🔍", layout="wide")

# 2. УЛЬТРА CSS (Яндекс-стайл)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #fff; }
    .logo { font-size: 38px; font-weight: 900; letter-spacing: -2.5px; color: #000; margin-bottom: 5px; }
    .informer-pill { background: #f2f2f4; padding: 4px 12px; border-radius: 12px; font-size: 11px; color: #555; }
    .currency-red { border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; padding: 2px 10px; border-radius: 10px; }
    
    /* Поиск */
    .stTextInput > div > div > input { font-size: 18px !important; padding: 20px 25px !important; border-radius: 30px !important; border: 2px solid #ffdb4d !important; }
    .stButton > button { height: 50px; width: 100%; border-radius: 25px; background-color: #ffdb4d !important; color: black !important; font-size: 18px; font-weight: bold; border: none !important; }
    
    /* Карточки результатов */
    .result-item { margin-bottom: 25px; border-bottom: 1px solid #f0f0f0; padding-bottom: 15px; }
    .result-domain { color: #006621; font-size: 13px; margin-bottom: 2px; display: block; }
    .result-title { font-size: 19px; color: #1a0dab; text-decoration: none; font-weight: 500; }
    .result-title:hover { text-decoration: underline; }
    
    .alice-card { background: #fdfdff; padding: 25px; border-radius: 22px; box-shadow: 0 10px 40px rgba(0,0,0,0.05); border-left: 6px solid #8e44ad; margin-top: 15px; line-height: 1.6; font-size: 18px; }
    .img-box { border: 1px solid #eee; border-radius: 12px; padding: 5px; text-align: center; background: #fff; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 3. ИНИЦИАЛИЗАЦИЯ ПАМЯТИ
state = st.session_state
if 'links' not in state: state.links = []
if 'images' not in state: state.images = []
if 'videos' not in state: state.videos = []
if 'page' not in state: state.page = 1
if 'ai_ans' not in state: state.ai_ans = ""
if 'last_q' not in state: state.last_q = ""

# 4. ФУНКЦИИ API
def get_ai(q, ctx):
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role":"system","content":"Ты Кусица. Отвечай подробно."}, {"role":"user","content":f"Вопрос: {q}\nДанные: {ctx}"}],
            "temperature": 0.6
        }
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {api_key}"}, json=payload, timeout=20).json()
        return res['choices'][0]['message']['content']
    except: return "Кусица призадумалась..."

def run_full_search(q, p=1):
    s_key = st.secrets["SERPER_API_KEY"]
    h = {'X-API-KEY': s_key, 'Content-Type': 'application/json'}
    if p == 1:
        state.links, state.images, state.videos, state.page = [], [], [], 1
    
    with st.spinner("КУСИЦА ищет..."):
        try:
            # Текст
            r_t = requests.post("https://google.serper.dev/search", headers=h, json={"q": q, "hl": "ru", "page": p}).json()
            state.links.extend(r_t.get('organic', []))
            # Картинки
            r_i = requests.post("https://google.serper.dev/images", headers=h, json={"q": q, "page": p}).json()
            state.images.extend(r_i.get('images', []))
            # Видео
            r_v = requests.post("https://google.serper.dev/videos", headers=h, json={"q": q, "page": p}).json()
            state.videos.extend(r_v.get('videos', []))
            
            if p == 1:
                context = "\n".join([l.get('snippet','') for l in state.links[:3]])
                state.ai_ans = get_ai(q, context)
            
            state.last_q = q
            state.page = p
        except: st.error("Ошибка API")

# --- ШАПКА (Информеры) ---
col_l, col_i = st.columns([1, 4])
with col_l: st.markdown('<div class="logo">КУСИЦА</div>', unsafe_allow_html=True)
with col_i:
    try:
        w = requests.get("https://wttr.in/Moscow?format=%t", timeout=2).text.strip()
        c = requests.get("https://open.er-api.com/v6/latest/USD", timeout=2).json()
        u_r = round(c['rates']['RUB'], 2)
        st.markdown(f'<div style="display:flex; gap:10px;"><div class="informer-pill">🌡️ {w}</div><div class="currency-red">USD {u_r}₽</div></div>', unsafe_allow_html=True)
    except: pass

# --- ПОИСК ---
q_input = st.text_input("", placeholder="Найдётся всё...", key="main_search", label_visibility="collapsed")
if st.button("Найти ➔") or (q_input and q_input != state.last_q):
    run_full_search(q_input, 1)

# --- ВЫВОД ---
if state.links:
    t1, t2, t3 = st.tabs(["🔍 Поиск", "🖼️ Картинки", "📺 Видео"])
    
    with t1:
        # ОТВЕТ ИИ С ОЗВУЧКОЙ
        st.markdown(f'<div class="alice-card"><b>🟣 КУСИЦА:</b><br><br>{state.ai_ans}</div>', unsafe_allow_html=True)
        
        # Надежный JS компонент для озвучки
        tts_code = f"""
        <button onclick="speak()" style="background:#8e44ad; color:white; border:none; padding:10px 20px; border-radius:15px; cursor:pointer; font-weight:bold;">🔊 Озвучить ответ</button>
        <script>
        function speak() {{
            window.speechSynthesis.cancel();
            const msg = new SpeechSynthesisUtterance("{state.ai_ans.replace('"', '').replace('\\', '').replace('\\n', ' ')}");
            msg.lang = 'ru-RU';
            window.speechSynthesis.speak(msg);
        }}
        </script>
        """
        components.html(tts_code, height=60)

        st.write("---")
        # Список ссылок
        for l in state.links:
            domain = urlparse(l['link']).netloc
            st.markdown(f"""
            <div class="result-item">
                <span class="result-domain">{domain}</span>
                <a class="result-title" href="{l['link']}" target="_blank">{l['title']}</a>
                <div style="font-size:14px; color:#444; margin-top:5px;">{l.get('snippet','')}</div>
            </div>
            """, unsafe_allow_html=True)
        
        if st.button("Показать еще ссылки"):
            run_full_search(state.last_query, state.page + 1)
            st.rerun()

    with t2:
        cols = st.columns(2)
        for i, img in enumerate(state.images):
            with cols[i % 2]:
                st.markdown(f"""
                <div class="img-box">
                    <img src="{img['imageUrl']}" style="width:100%; border-radius:10px; height:150px; object-fit:cover;">
                    <div style="font-size:12px; font-weight:bold; margin-top:5px;">{img.get('title','')[:30]}...</div>
                    <a href="{img['link']}" target="_blank" style="font-size:11px; color:green;">{img.get('source','Перейти')}</a>
                </div>
                """, unsafe_allow_html=True)
        
        if st.button("Загрузить еще картинки"):
            run_full_search(state.last_query, state.page + 1)
            st.rerun()

    with t3:
        for v in state.videos:
            st.markdown(f"""
            <div style="background:#f9f9f9; padding:15px; border-radius:15px; margin-bottom:15px; border:1px solid #eee;">
                <b>{v['title']}</b><br>
                <small>{v.get('source','YouTube')}</small><br>
                <a href="{v['link']}" target="_blank">▶️ Смотреть видео</a>
            </div>
            """, unsafe_allow_html=True)
        
        if st.button("Больше видео"):
            run_full_search(state.last_query, state.page + 1)
            st.rerun()

else:
    # НОВОСТИ (Главная)
    st.write("---")
    st.subheader("Главное сегодня")
    try:
        n_res = requests.post("https://google.serper.dev/news", headers={'X-API-KEY': st.secrets["SERPER_API_KEY"]}, json={"q": "новости России", "hl": "ru"}).json()
        for n in n_res.get('news', [])[:5]:
            st.markdown(f"📰 [{n['title']}]({n['link']})")
    except: pass

st.markdown("<br><hr><center style='color:#ccc; font-size:10px;'>КУСИЦА 2024</center>", unsafe_allow_html=True)
