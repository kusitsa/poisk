import streamlit as st
import requests
import uuid
import pytz
import re
from datetime import datetime
from urllib.parse import urlparse
import streamlit.components.v1 as components

# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ
st.set_page_config(page_title="КУСИЦА — Поисковая Система", page_icon="🔍", layout="wide")

# 2. УЛЬТРА CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #fff; }
    .logo { font-size: 38px; font-weight: 900; letter-spacing: -2.5px; color: #000; margin-bottom: 5px; }
    
    /* Информеры */
    .informer-pill { background: #f2f2f4; padding: 4px 12px; border-radius: 12px; font-size: 11px; color: #555; white-space: nowrap; }
    .currency-red { border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; padding: 2px 10px; border-radius: 10px; }
    
    /* Поиск */
    .stTextInput > div > div > input { font-size: 18px !important; padding: 22px 25px !important; border-radius: 30px !important; border: 2px solid #ffdb4d !important; }
    .stButton > button { height: 50px; width: 100%; border-radius: 25px; background-color: #ffdb4d !important; color: black !important; font-size: 18px; font-weight: bold; }
    
    /* Фавиконки и Ссылки */
    .favicon { width: 18px; height: 18px; vertical-align: middle; margin-right: 8px; border-radius: 3px; }
    .result-item { margin-bottom: 25px; padding: 10px; border-radius: 15px; }
    .result-title { font-size: 20px; color: #1a0dab; text-decoration: none; font-weight: 500; display: inline-block; vertical-align: middle; }
    
    /* Квадратные превью */
    .img-square { width: 100%; aspect-ratio: 1 / 1; object-fit: cover; border-radius: 15px; border: 1px solid #eee; background: #f9f9f9; }
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
    except: return "Кусица задумалась..."

def perform_search(q, p=1):
    if not q: return
    s_key = st.secrets["SERPER_API_KEY"]
    h = {'X-API-KEY': s_key, 'Content-Type': 'application/json'}
    
    if p == 1:
        state.links, state.images, state.videos, state.page, state.ai_history = [], [], [], 1, []
    
    try:
        # 1. Текст (РФ)
        r_t = requests.post("https://google.serper.dev/search", headers=h, json={"q": q, "hl": "ru", "gl": "ru", "page": p}).json()
        state.links.extend(r_t.get('organic', []))
        
        # 2. Картинки (РФ)
        r_i = requests.post("https://google.serper.dev/images", headers=h, json={"q": q, "hl": "ru", "gl": "ru", "page": p}).json()
        state.images.extend(r_i.get('images', []))
        
        # 3. Видео (Усиление RU сегмента: RuTube, VK, Dzen)
        video_query = f"{q} site:rutube.ru OR site:vk.com OR site:dzen.ru OR site:ok.ru"
        r_v = requests.post("https://google.serper.dev/videos", headers=h, json={"q": video_query, "hl": "ru", "gl": "ru", "page": p}).json()
        state.videos.extend(r_v.get('videos', []))
        
        if p == 1:
            ctx = "\n".join([l.get('snippet','') for l in state.links[:3]])
            ans = get_ai_res([{"role":"system","content":"Ты Кусица. Отвечай подробно."}, {"role":"user","content":f"Вопрос: {q}\nИнфо: {ctx}"}])
            state.ai_history.append({"role": "assistant", "content": ans})
        
        state.last_q, state.page = q, p
    except: st.error("Ошибка сети")

# --- ШАПКА ---
col_l, col_i = st.columns([1, 4])
with col_l: st.markdown('<div class="logo">КУСИЦА</div>', unsafe_allow_html=True)
with col_i:
    try:
        w = requests.get("https://wttr.in/Moscow?format=%t", timeout=2).text.strip()
        c = requests.get("https://open.er-api.com/v6/latest/USD", timeout=2).json()
        st.markdown(f'<div style="display:flex; gap:10px;"><div class="informer-pill">🌡️ МСК {w}</div><div class="currency-red">USD {round(c["rates"]["RUB"], 2)}₽</div></div>', unsafe_allow_html=True)
    except: pass

# --- URL ПОИСК (?q=...) ---
url_query = st.query_params.get("q")
if url_query and state.last_q != url_query: perform_search(url_query, 1)

# --- СТРОКА ПОИСКА ---
q_input = st.text_input("", value=url_query if url_query and not state.last_q else "", placeholder="Найдётся всё...", key="main_search", label_visibility="collapsed")
if st.button("Найти ответ ➔") or (q_input and q_input != state.last_q):
    perform_search(q_input, 1)

# --- ВЫВОД ---
if state.links:
    t1, t2, t3 = st.tabs(["🔍 Поиск", "🖼️ Картинки", "📺 Видео"])
    
    with t1:
        st.markdown(f'<div class="alice-card"><b>🟣 КУСИЦА АССИСТЕНТ</b><br><br>{state.ai_history[0]["content"]}</div>', unsafe_allow_html=True)
        st.write("---")
        for l in state.links:
            domain = urlparse(l['link']).netloc
            favicon = f"https://www.google.com/s2/favicons?sz=64&domain_url={domain}"
            st.markdown(f"""
            <div class="result-item">
                <span style="color:green; font-size:13px;">{domain}</span><br>
                <img src="{favicon}" class="favicon">
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
            st.link_button(f"🌐 На сайт {img.get('source','')}", img['link'])
            c1, c2 = st.columns(2)
            with c1: 
                if idx > 0 and st.button("◀️ Назад"): state.view_img_idx -= 1; st.rerun()
            with c2:
                if idx < len(state.images)-1 and st.button("Вперед ▶️"): state.view_img_idx += 1; st.rerun()
        else:
            cols = st.columns(2)
            for i, img in enumerate(state.images):
                with cols[i % 2]:
                    st.markdown(f'<img src="{img["imageUrl"]}" class="img-square">', unsafe_allow_html=True)
                    if st.button(f"Увеличить #{i+1}", key=f"z_{i}"):
                        state.view_img_idx = i; st.rerun()
            if st.button("Больше картинок"): perform_search(state.last_q, state.page + 1); st.rerun()

    with t3:
        if not state.videos: st.write("Видео из РФ не найдены. Попробуйте другой запрос.")
        for v in state.videos:
            st.markdown(f"""
            <div class="video-row">
                <img src="{v.get('imageUrl','https://via.placeholder.com/100')}" class="video-thumb">
                <div>
                    <div style="font-size:16px; font-weight:bold; color:#000;">{v['title']}</div>
                    <div style="color:green; font-size:12px; margin: 3px 0;">{v.get('source','Видео')}</div>
                    <a href="{v['link']}" target="_blank" style="color:#1a0dab; font-size:14px; font-weight:bold; text-decoration:none;">▶️ Смотреть на {v.get('source','сайте')}</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
        if st.button("Больше видео"): perform_search(state.last_q, state.page + 1); st.rerun()

else:
    # ГЛАВНАЯ (НОВОСТИ)
    st.write("---")
    st.subheader("Главное сегодня")
    try:
        n_res = requests.post("https://google.serper.dev/news", headers={'X-API-KEY': st.secrets["SERPER_API_KEY"]}, json={"q": "новости России сегодня", "hl": "ru", "gl": "ru"}).json()
        for n in n_res.get('news', [])[:5]:
            st.markdown(f"📰 [{n['title']}]({n['link']})")
    except: pass

st.markdown("<br><hr><center style='color:#ccc; font-size:10px;'>КУСИЦА 2024</center>", unsafe_allow_html=True)
