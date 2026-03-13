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
    .logo { font-size: 38px; font-weight: 900; letter-spacing: -2px; color: #000; margin-bottom: 5px; }
    .informer-box { display: flex; flex-wrap: wrap; gap: 6px; font-size: 11px; margin-bottom: 15px; }
    .informer-pill { background: #f2f2f4; padding: 4px 10px; border-radius: 10px; display: flex; align-items: center; gap: 4px; color: #555; white-space: nowrap; }
    .currency-red { border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; padding: 2px 8px; border-radius: 8px; }
    .stTextInput > div > div > input { font-size: 18px !important; padding: 18px 22px !important; border-radius: 25px !important; border: 2px solid #ffdb4d !important; }
    .stButton > button { height: 52px; width: 100%; border-radius: 25px; background-color: #ffdb4d !important; color: black !important; font-size: 18px; font-weight: bold; }
    .alice-card { background: #fdfdff; padding: 20px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); border-left: 6px solid #8e44ad; margin-bottom: 20px; font-size: 17px; line-height: 1.5; }
    .result-item { margin-bottom: 25px; border-bottom: 1px solid #f0f0f0; padding-bottom: 15px; }
    .result-title { font-size: 19px; color: #1a0dab; text-decoration: none; font-weight: 500; }
    .result-url { color: #006621; font-size: 13px; display: block; overflow: hidden; text-overflow: ellipsis; }
    .img-box { border: 1px solid #eee; border-radius: 12px; padding: 5px; text-align: center; background: #fff; margin-bottom: 10px; }
    @media (max-width: 640px) { .logo { font-size: 28px; text-align: center; } .informer-box { justify-content: center; } }
    </style>
    """, unsafe_allow_html=True)

# 3. ИНИЦИАЛИЗАЦИЯ ПАМЯТИ
if 'all_links' not in st.session_state: st.session_state.all_links = []
if 'all_images' not in st.session_state: st.session_state.all_images = []
if 'all_videos' not in st.session_state: st.session_state.all_videos = []
if 'ai_answer' not in st.session_state: st.session_state.ai_answer = ""
if 'current_page' not in st.session_state: st.session_state.current_page = 1
if 'last_query' not in st.session_state: st.session_state.last_query = ""
if 'view_img_idx' not in st.session_state: st.session_state.view_img_idx = None

# 4. ФУНКЦИИ API
@st.cache_data(ttl=600)
def get_header_data():
    try:
        tz_m = pytz.timezone('Europe/Moscow')
        w = requests.get("https://wttr.in/Moscow?format=%t", timeout=2).text.strip()
        curr = requests.get("https://open.er-api.com/v6/latest/USD", timeout=2).json()
        return datetime.now(tz_m).strftime("%d.%m"), datetime.now(tz_m).strftime("%H:%M"), w, round(curr['rates']['RUB'], 2)
    except: return "??", "??", "?", "??"

def get_ai_res(q, context):
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role":"system","content":"Ты Кусица. Отвечай подробно."}, {"role":"user","content":f"Вопрос: {q}\nИнфо: {context}"}],
            "temperature": 0.6
        }
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {api_key}"}, json=payload, timeout=20).json()
        return res['choices'][0]['message']['content']
    except: return "Кусица призадумалась..."

# 5. ГЛАВНАЯ ФУНКЦИЯ ПОИСКА (С ПАГИНАЦИЕЙ)
def run_search(query, page=1):
    s_key = st.secrets["SERPER_API_KEY"]
    headers = {'X-API-KEY': s_key, 'Content-Type': 'application/json'}
    
    # Если это новый запрос - чистим память
    if page == 1:
        st.session_state.all_links = []
        st.session_state.all_images = []
        st.session_state.all_videos = []
        st.session_state.current_page = 1
        st.session_state.ai_answer = ""

    with st.spinner(f"Загрузка результатов (страница {page})..."):
        try:
            # Запрос текста
            res_text = requests.post("https://google.serper.dev/search", headers=headers, 
                                   json={"q": query, "hl": "ru", "gl": "ru", "page": page}).json()
            # Запрос картинок
            res_img = requests.post("https://google.serper.dev/images", headers=headers, 
                                  json={"q": query, "page": page}).json()
            # Запрос видео
            res_vid = requests.post("https://google.serper.dev/videos", headers=headers, 
                                  json={"q": query, "page": page}).json()

            # Добавляем данные в общий список
            st.session_state.all_links.extend(res_text.get('organic', []))
            st.session_state.all_images.extend(res_img.get('images', []))
            st.session_state.all_videos.extend(res_vid.get('videos', []))
            
            # Генерируем ИИ ответ только для первой страницы
            if page == 1:
                ctx = "\n".join([l.get('snippet','') for l in res_text.get('organic', [])[:3]])
                st.session_state.ai_answer = get_ai_res(query, ctx)
                
            st.session_state.last_query = query
            st.session_state.current_page = page
        except Exception as e:
            st.error(f"Ошибка сети: {e}")

# --- ШАПКА ---
d, tm, w, usd_r = get_header_data()
st.markdown(f'<div class="logo">КУСИЦА</div>', unsafe_allow_html=True)
st.markdown(f'<div class="informer-box"><div class="informer-pill">📅 {d}</div><div class="informer-pill">🕒 МСК {tm}</div><div class="informer-pill">🌡️ {w}</div><div class="currency-red">USD {usd_r}₽</div></div>', unsafe_allow_html=True)

# --- ПОИСК ---
url_q = st.query_params.get("q")
q_input = st.text_input("", value=url_q if url_q and not st.session_state.last_query else "", placeholder="Найдётся всё...", key="main_search", label_visibility="collapsed")

if st.button("Найти ➔") or (q_input and q_input != st.session_state.last_query) or (url_q and not st.session_state.last_query):
    query_to_use = q_input if q_input else url_q
    run_search(query_to_use, page=1)

# --- ВЫВОД РЕЗУЛЬТАТОВ ---
if st.session_state.all_links:
    t1, t2, t3 = st.tabs(["🔍 Поиск", "🖼️ Картинки", "📺 Видео"])
    
    with t1:
        st.markdown(f'<div class="alice-card"><b>🟣 КУСИЦА:</b><br><br>{st.session_state.ai_answer}</div>', unsafe_allow_html=True)
        for l in st.session_state.all_links:
            st.markdown(f"""<div class="result-item">
                <a class="result-title" href="{l['link']}" target="_blank">{l['title']}</a>
                <span class="result-url">{l['link']}</span>
                <div style="font-size:14px; color:#444; margin-top:5px;">{l.get('snippet','')}</div>
            </div>""", unsafe_allow_html=True)
        
        if st.button("Показать еще ссылки ⬇️"):
            run_search(st.session_state.last_query, page=st.session_state.current_page + 1)
            st.rerun()

    with t2:
        if st.session_state.view_img_idx is not None:
            idx = st.session_state.view_img_idx
            img = st.session_state.all_images[idx]
            st.button("⬅️ Назад", on_click=lambda: setattr(st.session_state, 'view_img_idx', None))
            st.image(img['imageUrl'], use_container_width=True)
            st.subheader(img.get('title',''))
            st.link_button(f"🌐 Перейти на {img.get('source','сайт')}", img['link'])
            if st.button("📩 Отправить в Мессенджер"): st.info(f"Ссылка скопирована: {img['imageUrl']}")
            c1, c2 = st.columns(2)
            with c1: 
                if idx > 0 and st.button("◀️ Назад"): st.session_state.view_img_idx -= 1; st.rerun()
            with c2:
                if idx < len(st.session_state.all_images)-1 and st.button("Вперед ▶️"): st.session_state.view_img_idx += 1; st.rerun()
        else:
            cols = st.columns(2)
            for i, img in enumerate(st.session_state.all_images):
                with cols[i % 2]:
                    st.markdown(f'<div class="img-box"><img src="{img["imageUrl"]}" style="width:100%; border-radius:10px;"></div>', unsafe_allow_html=True)
                    if st.button(f"Увеличить #{i+1}", key=f"z_{i}"):
                        st.session_state.view_img_idx = i
                        st.rerun()
            if st.button("Загрузить еще картинки 🖼️"):
                run_search(st.session_state.last_query, page=st.session_state.current_page + 1)
                st.rerun()

    with t3:
        for v in st.session_state.all_videos:
            st.markdown(f"""<div style="background:#f9f9f9; padding:10px; border-radius:15px; margin-bottom:15px;">
                <b>{v['title']}</b><br><a href="{v['link']}" target="_blank">▶️ Смотреть видео</a>
            </div>""", unsafe_allow_html=True)
        if st.button("Больше видео 📺"):
            run_search(st.session_state.last_query, page=st.session_state.current_page + 1)
            st.rerun()

else:
    # Главная страница (новости)
    st.write("---")
    st.subheader("Главное сегодня")
    try:
        n_res = requests.post("https://google.serper.dev/news", headers={'X-API-KEY': st.secrets["SERPER_API_KEY"]}, json={"q": "новости сегодня", "hl": "ru"}).json()
        for n in n_res.get('news', [])[:5]:
            st.markdown(f"📰 [{n['title']}]({n['link']})")
    except: st.write("Загрузка новостей...")

st.markdown("<br><hr><center style='color:#ccc; font-size:10px;'>КУСИЦА • 2024</center>", unsafe_allow_html=True)
