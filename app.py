import streamlit as st
import httpx
from datetime import datetime
import pytz
import uuid

# 1. Настройка страницы
st.set_page_config(page_title="КУСИЦА", page_icon="🔍", layout="wide")

# 2. Яндекс-стайл CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #fff; }
    .logo { font-size: 38px; font-weight: 900; letter-spacing: -2px; color: #000; margin-bottom: 5px; }
    .informer-box { display: flex; flex-wrap: wrap; gap: 8px; font-size: 12px; margin-bottom: 20px; }
    .informer-pill { background: #f2f2f4; padding: 5px 12px; border-radius: 15px; display: flex; align-items: center; gap: 5px; color: #555; }
    .currency-pill { border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; }
    .stTextInput > div > div > input {
        font-size: 18px !important; padding: 22px 25px !important;
        border-radius: 30px !important; border: 2px solid #ffdb4d !important;
    }
    .stButton > button { height: 60px; width: 100%; border-radius: 30px; background-color: #ffdb4d; color: black; border: none; font-size: 24px; }
    .alice-card { background: #fff; padding: 25px; border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.05); border-left: 6px solid #8e44ad; margin-top: 15px; }
    .alice-label { color: #8e44ad; font-weight: bold; font-size: 13px; margin-bottom: 8px; text-transform: uppercase; }
    .news-item { padding: 10px 0; border-bottom: 1px solid #f0f0f0; font-size: 15px; }
    .news-item a { color: #000; text-decoration: none; font-weight: 500; }
    .search-result { margin-bottom: 20px; }
    .search-title { font-size: 18px; color: #1a0dab; text-decoration: none; font-weight: 500; }
    .search-url { color: #006621; font-size: 13px; display: block; }
    .img-container { cursor: pointer; border-radius: 12px; overflow: hidden; transition: 0.3s; margin-bottom: 15px; border: 1px solid #eee; }
    .img-container:hover { transform: scale(1.02); }
    </style>
    """, unsafe_allow_html=True)

# 3. Память приложения (Session State)
if 'res' not in st.session_state: st.session_state.res = None
if 'link_limit' not in st.session_state: st.session_state.link_limit = 3
if 'img_limit' not in st.session_state: st.session_state.img_limit = 4
if 'view_img_idx' not in st.session_state: st.session_state.view_img_idx = None

# 4. Получение данных (Шапка + Новости)
@st.cache_data(ttl=600)
def get_informers():
    try:
        tz_m = pytz.timezone('Europe/Moscow')
        now = datetime.now(tz_m)
        w = httpx.get("https://wttr.in/Moscow?format=%t", timeout=3).text.strip()
        c = httpx.get("https://open.er-api.com/v6/latest/USD", timeout=3).json()
        usd = round(c['rates']['RUB'], 1)
        eur = round(usd / (c['rates']['EUR'] / c['rates']['USD']), 1)
        return now.strftime("%d.%m"), now.strftime("%H:%M"), datetime.now(pytz.timezone('Asia/Almaty')).strftime("%H:%M"), w, usd, eur
    except: return "??", "??", "??", "?", "??", "??"

@st.cache_data(ttl=1800)
def get_news(key):
    try:
        r = httpx.post("https://google.serper.dev/news", headers={'X-API-KEY': key}, json={"q": "новости сегодня", "gl": "ru", "hl": "ru"}).json()
        return r.get('news', [])[:5]
    except: return []

# 5. Мозг (GigaChat)
def get_ai(msgs):
    try:
        auth = st.secrets["GIGACHAT_CREDENTIALS"]
        with httpx.Client(verify=False) as cl:
            tk_r = cl.post("https://ngw.devices.sberbank.ru:9443/api/v2/oauth", 
                         headers={"Authorization": f"Basic {auth}", "RqUID": str(uuid.uuid4()), "Content-Type": "application/x-www-form-urlencoded"},
                         data={"scope": "GIGACHAT_API_PERS"})
            tk = tk_r.json()['access_token']
            rs = cl.post("https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                        headers={"Authorization": f"Bearer {tk}", "Content-Type": "application/json"},
                        json={"model": "GigaChat", "messages": msgs, "temperature": 0.7}).json()
            return rs['choices'][0]['message']['content']
    except Exception as e:
        return f"Ошибка ИИ: {str(e)}. Проверьте GIGACHAT_CREDENTIALS."

# --- ШАПКА ---
d, tm, tk, w, usd, eur = get_informers()
col_logo, col_info = st.columns([1, 4])
with col_logo: st.markdown('<div class="logo">КУСИЦА</div>', unsafe_allow_html=True)
with col_info:
    st.markdown(f'<div class="informer-box"><div class="informer-pill">📅 {d}</div><div class="informer-pill">🕒 МСК {tm}</div><div class="informer-pill">🇰🇿 КЗ {tk}</div><div class="informer-pill">🌡️ {w}</div><div class="informer-pill currency-pill">USD {usd}₽</div><div class="informer-pill currency-pill">EUR {eur}₽</div></div>', unsafe_allow_html=True)

# --- ПОИСК ---
col_q, col_b = st.columns([7, 1])
with col_q: q = st.text_input("", placeholder="Найдётся всё...", label_visibility="collapsed")
with col_b: btn = st.button("➔")

if (btn or q) and q:
    if st.session_state.get('last_q') != q:
        with st.spinner(" "):
            try:
                s_key = st.secrets["SERPER_API_KEY"]
                sr = httpx.post("https://google.serper.dev/search", headers={'X-API-KEY': s_key}, json={"q": q, "hl": "ru"}).json()
                ir = httpx.post("https://google.serper.dev/images", headers={'X-API-KEY': s_key}, json={"q": q}).json()
                links = sr.get('organic', [])
                ans = get_ai([{"role":"system","content":"Ты Кусица, дружелюбный ассистент."}, {"role":"user","content":f"Запрос: {q}\nДанные: {links[:3]}"}])
                st.session_state.res = {"ans": ans, "links": links, "imgs": ir.get('images', [])}
                st.session_state.last_q = q
                st.session_state.link_limit = 3
                st.session_state.img_limit = 4
                st.session_state.view_img_idx = None
            except: st.error("Ошибка поиска")

# --- ВЫВОД ---
if st.session_state.res:
    t1, t2 = st.tabs(["🔍 Поиск", "🖼️ Картинки"])
    
    with t1:
        st.markdown(f'<div class="alice-card"><div class="alice-label">✨ Ассистент Кусица</div>{st.session_state.res["ans"]}</div>', unsafe_allow_html=True)
        st.write("")
        for l in st.session_state.res['links'][:st.session_state.link_limit]:
            st.markdown(f'<div class="search-result"><a class="search-title" href="{l["link"]}" target="_blank">{l["title"]}</a><span class="search-url">{l["link"]}</span><div class="search-desc">{l.get("snippet","")}</div></div>', unsafe_allow_html=True)
        if st.session_state.link_limit < len(st.session_state.res['links']):
            if st.button("Показать еще ссылки"): st.session_state.link_limit += 5; st.rerun()

    with t2:
        imgs = st.session_state.res['imgs']
        if st.session_state.view_img_idx is not None:
            # ПРОСМОТР КАРТИНКИ
            idx = st.session_state.view_img_idx
            curr_img = imgs[idx]
            st.button("⬅️ К списку", on_click=lambda: setattr(st.session_state, 'view_img_idx', None))
            
            c1, c2, c3 = st.columns([1, 10, 1])
            with c1: 
                if idx > 0: st.button("◀️", on_click=lambda: setattr(st.session_state, 'view_img_idx', idx-1))
            with c2:
                st.image(curr_img['imageUrl'], use_container_width=True)
                st.subheader(curr_img['title'])
                st.caption(f"Источник: {curr_img['source']}")
                st.link_button("Открыть сайт", curr_img['link'])
            with c3:
                if idx < len(imgs)-1: st.button("▶️", on_click=lambda: setattr(st.session_state, 'view_img_idx', idx+1))
        else:
            # ГАЛЕРЕЯ
            cols = st.columns(2)
            for i, img in enumerate(imgs[:st.session_state.img_limit]):
                with cols[i % 2]:
                    st.image(img['imageUrl'])
                    if st.button(f"Увеличить #{i+1}", key=f"img_{i}"):
                        st.session_state.view_img_idx = i
                        st.rerun()
            if st.session_state.img_limit < len(imgs):
                if st.button("Показать еще картинки"): st.session_state.img_limit += 6; st.rerun()
else:
    # ГЛАВНАЯ
    st.write("---")
    st.subheader("Главные новости")
    for n in get_news(st.secrets.get("SERPER_API_KEY", "")):
        st.markdown(f'<div class="news-item"><a href="{n["link"]}" target="_blank">{n["title"]}</a><br><small>{n.get("source","")} • {n.get("date","")}</small></div>', unsafe_allow_html=True)

st.markdown("<br><hr><center style='color:#999; font-size:11px;'>КУСИЦА ПОИСК • 2024</center>", unsafe_allow_html=True)
