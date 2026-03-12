import streamlit as st
import requests
import uuid
import pytz
import re
from datetime import datetime
import streamlit.components.v1 as components

# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ
st.set_page_config(page_title="КУСИЦА", page_icon="🔍", layout="wide")

# 2. УЛЬТРА CSS (Мобильная адаптация + Яндекс-стайл)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #fff; }
    
    .logo { font-size: 38px; font-weight: 900; letter-spacing: -2px; color: #000; margin-bottom: 5px; }
    
    /* Шапка (Информеры) */
    .informer-box { display: flex; flex-wrap: wrap; gap: 6px; font-size: 11px; margin-bottom: 15px; }
    .informer-pill { background: #f2f2f4; padding: 4px 10px; border-radius: 10px; display: flex; align-items: center; gap: 4px; color: #555; white-space: nowrap; }
    .currency-red { border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; padding: 2px 8px; border-radius: 8px; }

    /* Поиск */
    .stTextInput > div > div > input { font-size: 18px !important; padding: 18px 22px !important; border-radius: 25px !important; border: 2px solid #ffdb4d !important; }
    .stButton > button { height: 52px; width: 100%; border-radius: 25px; background-color: #ffdb4d !important; color: black !important; font-size: 18px; font-weight: bold; border: none !important; }

    /* Ответ ИИ */
    .alice-card { background: #fdfdff; padding: 20px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); border-left: 6px solid #8e44ad; margin-top: 10px; font-size: 17px; line-height: 1.5; }
    
    /* Карточки контента */
    .video-card { background: #f9f9f9; padding: 10px; border-radius: 15px; border: 1px solid #eee; margin-bottom: 15px; }
    .img-box { border: 1px solid #eee; border-radius: 12px; padding: 5px; text-align: center; background: #fff; margin-bottom: 10px; }
    
    /* Мессенджер */
    .messenger-box { background: #e7f3ff; padding: 15px; border-radius: 15px; border: 2px solid #007bff; margin-top: 10px; }

    @media (max-width: 640px) {
        .logo { font-size: 28px; text-align: center; }
        .informer-box { justify-content: center; }
        .stTabs [data-baseweb="tab"] { font-size: 14px; padding: 10px 5px; }
    }
    </style>
    """, unsafe_allow_html=True)

# 3. ПАМЯТЬ ПРИЛОЖЕНИЯ
if 'res' not in st.session_state: st.session_state.res = None
if 'history' not in st.session_state: st.session_state.history = []
if 'limits' not in st.session_state: st.session_state.limits = {"links": 3, "imgs": 8, "vids": 4}
if 'view_img_idx' not in st.session_state: st.session_state.view_img_idx = None
if 'msg_open' not in st.session_state: st.session_state.msg_open = False

# 4. ФУНКЦИИ API
@st.cache_data(ttl=600)
def get_header_data():
    try:
        tz_m, tz_k = pytz.timezone('Europe/Moscow'), pytz.timezone('Asia/Almaty')
        now = datetime.now(tz_m)
        w = requests.get("https://wttr.in/Moscow?format=%t", timeout=2).text.strip()
        curr = requests.get("https://open.er-api.com/v6/latest/USD", timeout=2).json()
        usd = round(curr['rates']['RUB'], 2)
        eur = round(usd / (curr['rates']['EUR'] / curr['rates']['USD']), 2)
        return now.strftime("%d.%m"), now.strftime("%H:%M"), datetime.now(tz_k).strftime("%H:%M"), w, usd, eur
    except: return "??", "??", "??", "?", "??", "??"

def get_ai_res(msgs):
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {"model": "llama-3.1-8b-instant", "messages": msgs, "temperature": 0.6}
        res = requests.post(url, headers={"Authorization": f"Bearer {api_key}"}, json=payload, timeout=20).json()
        return res['choices'][0]['message']['content']
    except: return "Кусица призадумалась. Попробуйте снова."

@st.cache_data(ttl=1800)
def fetch_news(key):
    try:
        r = requests.post("https://google.serper.dev/news", headers={'X-API-KEY': key}, json={"q": "новости сегодня Россия", "gl": "ru", "hl": "ru"}).json()
        return r.get('news', [])[:5]
    except: return []

# --- ШАПКА ---
d, tm, tk, w, usd_r, eur_r = get_header_data()
st.markdown(f'<div class="logo">КУСИЦА</div>', unsafe_allow_html=True)
st.markdown(f"""
    <div class="informer-box">
        <div class="informer-pill">📅 {d}</div><div class="informer-pill">🕒 МСК {tm}</div>
        <div class="informer-pill">🇰🇿 КЗ {tk}</div><div class="informer-pill">🌡️ МСК {w}</div>
        <div class="currency-red">USD {usd_r}₽</div><div class="currency-red">EUR {eur_r}₽</div>
    </div>
    """, unsafe_allow_html=True)

# --- ПОИСК ---
col_q, col_b = st.columns([6, 1])
with col_q: q = st.text_input("", placeholder="Найдётся всё...", key="main_search", label_visibility="collapsed")
with col_b: btn = st.button("Найти ➔")

# --- САЙДБАР (ИСТОРИЯ) ---
with st.sidebar:
    st.title("📜 История")
    for h in reversed(st.session_state.history[-5:]):
        if st.button(f"🔍 {h}", key=f"hist_{h}"): q = h

# --- ЛОГИКА ПОИСКА ---
if (btn or q) and q:
    if st.session_state.get('last_q') != q:
        with st.spinner(" "):
            try:
                s_key = st.secrets["SERPER_API_KEY"]
                headers = {'X-API-KEY': s_key, 'Content-Type': 'application/json'}
                sr = requests.post("https://google.serper.dev/search", headers=headers, json={"q": q, "hl": "ru"}).json()
                ir = requests.post("https://google.serper.dev/images", headers=headers, json={"q": q}).json()
                vr = requests.post("https://google.serper.dev/videos", headers=headers, json={"q": q}).json()
                
                links = sr.get('organic', [])
                ans = get_ai_res([{"role":"system","content":"Ты Кусица. Отвечай подробно."}, {"role":"user","content":f"Вопрос: {q}\nДанные: {links[:3]}"}])
                
                st.session_state.res = {"ans": ans, "links": links, "imgs": ir.get('images', []), "vids": vr.get('videos', []), "q": q}
                if q not in st.session_state.history: st.session_state.history.append(q)
                st.session_state.last_q = q
                st.session_state.limits = {"links": 3, "imgs": 8, "vids": 4}
                st.session_state.view_img_idx = None
            except: st.error("Ошибка сети")

# --- ВЫВОД РЕЗУЛЬТАТОВ ---
if st.session_state.res:
    res = st.session_state.res
    tab1, tab2, tab3 = st.tabs(["🔍 Поиск", "🖼️ Картинки", "📺 Видео"])
    
    with tab1:
        st.markdown(f'<div class="alice-card"><b>🟣 КУСИЦА:</b><br><br>{res["ans"]}</div>', unsafe_allow_html=True)
        st.write("---")
        for l in res['links'][:st.session_state.limits['links']]:
            st.markdown(f'<div style="margin-bottom:20px;"><a href="{l["link"]}" target="_blank" style="font-size:19px; color:#1a0dab; text-decoration:none; font-weight:500;">{l["title"]}</a><br><small style="color:#006621;">{l["link"][:80]}...</small><div style="font-size:14px; color:#444;">{l.get("snippet","")}</div></div>', unsafe_allow_html=True)
        if st.button("Показать еще ссылки"): st.session_state.limits['links'] += 5; st.rerun()

    with tab2:
        imgs = res['imgs']
        if st.session_state.view_img_idx is not None:
            idx = st.session_state.view_img_idx
            st.button("⬅️ Назад", on_click=lambda: setattr(st.session_state, 'view_img_idx', None))
            st.image(imgs[idx]['imageUrl'], use_container_width=True)
            st.subheader(imgs[idx].get('title', ''))
            
            c1, c2 = st.columns(2)
            with c1: st.link_button("🌐 Перейти на сайт", imgs[idx]['link'])
            with c2: 
                if st.button("📩 Отправить в Мессенджер"): st.session_state.msg_open = True
            
            if st.session_state.msg_open:
                st.markdown('<div class="messenger-box"><b>💬 КУСИЦА МЕССЕНДЖЕР</b><br>Скопируйте ссылку ниже:</div>', unsafe_allow_html=True)
                st.code(imgs[idx]['imageUrl'])
                if st.button("Закрыть"): st.session_state.msg_open = False; st.rerun()

            cp1, cp2 = st.columns(2)
            with cp1: 
                if idx > 0 and st.button("◀️ Назад"): st.session_state.view_img_idx -= 1; st.rerun()
            with cp2:
                if idx < len(imgs)-1 and st.button("Вперед ▶️"): st.session_state.view_img_idx += 1; st.rerun()
        else:
            cols = st.columns(2)
            for i, img in enumerate(imgs[:st.session_state.limits['imgs']]):
                with cols[i % 2]:
                    st.markdown(f'<div class="img-box"><img src="{img["imageUrl"]}" style="width:100%; border-radius:10px;"><br><small>{img.get("source","")}</small></div>', unsafe_allow_html=True)
                    if st.button(f"Увеличить #{i+1}", key=f"z_{i}"): st.session_state.view_img_idx = i; st.rerun()
            if st.button("Больше картинок"): st.session_state.limits['imgs'] += 10; st.rerun()

    with tab3:
        vids = res['vids']
        if not vids: st.write("Видео не найдены")
        for v in vids[:st.session_state.limits['vids']]:
            st.markdown(f"""<div class="video-card"><b>{v['title']}</b><br><img src="{v.get('imageUrl','')}" style="width:200px; border-radius:10px; margin:10px 0;"><br><a href="{v['link']}" target="_blank">▶️ Смотреть на {v.get('source','сайте')}</a></div>""", unsafe_allow_html=True)
        if st.button("Больше видео"): st.session_state.limits['vids'] += 4; st.rerun()

else:
    # ГЛАВНАЯ
    st.write("---")
    st.subheader("Главное сегодня")
    for n in fetch_news(st.secrets.get("SERPER_API_KEY", "")):
        st.markdown(f"📰 [{n['title']}]({n['link']})")

st.markdown("<br><hr><center style='color:#ccc; font-size:10px;'>КУСИЦА • 2024</center>", unsafe_allow_html=True)
