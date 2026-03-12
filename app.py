import streamlit as st
import requests
import uuid
import pytz
from datetime import datetime

# 1. Настройка страницы
st.set_page_config(page_title="КУСИЦА", page_icon="🔍", layout="wide")

# 2. Яндекс-стайл CSS (Адаптивный под телефон)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #fff; color: #000; }
    
    .logo { font-size: 34px; font-weight: 900; letter-spacing: -2px; color: #000; margin-bottom: 5px; }
    
    /* Информеры */
    .informer-box { display: flex; flex-wrap: wrap; gap: 6px; font-size: 11px; margin-bottom: 20px; }
    .informer-item { background: #f2f2f4; padding: 4px 10px; border-radius: 12px; display: flex; align-items: center; gap: 4px; color: #555; white-space: nowrap; }
    .currency-pill { border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; }

    /* Поисковая строка */
    .stTextInput > div > div > input {
        font-size: 18px !important; padding: 18px 25px !important;
        border-radius: 25px !important; border: 2px solid #ffdb4d !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    .stButton > button {
        height: 55px; width: 100%; border-radius: 25px;
        background-color: #ffdb4d; color: black; border: none; font-size: 24px; font-weight: bold;
    }

    /* Блок ассистента (Алиса стайл) */
    .alice-card { 
        background: #fff; padding: 25px; border-radius: 20px; 
        box-shadow: 0 10px 40px rgba(0,0,0,0.05); border-left: 6px solid #8e44ad; margin-top: 15px; 
    }
    .alice-label { color: #8e44ad; font-weight: bold; font-size: 13px; margin-bottom: 8px; text-transform: uppercase; }

    /* Ссылки поиска */
    .search-result { margin-bottom: 22px; }
    .search-title { font-size: 19px; color: #1a0dab; text-decoration: none; font-weight: 500; }
    .search-title:hover { text-decoration: underline; }
    .search-url { color: #006621; font-size: 13px; display: block; margin-top: 2px; }
    .search-desc { color: #444; font-size: 14px; margin-top: 4px; line-height: 1.5; }

    /* Новости */
    .news-item { padding: 10px 0; border-bottom: 1px solid #f0f0f0; font-size: 15px; }
    .news-item a { color: #000; text-decoration: none; font-weight: 500; }

    /* Картинки */
    .img-grid-container { border-radius: 12px; overflow: hidden; border: 1px solid #eee; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 3. Инициализация памяти приложения
if 'res' not in st.session_state: st.session_state.res = None
if 'link_limit' not in st.session_state: st.session_state.link_limit = 3
if 'img_limit' not in st.session_state: st.session_state.img_limit = 4
if 'view_img_idx' not in st.session_state: st.session_state.view_img_idx = None

# 4. Функции данных (Информеры)
@st.cache_data(ttl=600)
def get_top_data():
    try:
        tz_m = pytz.timezone('Europe/Moscow')
        now = datetime.now(tz_m)
        w_m = requests.get("https://wttr.in/Moscow?format=%t", timeout=3).text.strip()
        w_s = requests.get("https://wttr.in/Saint-Petersburg?format=%t", timeout=3).text.strip()
        curr = requests.get("https://open.er-api.com/v6/latest/USD", timeout=3).json()
        usd = round(curr['rates']['RUB'], 1)
        eur = round(usd / (curr['rates']['EUR'] / curr['rates']['USD']), 1)
        return now.strftime("%d.%m"), now.strftime("%H:%M"), datetime.now(pytz.timezone('Asia/Almaty')).strftime("%H:%M"), w_m, w_s, usd, eur
    except: return "??", "??", "??", "?", "?", "??", "??"

@st.cache_data(ttl=1800)
def get_real_news(key):
    try:
        r = requests.post("https://google.serper.dev/news", headers={'X-API-KEY': key}, json={"q": "главные новости", "gl": "ru", "hl": "ru"}).json()
        return r.get('news', [])[:5]
    except: return []

# 5. Функция GigaChat (Исправленная ошибка Connection Reset)
def get_ai_answer(msgs):
    try:
        auth = st.secrets["GIGACHAT_CREDENTIALS"]
        # Шаг 1: Токен (verify=False обходит ошибки SSL)
        auth_res = requests.post("https://ngw.devices.sberbank.ru:9443/api/v2/oauth", 
                               headers={'Authorization': f'Basic {auth}', 'RqUID': str(uuid.uuid4()), 'Content-Type': 'application/x-www-form-urlencoded'},
                               data={'scope': 'GIGACHAT_API_PERS'}, verify=False, timeout=10)
        token = auth_res.json()['access_token']
        # Шаг 2: Чат
        chat_res = requests.post("https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                               headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
                               json={"model": "GigaChat", "messages": msgs, "temperature": 0.7}, verify=False, timeout=20)
        return chat_res.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Ошибка ассистента: {str(e)}. Проверьте GIGACHAT_CREDENTIALS."

# --- ШАПКА ---
d, tm, tk, wm, ws, usd, eur = get_top_data()
col_logo, col_info = st.columns([1, 4])
with col_logo: st.markdown('<div class="logo">КУСИЦА</div>', unsafe_allow_html=True)
with col_info:
    st.markdown(f"""
    <div class="informer-box">
        <div class="informer-item">📅 {d}</div><div class="informer-item">🕒 МСК {tm}</div>
        <div class="informer-item">🇰🇿 КЗ {tk}</div><div class="informer-item">🌡️ МСК {wm}</div>
        <div class="informer-item">🌡️ СПБ {ws}</div>
        <div class="informer-item currency-pill">USD {usd}₽</div><div class="informer-item currency-pill">EUR {eur}₽</div>
    </div>
    """, unsafe_allow_html=True)

# --- ПОИСК ---
col_q, col_b = st.columns([7, 1])
with col_q: q = st.text_input("", placeholder="Найдётся всё...", label_visibility="collapsed")
with col_b: btn = st.button("➔")

if (btn or q) and q:
    if st.session_state.get('last_q') != q:
        with st.spinner(" "):
            try:
                s_key = st.secrets["SERPER_API_KEY"]
                sr = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': s_key}, json={"q": q, "hl": "ru"}).json()
                ir = requests.post("https://google.serper.dev/images", headers={'X-API-KEY': s_key}, json={"q": q}).json()
                links = sr.get('organic', [])
                ans = get_ai_answer([{"role":"system","content":"Ты Кусица, ассистент от Яндекса. Отвечай кратко."}, {"role":"user","content":f"Вопрос: {q}\nДанные: {links[:3]}"}])
                st.session_state.res = {"ans": ans, "links": links, "imgs": ir.get('images', [])}
                st.session_state.last_q = q
                st.session_state.link_limit, st.session_state.img_limit = 3, 4
                st.session_state.view_img_idx = None
            except: st.error("Ошибка сети")

# --- ВЫВОД РЕЗУЛЬТАТОВ ---
if st.session_state.res:
    t1, t2 = st.tabs(["🔍 Поиск", "🖼️ Картинки"])
    
    with t1:
        st.markdown(f'<div class="alice-card"><div class="alice-label">✨ Ассистент Кусица</div>{st.session_state.res["ans"]}</div>', unsafe_allow_html=True)
        for l in st.session_state.res['links'][:st.session_state.link_limit]:
            st.markdown(f'<div class="search-result"><a class="search-title" href="{l["link"]}" target="_blank">{l["title"]}</a><span class="search-url">{l["link"][:80]}...</span><div class="search-desc">{l.get("snippet","")}</div></div>', unsafe_allow_html=True)
        if st.session_state.link_limit < len(st.session_state.res['links']):
            if st.button("Показать еще ссылки"): st.session_state.link_limit += 5; st.rerun()

    with t2:
        imgs = st.session_state.res['imgs']
        if st.session_state.view_img_idx is not None:
            idx = st.session_state.view_img_idx
            st.button("⬅️ Назад к галерее", on_click=lambda: setattr(st.session_state, 'view_img_idx', None))
            c1, c2, c3 = st.columns([1, 8, 1])
            with c1: 
                if idx > 0: st.button("◀️", on_click=lambda: setattr(st.session_state, 'view_img_idx', idx-1))
            with c2:
                st.image(imgs[idx]['imageUrl'], use_container_width=True)
                st.subheader(imgs[idx]['title'])
                st.link_button(f"Источник: {imgs[idx]['source']}", imgs[idx]['link'])
            with c3:
                if idx < len(imgs)-1: st.button("▶️", on_click=lambda: setattr(st.session_state, 'view_img_idx', idx+1))
        else:
            cols = st.columns(2)
            for i, img in enumerate(imgs[:st.session_state.img_limit]):
                with cols[i % 2]:
                    st.image(img['imageUrl'])
                    if st.button(f"Открыть #{i+1}", key=f"btn_{i}"):
