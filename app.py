import streamlit as st
import requests
import uuid
import pytz
import re
from datetime import datetime
from urllib.parse import urlparse
import streamlit.components.v1 as components

# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ
st.set_page_config(page_title="КУСИЦА — Супер Портал", page_icon="🔍", layout="wide")

# 2. УЛЬТРА CSS (Яндекс-стайл 2024)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #fff; }
    .logo { font-size: 38px; font-weight: 900; letter-spacing: -2.5px; color: #000; margin-bottom: 5px; }
    
    /* Информеры */
    .informer-pill { background: #f2f2f4; padding: 4px 12px; border-radius: 12px; font-size: 12px; color: #555; white-space: nowrap; }
    .currency-red { border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; padding: 2px 10px; border-radius: 10px; }
    
    /* Поиск */
    .stTextInput > div > div > input { font-size: 18px !important; padding: 22px 25px !important; border-radius: 30px !important; border: 2.5px solid #ffdb4d !important; }
    .stButton > button { height: 55px; width: 100%; border-radius: 25px; background-color: #ffdb4d !important; color: black !important; font-size: 18px; font-weight: bold; }
    
    /* Ссылки */
    .result-item { margin-bottom: 25px; padding: 10px; border-radius: 15px; transition: 0.2s; }
    .result-item:hover { background: #f9f9f9; }
    .result-domain { color: #006621; font-size: 14px; margin-bottom: 2px; font-weight: 500; }
    .result-title { font-size: 20px; color: #1a0dab; text-decoration: none; font-weight: 500; display: block; }
    .result-snippet { color: #444; font-size: 15px; margin-top: 5px; line-height: 1.5; }
    
    /* Карточка Алисы */
    .alice-card { background: #fdfdff; padding: 25px; border-radius: 25px; box-shadow: 0 10px 40px rgba(0,0,0,0.05); border-left: 8px solid #8e44ad; margin-bottom: 20px; }
    
    /* Видео и Картинки */
    .video-card { background: #fff; border-radius: 20px; border: 1px solid #eee; overflow: hidden; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.03); }
    .img-box { border-radius: 15px; overflow: hidden; border: 1px solid #eee; margin-bottom: 10px; background: #fff; cursor: pointer; }
    
    /* Мобильность */
    @media (max-width: 640px) {
        .logo { font-size: 30px; text-align: center; }
        .informer-box { justify-content: center; }
    }
    </style>
    """, unsafe_allow_html=True)

# 3. ИНИЦИАЛИЗАЦИЯ ПАМЯТИ
state = st.session_state
if 'links' not in state: state.links = []
if 'images' not in state: state.images = []
if 'videos' not in state: state.videos = []
if 'ai_history' not in state: state.ai_history = [] # История чата
if 'page' not in state: state.page = 1
if 'last_q' not in state: state.last_q = ""
if 'view_img_idx' not in state: state.view_img_idx = None

# 4. ФУНКЦИИ API
def get_ai_response(msgs):
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {"model": "llama-3.1-8b-instant", "messages": msgs, "temperature": 0.7}
        res = requests.post(url, headers={"Authorization": f"Bearer {api_key}"}, json=payload, timeout=20).json()
        return res['choices'][0]['message']['content']
    except: return "Кусица задумалась. Попробуй еще раз."

def perform_search(q, p=1):
    s_key = st.secrets["SERPER_API_KEY"]
    h = {'X-API-KEY': s_key, 'Content-Type': 'application/json'}
    if p == 1:
        state.links, state.images, state.videos, state.page, state.ai_history = [], [], [], 1, []
    
    with st.spinner(" "):
        try:
            # Текст (hl=ru, gl=ru для поиска по России)
            r_t = requests.post("https://google.serper.dev/search", headers=h, json={"q": q, "hl": "ru", "gl": "ru", "page": p}).json()
            state.links.extend(r_t.get('organic', []))
            # Картинки
            r_i = requests.post("https://google.serper.dev/images", headers=h, json={"q": q, "page": p}).json()
            state.images.extend(r_i.get('images', []))
            # Видео
            r_v = requests.post("https://google.serper.dev/videos", headers=h, json={"q": q, "page": p}).json()
            state.videos.extend(r_v.get('videos', []))
            
            if p == 1:
                ctx = "\n".join([l.get('snippet','') for l in state.links[:3]])
                ans = get_ai_response([{"role":"system","content":"Ты Кусица. Отвечай подробно."}, {"role":"user","content":f"Вопрос: {q}\nДанные: {ctx}"}])
                state.ai_history.append({"role": "assistant", "content": ans})
            
            state.last_q = q
            state.page = p
        except: st.error("Ошибка поиска")

# --- ШАПКА (Информеры) ---
col_l, col_i = st.columns([1, 4])
with col_l: st.markdown('<div class="logo">КУСИЦА</div>', unsafe_allow_html=True)
with col_i:
    try:
        w = requests.get("https://wttr.in/Moscow?format=%t", timeout=2).text.strip()
        c = requests.get("https://open.er-api.com/v6/latest/USD", timeout=2).json()
        st.markdown(f'<div style="display:flex; gap:10px;"><div class="informer-pill">🌡️ МСК {w}</div><div class="currency-red">USD {round(c["rates"]["RUB"], 2)}₽</div></div>', unsafe_allow_html=True)
    except: pass

# --- ПОИСК ---
q_input = st.text_input("", placeholder="Найдётся всё...", key="main_search", label_visibility="collapsed")
if st.button("Найти ответ ➔") or (q_input and q_input != state.last_q):
    perform_search(q_input, 1)

# --- ВЫВОД ---
if state.links:
    t1, t2, t3 = st.tabs(["🔍 Поиск", "🖼️ Картинки", "📺 Видео"])
    
    with t1:
        # Ответ ИИ и ЧАТ
        st.markdown(f'<div class="alice-card"><b>🟣 КУСИЦА АССИСТЕНТ</b><br><br>{state.ai_history[0]["content"]}</div>', unsafe_allow_html=True)
        
        # Уточнение (Диалог)
        with st.expander("💬 Уточнить ответ у Кусицы"):
            u_q = st.text_input("Ваш вопрос...")
            if u_q:
                with st.spinner(" "):
                    chat_ans = get_ai_response([{"role":"assistant", "content":state.ai_history[0]["content"]}, {"role":"user", "content":u_q}])
                    st.write(f"**Ответ:** {chat_ans}")

        st.write("---")
        # Список ссылок (tutu.ru style)
        for l in state.links:
            domain = urlparse(l['link']).netloc
            st.markdown(f"""
            <div class="result-item">
                <span class="result-domain">{domain}</span>
                <a class="result-title" href="{l['link']}" target="_blank">{l['title']}</a>
                <div class="result-snippet">{l.get('snippet','')}</div>
            </div>
            """, unsafe_allow_html=True)
        
        if st.button("Показать еще результаты ⬇️"):
            perform_search(state.last_q, state.page + 1)
            st.rerun()

    with t2:
        # КАРТИНКИ С ZOOM
        if state.view_img_idx is not None:
            idx = state.view_img_idx
            img = state.images[idx]
            st.button("⬅️ Назад к сетке", on_click=lambda: setattr(state, 'view_img_idx', None))
            st.image(img['imageUrl'], use_container_width=True)
            st.subheader(img.get('title',''))
            st.link_button(f"🌐 Перейти на {img.get('source','сайт')}", img['link'])
            
            c1, c2 = st.columns(2)
            with c1: 
                if idx > 0 and st.button("◀️ Назад"): state.view_img_idx -= 1; st.rerun()
            with c2:
                if idx < len(state.images)-1 and st.button("Вперед ▶️"): state.view_img_idx += 1; st.rerun()
        else:
            cols = st.columns(2) # 2 колонки для мобилок
            for i, img in enumerate(state.images):
                with cols[i % 2]:
                    st.markdown(f'<div class="img-box"><img src="{img["imageUrl"]}" style="width:100%; border-radius:10px; height:180px; object-fit:cover;"></div>', unsafe_allow_html=True)
                    if st.button(f"Увеличить #{i+1}", key=f"z_{i}"):
                        state.view_img_idx = i
                        st.rerun()
            if st.button("Больше картинок 🖼️"):
                perform_search(state.last_q, state.page + 1)
                st.rerun()

    with t3:
        # ВИДЕО С ПРЕВЬЮ
        for v in state.videos:
            st.markdown(f"""
            <div class="video-card">
                <img src="{v.get('imageUrl','')}" style="width:100%; height:200px; object-fit:cover;">
                <div style="padding:15px;">
                    <div style="font-size:18px; font-weight:bold; margin-bottom:5px;">{v['title']}</div>
                    <div style="color:green; font-size:13px; margin-bottom:10px;">Источник: {v.get('source','YouTube')}</div>
                    <a href="{v['link']}" target="_blank" style="background:#ffdb4d; color:black; padding:8px 20px; border-radius:10px; text-decoration:none; font-weight:bold;">▶️ Смотреть</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        if st.button("Больше видео 📺"):
            perform_search(state.last_q, state.page + 1)
            st.rerun()

else:
    # ГЛАВНАЯ
    st.write("---")
    st.subheader("Главное сегодня")
    try:
        n_res = requests.post("https://google.serper.dev/news", headers={'X-API-KEY': st.secrets["SERPER_API_KEY"]}, json={"q": "новости России сегодня", "hl": "ru", "gl": "ru"}).json()
        for n in n_res.get('news', [])[:5]:
            st.markdown(f"📰 [{n['title']}]({n['link']})")
    except: pass

st.markdown("<br><hr><center style='color:#ccc; font-size:10px;'>КУСИЦА 2024</center>", unsafe_allow_html=True)
