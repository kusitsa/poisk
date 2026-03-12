import streamlit as st
import httpx
from datetime import datetime
import pytz
import uuid

# 1. Настройка страницы
st.set_page_config(page_title="КУСИЦА", page_icon="🔍", layout="wide")

# 2. Яндекс-стайл CSS (Минимализм)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #fff; color: #000; }

    /* Логотип */
    .logo { font-size: 38px; font-weight: 900; letter-spacing: -2px; color: #000; margin-bottom: 5px; }
    
    /* Информеры */
    .informer-box { display: flex; flex-wrap: wrap; gap: 8px; font-size: 12px; margin-bottom: 20px; }
    .informer-pill { background: #f2f2f4; padding: 5px 12px; border-radius: 15px; display: flex; align-items: center; gap: 5px; color: #555; }
    .currency-pill { border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; }

    /* Поисковая строка */
    .stTextInput > div > div > input {
        font-size: 18px !important; padding: 22px 25px !important;
        border-radius: 30px !important; border: 2px solid #ffdb4d !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    }
    .stButton > button {
        height: 60px; width: 100%; border-radius: 30px;
        background-color: #ffdb4d; color: black; border: none; font-size: 24px;
    }

    /* Блок Алисы */
    .alice-card { 
        background: #fff; padding: 25px; border-radius: 20px; 
        box-shadow: 0 10px 40px rgba(0,0,0,0.05); border-left: 6px solid #8e44ad; margin-top: 15px; 
    }
    .alice-label { color: #8e44ad; font-weight: bold; font-size: 13px; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; }

    /* Новости */
    .news-item { padding: 10px 0; border-bottom: 1px solid #f0f0f0; font-size: 15px; }
    .news-item a { color: #000; text-decoration: none; font-weight: 500; }
    .news-item a:hover { color: #ff4b4b; }
    .news-meta { font-size: 11px; color: #999; margin-top: 3px; }

    /* Ссылки поиска */
    .search-result { margin-bottom: 20px; }
    .search-title { font-size: 18px; color: #1a0dab; text-decoration: none; font-weight: 500; }
    .search-url { color: #006621; font-size: 13px; display: block; margin-top: 2px; }
    .search-desc { color: #444; font-size: 14px; margin-top: 4px; line-height: 1.4; }

    /* Табы */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { border-radius: 20px; padding: 5px 20px; background: #f0f0f2; }
    .stTabs [aria-selected="true"] { background: #ffdb4d !important; }
    </style>
    """, unsafe_allow_html=True)

# 3. Функции получения данных
@st.cache_data(ttl=600)
def get_informers():
    try:
        # Время
        tz_m = pytz.timezone('Europe/Moscow')
        now_m = datetime.now(tz_m)
        d, t_m = now_m.strftime("%d.%m"), now_m.strftime("%H:%M")
        t_k = datetime.now(pytz.timezone('Asia/Almaty')).strftime("%H:%M")
        # Погода и Валюта
        w = httpx.get("https://wttr.in/Moscow?format=%t", timeout=3).text.strip()
        c = httpx.get("https://open.er-api.com/v6/latest/USD", timeout=3).json()
        usd = round(c['rates']['RUB'], 1)
        eur = round(usd / (c['rates']['EUR'] / c['rates']['USD']), 1)
        return d, t_m, t_k, w, usd, eur
    except: return "??", "??", "??", "?°C", "??", "??"

@st.cache_data(ttl=1800)
def get_real_news(api_key):
    try:
        url = "https://google.serper.dev/news"
        headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
        # Ищем главные новости России
        res = httpx.post(url, headers=headers, json={"q": "главные новости сегодня", "gl": "ru", "hl": "ru"}, timeout=10).json()
        return res.get('news', [])[:5]
    except: return []

def get_ai_res(msgs):
    try:
        auth = st.secrets["GIGACHAT_CREDENTIALS"]
        uid = str(uuid.uuid4())
        with httpx.Client(verify=False) as cl:
            tk = cl.post("https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                headers={"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded", "RqUID": uid},
                data={"scope": "GIGACHAT_API_PERS"}).json()["access_token"]
            rs = cl.post("https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {tk}", "Content-Type": "application/json"},
                json={"model": "GigaChat", "messages": msgs, "temperature": 0.7}).json()
            return rs["choices"][0]["message"]["content"]
    except: return "Ошибка связи с ассистентом."

# --- Инициализация ---
if 'search_res' not in st.session_state: st.session_state.search_res = None
d, tm, tk, w, usd, eur = get_informers()

# --- ШАПКА ---
col_logo, col_info = st.columns([1, 4])
with col_logo: st.markdown('<div class="logo">КУСИЦА</div>', unsafe_allow_html=True)
with col_info:
    st.markdown(f"""
    <div class="informer-box">
        <div class="informer-pill">📅 {d}</div>
        <div class="informer-pill">🕒 МСК {tm}</div>
        <div class="informer-pill">🇰🇿 КЗ {tk}</div>
        <div class="informer-pill">🌡️ {w}</div>
        <div class="informer-pill currency-pill">USD {usd}₽</div>
        <div class="informer-pill currency-pill">EUR {eur}₽</div>
    </div>
    """, unsafe_allow_html=True)

# --- ПОИСК ---
col_q, col_b = st.columns([7, 1])
with col_q: q = st.text_input("", placeholder="Найдётся всё...", label_visibility="collapsed")
with col_b: btn = st.button("➔")

# --- ЛОГИКА ---
if (btn or q) and q:
    if st.session_state.get('last_q') != q:
        with st.spinner(" "):
            try:
                s_key = st.secrets["SERPER_API_KEY"]
                # Поиск текста
                sr = httpx.post("https://google.serper.dev/search", headers={'X-API-KEY': s_key}, json={"q": q, "hl": "ru"}).json()
                # Поиск картинок
                ir = httpx.post("https://google.serper.dev/images", headers={'X-API-KEY': s_key}, json={"q": q}).json()
                
                links = sr.get('organic', [])
                ctx = "\n".join([l.get('snippet', '') for l in links[:5]])
                ans = get_ai_res([{"role":"system","content":"Ты Кусица. Отвечай кратко и вежливо как Алиса."},
                                  {"role":"user","content":f"Запрос: {q}\nДанные: {ctx}"}])
                
                st.session_state.search_res = {"ans": ans, "links": links, "imgs": ir.get('images', []), "ctx": ctx}
                st.session_state.last_q = q
            except: st.error("Ошибка поиска")

# --- ВЫВОД РЕЗУЛЬТАТОВ ---
if st.session_state.search_res:
    t1, t2 = st.tabs(["🔍 Поиск", "🖼️ Картинки"])
    with t1:
        res = st.session_state.search_res
        st.markdown(f"""
        <div class="alice-card">
            <div class="alice-label">✨ Ассистент Кусица</div>
            <div style="font-size: 18px; line-height: 1.5;">{res['ans']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("")
        for l in res['links'][:5]:
            st.markdown(f"""
            <div class="search-result">
                <a class="search-title" href="{l.get('link')}" target="_blank">{l.get('title')}</a>
                <span class="search-url">{l.get('link')[:70]}...</span>
                <div class="search-desc">{l.get('snippet')}</div>
            </div>
            """, unsafe_allow_html=True)

    with t2:
        imgs = st.session_state.search_res.get('imgs', [])
        c = st.columns(2)
        for i, img in enumerate(imgs[:12]):
            with c[i % 2]: st.image(img.get('imageUrl'), use_container_width=True)

# --- НОВОСТИ (Главная страница) ---
else:
    st.write("---")
    st.subheader("Главные новости")
    real_news = get_real_news(st.secrets["SERPER_API_KEY"])
    if real_news:
        for n in real_news:
            st.markdown(f"""
            <div class="news-item">
                <a href="{n.get('link')}" target="_blank">{n.get('title')}</a>
                <div class="news-meta">{n.get('source')} • {n.get('date')}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.write("Новости временно недоступны")

st.markdown("<br><hr><center style='color:#999; font-size:11px;'>КУСИЦА ПОИСК • 2024</center>", unsafe_allow_html=True)
