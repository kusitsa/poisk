import streamlit as st
import requests
import uuid
import pytz
import re
import math
from datetime import datetime
import streamlit.components.v1 as components

# 1. НАСТРОЙКА СТРАНИЦЫ
st.set_page_config(page_title="КУСИЦА — Super App", page_icon="🔍", layout="wide")

# 2. УЛЬТРА CSS (Яндекс-стайл + Озвучка)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #fff; }
    .logo { font-size: 38px; font-weight: 900; letter-spacing: -2.5px; color: #000; margin-bottom: 5px; }
    .informer-pill { background: #f2f2f4; padding: 4px 12px; border-radius: 12px; font-size: 11px; color: #555; }
    .currency-red { border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; padding: 2px 10px; border-radius: 10px; }
    
    /* Стили калькулятора */
    .calc-display { background: #000; color: #0f0; padding: 15px; border-radius: 10px; font-family: monospace; font-size: 24px; text-align: right; margin-bottom: 10px; }
    
    /* Поиск */
    .stTextInput > div > div > input { font-size: 18px !important; padding: 20px 25px !important; border-radius: 30px !important; border: 2px solid #ffdb4d !important; }
    .stButton > button { height: 55px; width: 100%; border-radius: 30px; background-color: #ffdb4d !important; color: black !important; font-size: 18px; font-weight: bold; border: none !important; }
    
    .alice-card { background: #fdfdff; padding: 25px; border-radius: 22px; box-shadow: 0 10px 40px rgba(0,0,0,0.05); border-left: 6px solid #8e44ad; margin-top: 15px; line-height: 1.6; font-size: 18px; }
    .tts-btn { background: #8e44ad !important; color: white !important; border-radius: 20px !important; margin-top: 10px !important; }
    
    .img-box { border: 1px solid #eee; border-radius: 12px; padding: 5px; text-align: center; background: #fff; }
    </style>
    """, unsafe_allow_html=True)

# 3. JS ФУНКЦИИ (ГОЛОС И ОЗВУЧКА)
def inject_js():
    components.html("""
        <script>
        // Функция озвучки текста
        window.speakText = (text) => {
            if ('speechSynthesis' in window) {
                window.speechSynthesis.cancel(); // Остановить текущую речь
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = 'ru-RU';
                utterance.rate = 1.1; // Скорость
                window.speechSynthesis.speak(utterance);
            } else {
                alert("Ваш браузер не поддерживает озвучку текста.");
            }
        };
        // Функция распознавания голоса (микрофон)
        window.startVoice = () => {
            const rec = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            rec.lang = 'ru-RU'; rec.start();
            rec.onresult = (e) => {
                const text = e.results[0][0].transcript;
                const input = window.parent.document.querySelector('input[data-testid="stTextInput"]');
                input.value = text;
                input.dispatchEvent(new Event('input', {bubbles:true}));
            };
        };
        </script>
    """, height=0)

# 4. ИНИЦИАЛИЗАЦИЯ ПАМЯТИ
state = st.session_state
if 'res' not in state: state.res = None
if 'calc_val' not in state: state.calc_val = ""
if 'last_q' not in state: state.last_q = ""

# 5. API ФУНКЦИИ
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

# 6. ВИДЖЕТЫ
def show_calculator():
    st.markdown("### 🧮 Калькулятор")
    mode = st.toggle("Научный режим", key="sci_mode")
    st.markdown(f'<div class="calc-display">{state.calc_val if state.calc_val else "0"}</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    keys = ['7','8','9','/','4','5','6','*','1','2','3','-','0','.','C','+']
    if mode: keys += ['sin','cos','sqrt','**','log','tan','(',')','abs','pi']
    for i, k in enumerate(keys):
        with cols[i % 4]:
            if st.button(k, key=f"k_{k}"):
                if k == 'C': state.calc_val = ""
                else: state.calc_val += k
                st.rerun()
    if st.button("=", use_container_width=True):
        try:
            safe_dict = {"math": math, "sin": math.sin, "cos": math.cos, "sqrt": math.sqrt, "log": math.log, "tan": math.tan, "pi": math.pi, "abs": abs}
            state.calc_val = str(eval(state.calc_val, {"__builtins__": None}, safe_dict))
        except: state.calc_val = "Ошибка"
        st.rerun()

def show_translator():
    st.markdown("### 🌐 Переводчик")
    langs = ["Русский", "English", "Deutsch", "Français", "中文", "日本語"]
    c1, c2 = st.columns(2)
    with c1:
        src = st.selectbox("Из", langs, index=0)
        txt = st.text_area("Текст", height=100)
    with c2:
        tar = st.selectbox("В", langs, index=1)
        if txt:
            res = get_ai([{"role":"user", "content":f"Переведи на {tar}: {txt}"}])
            st.text_area("Результат", value=res, height=100)

# --- ШАПКА ---
inject_js()
m_t, m_w, m_u = get_meta()
col_l, col_i = st.columns([1, 4])
with col_l: st.markdown('<div class="logo">КУСИЦА</div>', unsafe_allow_html=True)
with col_i: st.markdown(f'<div style="display:flex; gap:10px;"><div class="informer-pill">📅 {m_t}</div><div class="informer-pill">🌡️ {m_w}</div><div class="currency-red">USD {m_u}₽</div></div>', unsafe_allow_html=True)

# --- ПОИСК ---
col_q, col_mic, col_b = st.columns([7, 0.5, 1.5])
with col_q: q = st.text_input("", placeholder="Найдётся всё...", key="main_search", label_visibility="collapsed")
with col_mic:
    if st.button("🎙️"): st.write('<script>window.startVoice();</script>', unsafe_allow_html=True)
with col_b: btn = st.button("Найти ответ ➔")

# --- ЛОГИКА ---
if (btn or q) and q:
    ql = q.lower()
    if "калькулятор" in ql: show_calculator()
    elif "переводчик" in ql: show_translator()
    else:
        if state.last_q != q:
            with st.spinner(" "):
                try:
                    s_key = st.secrets["SERPER_API_KEY"]
                    res_t = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': s_key}, json={"q": q, "hl": "ru"}).json()
                    res_i = requests.post("https://google.serper.dev/images", headers={'X-API-KEY': s_key}, json={"q": q}).json()
                    res_v = requests.post("https://google.serper.dev/videos", headers={'X-API-KEY': s_key}, json={"q": q}).json()
                    links = res_t.get('organic', [])
                    ctx = "\n".join([l.get('snippet','') for l in links[:3]])
                    ans = get_ai([{"role":"system","content":"Ты Кусица. Отвечай подробно."}, {"role":"user","content":f"Вопрос: {q}\nДанные: {ctx}"}])
                    state.res = {"ans": ans, "links": links, "imgs": res_i.get('images', []), "vids": res_v.get('videos', [])}
                    state.last_q = q
                except: st.error("Ошибка поиска")

        if state.res:
            t1, t2, t3 = st.tabs(["🔍 Поиск", "🖼️ Картинки", "📺 Видео"])
            with t1:
                st.markdown(f'<div class="alice-card"><b>🟣 КУСИЦА:</b><br><br>{state.res["ans"]}</div>', unsafe_allow_html=True)
                if st.button("🔊 Озвучить ответ", key="tts_play"):
                    # Очищаем текст от лишних символов для TTS
                    clean_text = state.res['ans'].replace('"', "'").replace("\n", " ")
                    st.write(f'<script>window.speakText("{clean_text[:500]}");</script>', unsafe_allow_html=True)
                
                st.write("---")
                for l in state.res['links'][:10]:
                    st.markdown(f'<div><a href="{l["link"]}" target="_blank" style="font-size:18px; font-weight:bold; color:#1a0dab;">{l["title"]}</a><p>{l.get("snippet","")}</p></div>', unsafe_allow_html=True)
            
            with t2:
                cols = st.columns(2)
                for i, img in enumerate(state.res['imgs'][:12]):
                    with cols[i % 2]:
                        st.image(img['imageUrl'])
                        if st.button("📩 В Мессенджер", key=f"m_{i}"): st.code(img['imageUrl'])
            
            with t3:
                for v in state.res['vids'][:5]:
                    st.markdown(f"**[{v['title']}]({v['link']})**")
                    st.image(v.get('imageUrl', ''))
else:
    st.write("---")
    st.subheader("Главное сегодня")
    for n in fetch_news():
        st.markdown(f"📰 [{n['title']}]({n['link']})")

st.markdown("<br><hr><center style='color:#ccc; font-size:10px;'>КУСИЦА • 2024</center>", unsafe_allow_html=True)
