import streamlit as st
import requests
import uuid
import pytz
import re
import math
from datetime import datetime
import streamlit.components.v1 as components

# 1. НАСТРОЙКА СТРАНИЦЫ
st.set_page_config(page_title="КУСИЦА — Супер Портал", page_icon="🔍", layout="wide")

# 2. УЛЬТРА CSS (Яндекс-стайл + Виджеты)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #fff; }
    .logo { font-size: 38px; font-weight: 900; letter-spacing: -2.5px; color: #000; margin-bottom: 5px; }
    .informer-pill { background: #f2f2f4; padding: 4px 12px; border-radius: 12px; font-size: 11px; color: #555; }
    .currency-red { border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; padding: 2px 10px; border-radius: 10px; }
    
    /* Стили калькулятора */
    .calc-button { width: 100%; height: 50px; border-radius: 10px; border: 1px solid #ddd; background: #f8f9fa; font-weight: bold; }
    .calc-display { background: #000; color: #0f0; padding: 15px; border-radius: 10px; font-family: monospace; font-size: 24px; text-align: right; margin-bottom: 10px; }
    
    /* Стили переводчика */
    .trans-box { border: 2px solid #ffdb4d; border-radius: 20px; padding: 15px; background: #fff; }
    
    /* Кнопки поиска */
    .stTextInput > div > div > input { font-size: 18px !important; padding: 20px 25px !important; border-radius: 30px !important; border: 2px solid #ffdb4d !important; }
    .stButton > button { height: 60px; width: 100%; border-radius: 30px; background-color: #ffdb4d !important; color: black !important; font-size: 20px; font-weight: bold; border: none !important; }
    .alice-card { background: #fdfdff; padding: 25px; border-radius: 22px; box-shadow: 0 10px 40px rgba(0,0,0,0.05); border-left: 6px solid #8e44ad; margin-top: 15px; line-height: 1.6; font-size: 18px; }
    </style>
    """, unsafe_allow_html=True)

# 3. ПАМЯТЬ
state = st.session_state
if 'calc_val' not in state: state.calc_val = ""
if 'all_links' not in state: state.all_links = []
if 'all_images' not in state: state.all_images = []
if 'ai_answer' not in state: state.ai_answer = ""
if 'last_q' not in state: state.last_q = ""
if 'page' not in state: state.page = 1

# 4. ФУНКЦИИ API
def get_ai(msgs):
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        payload = {"model": "llama-3.1-8b-instant", "messages": msgs, "temperature": 0.6}
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {api_key}"}, json=payload, timeout=20).json()
        return res['choices'][0]['message']['content']
    except: return "Кусица задумалась..."

@st.cache_data(ttl=600)
def get_meta():
    try:
        w = requests.get("https://wttr.in/Moscow?format=%t", timeout=2).text.strip()
        c = requests.get("https://open.er-api.com/v6/latest/USD", timeout=2).json()
        return datetime.now(pytz.timezone('Europe/Moscow')).strftime("%d.%m %H:%M"), w, round(c['rates']['RUB'], 2)
    except: return "??.??", "?", "??"

def fetch_news():
    try:
        r = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': st.secrets["SERPER_API_KEY"]}, json={"q": "новости России сегодня", "hl": "ru"}).json()
        return r.get('organic', [])[:5]
    except: return []

# 5. ВИДЖЕТЫ (КАЛЬКУЛЯТОР И ПЕРЕВОДЧИК)
def show_calculator():
    st.markdown("### 🧮 Кусица Калькулятор")
    mode = st.toggle("Научный режим", key="calc_mode")
    st.markdown(f'<div class="calc-display">{state.calc_val if state.calc_val else "0"}</div>', unsafe_allow_html=True)
    
    cols = st.columns(4)
    btns = ['7','8','9','/','4','5','6','*','1','2','3','-','0','.','C','+']
    if mode: btns += ['sin','cos','sqrt','**','log','tan','(',')','abs','pi']
    
    for i, b in enumerate(btns):
        with cols[i % 4]:
            if st.button(b, key=f"btn_{b}"):
                if b == 'C': state.calc_val = ""
                else: state.calc_val += b
                st.rerun()
    if st.button("=", use_container_width=True):
        try:
            # Безопасное вычисление
            safe_dict = {"math": math, "sin": math.sin, "cos": math.cos, "sqrt": math.sqrt, "log": math.log, "tan": math.tan, "pi": math.pi, "abs": abs}
            state.calc_val = str(eval(state.calc_val, {"__builtins__": None}, safe_dict))
        except: state.calc_val = "Ошибка"
        st.rerun()

def show_translator():
    st.markdown("### 🌐 Кусица Переводчик")
    langs = ["Русский", "English", "Deutsch", "Français", "Español", "中文", "日本語", "Қазақша"]
    col1, col2 = st.columns(2)
    with col1:
        src_l = st.selectbox("С языка", langs, index=0)
        text_in = st.text_area("Текст для перевода", height=150)
    with col2:
        tar_l = st.selectbox("На язык", langs, index=1)
        if text_in:
            with st.spinner("Перевожу..."):
                res = get_ai([{"role":"user", "content": f"Переведи с {src_l} на {tar_l}: {text_in}"}])
                st.text_area("Результат", value=res, height=150)

# --- ШАПКА ---
meta_t, meta_w, meta_u = get_meta()
col_logo, col_info = st.columns([1, 4])
with col_logo: st.markdown('<div class="logo">КУСИЦА</div>', unsafe_allow_html=True)
with col_info:
    st.markdown(f'<div style="display:flex; gap:10px;"><div class="informer-pill">📅 {meta_t}</div><div class="informer-pill">🌡️ МСК {meta_w}</div><div class="currency-red">USD {meta_u}₽</div></div>', unsafe_allow_html=True)

# --- ПОИСК ---
url_q = st.query_params.get("q", "")
q = st.text_input("", value=url_q if url_q and not state.last_q else "", placeholder="Найдётся всё...", key="main_search", label_visibility="collapsed")
btn = st.button("Найти ответ ➔")

# --- ЛОГИКА ПОИСКА ---
if (btn or q) and q:
    q_low = q.lower()
    if "калькулятор" in q_low:
        show_calculator()
    elif "переводчик" in q_low:
        show_translator()
    else:
        if state.last_q != q:
            with st.spinner(" "):
                try:
                    s_key = st.secrets["SERPER_API_KEY"]
                    res_t = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': s_key}, json={"q": q, "hl": "ru"}).json()
                    res_i = requests.post("https://google.serper.dev/images", headers={'X-API-KEY': s_key}, json={"q": q}).json()
                    res_v = requests.post("https://google.serper.dev/videos", headers={'X-API-KEY': s_key}, json={"q": q}).json()
                    
                    state.all_links = res_t.get('organic', [])
                    state.all_images = res_i.get('images', [])
                    state.all_videos = res_v.get('videos', [])
                    
                    ctx = "\n".join([l.get('snippet','') for l in state.all_links[:3]])
                    state.ai_answer = get_ai([{"role":"system","content":"Ты Кусица, эрудированный ассистент. Отвечай подробно."}, {"role":"user","content":f"Вопрос: {q}\nДанные: {ctx}"}])
                    state.last_q = q
                except: st.error("Ошибка сети")

        # --- ВЫВОД РЕЗУЛЬТАТОВ ---
        if state.all_links:
            t1, t2, t3 = st.tabs(["🔍 Поиск", "🖼️ Картинки", "📺 Видео"])
            with t1:
                st.markdown(f'<div class="alice-card"><b>🟣 КУСИЦА:</b><br><br>{state.ai_answer}</div>', unsafe_allow_html=True)
                for l in state.all_links[:10]:
                    st.markdown(f'<div><a href="{l["link"]}" target="_blank" style="font-size:18px; font-weight:bold; color:#1a0dab;">{l["title"]}</a><br><small style="color:green;">{l["link"][:70]}</small><p>{l.get("snippet","")}</p></div>', unsafe_allow_html=True)
            with t2:
                cols = st.columns(2)
                for i, img in enumerate(state.all_images[:12]):
                    with cols[i % 2]:
                        st.image(img['imageUrl'])
                        st.caption(f"[{img.get('source','Источник')}]({img['link']})")
                        if st.button("📩 В Мессенджер", key=f"msg_{i}"): st.code(img['imageUrl'])
            with t3:
                for v in state.all_videos[:5]:
                    st.markdown(f"**[{v['title']}]({v['link']})**")
                    st.image(v.get('imageUrl', ''))
else:
    # ГЛАВНАЯ
    st.write("---")
    st.subheader("Главное сегодня")
    for n in fetch_news():
        st.markdown(f"📰 [{n['title']}]({n['link']})")

st.markdown("<br><hr><center style='color:#ccc; font-size:10px;'>КУСИЦА 2024</center>", unsafe_allow_html=True)
