import streamlit as st
import requests
import uuid
import pytz
import re
from datetime import datetime
import streamlit.components.v1 as components

# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ
st.set_page_config(page_title="КУСИЦА — INFINITY", page_icon="🔍", layout="wide")

# 2. УЛЬТРА CSS (Яндекс-стайл 2024)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    /* Шапка */
    .logo { font-size: 42px; font-weight: 900; letter-spacing: -2.5px; color: #000; margin-bottom: 5px; }
    .informer-box { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }
    .informer-pill { background: #f2f2f4; padding: 6px 12px; border-radius: 15px; font-size: 12px; color: #555; border: 1px solid #eee; }
    .currency-pill { border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; }

    /* Поисковая строка */
    .stTextInput > div > div > input {
        font-size: 20px !important; padding: 22px 28px !important;
        border-radius: 35px !important; border: 2.5px solid #ffdb4d !important;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
    }
    .stButton > button {
        height: 64px; width: 100%; border-radius: 35px;
        background-color: #ffdb4d !important; color: black !important; font-size: 26px; font-weight: bold; border: none !important;
    }

    /* Закладки (Top Sites) */
    .sites-grid { display: flex; justify-content: center; gap: 15px; margin: 20px 0; flex-wrap: wrap; }
    .site-item { text-align: center; width: 65px; text-decoration: none; color: #333; }
    .site-icon { width: 45px; height: 45px; background: #f5f5f7; border-radius: 14px; display: flex; align-items: center; justify-content: center; margin: 0 auto 5px; font-size: 22px; transition: 0.2s; }
    .site-icon:hover { background: #e2e2e5; transform: translateY(-3px); }
    .site-text { font-size: 11px; font-weight: 500; }

    /* Алиса-карточка */
    .alice-card { 
        background: #fdfdff; padding: 30px; border-radius: 25px; 
        box-shadow: 0 15px 45px rgba(0,0,0,0.06); border-left: 8px solid #8e44ad; margin: 20px 0;
        font-size: 18px; line-height: 1.6;
    }

    /* Конвертер */
    .conv-box { background: #fff; padding: 25px; border-radius: 25px; border: 2px solid #ffdb4d; text-align: center; margin-bottom: 20px; box-shadow: 0 5px 15px rgba(0,0,0,0.05); }
    .conv-val { font-size: 36px; font-weight: 900; color: #000; }

    .img-card { border-radius: 15px; overflow: hidden; border: 1px solid #eee; margin-bottom: 10px; background: #fff; }
    
    /* Тёмная тема (поддержка) */
    @media (prefers-color-scheme: dark) {
        .logo { color: #fff; }
        .site-text { color: #fff; }
    }
    </style>
    """, unsafe_allow_html=True)

# 3. ПАМЯТЬ ПРИЛОЖЕНИЯ
if 'res' not in st.session_state: st.session_state.res = None
if 'history' not in st.session_state: st.session_state.history = []
if 'limits' not in st.session_state: st.session_state.limits = {"links": 3, "imgs": 8, "vids": 4}
if 'view_img_idx' not in st.session_state: st.session_state.view_img_idx = None

# 4. ФУНКЦИИ API
@st.cache_data(ttl=600)
def get_header_data():
    try:
        tz_m, tz_k = pytz.timezone('Europe/Moscow'), pytz.timezone('Asia/Almaty')
        now = datetime.now(tz_m)
        w_m = requests.get("https://wttr.in/Moscow?format=%t", timeout=2).text.strip()
        curr = requests.get("https://open.er-api.com/v6/latest/USD", timeout=2).json()
        usd = round(curr['rates']['RUB'], 2)
        eur = round(usd / (curr['rates']['EUR'] / curr['rates']['USD']), 2)
        return now.strftime("%d.%m"), now.strftime("%H:%M"), datetime.now(tz_k).strftime("%H:%M"), w_m, usd, eur
    except: return "??", "??", "??", "?", "??", "??"

def get_ai_res(msgs):
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": "llama-3.1-70b-versatile", "messages": msgs, "temperature": 0.7}
        res = requests.post(url, headers=headers, json=payload, timeout=20).json()
        return res['choices'][0]['message']['content']
    except: return "Кусица задумалась. Попробуйте еще раз через 5 секунд."

@st.cache_data(ttl=1800)
def fetch_news(key):
    try:
        r = requests.post("https://google.serper.dev/news", headers={'X-API-KEY': key}, json={"q": "главные новости Россия", "hl": "ru"}).json()
        return r.get('news', [])[:5]
    except: return []

def check_math_and_conv(query, usd_v, eur_v):
    q = query.lower()
    # Валюта
    m_u = re.search(r'(\d+)\s*(доллар|usd|бакс)', q)
    if m_u: return f"{m_u.group(1)} USD", f"{round(int(m_u.group(1)) * usd_v, 2)} ₽"
    m_e = re.search(r'(\d+)\s*(евро|eur)', q)
    if m_e: return f"{m_e.group(1)} EUR", f"{round(int(m_e.group(1)) * eur_v, 2)} ₽"
    # Величины
    if "км в мили" in q:
        val = re.findall(r'\d+', q)
        if val: return f"{val[0]} км", f"{round(int(val[0]) * 0.621, 2)} миль"
    return None

# --- ШАПКА ---
d, tm, tk, wm, usd_r, eur_r = get_header_data()
col_logo, col_info = st.columns([1, 4])
with col_logo: st.markdown('<div class="logo">КУСИЦА</div>', unsafe_allow_html=True)
with col_info:
    st.markdown(f"""<div class="informer-box"><div class="informer-pill">📅 {d}</div><div class="informer-pill">🕒 МСК {tm}</div><div class="informer-pill">🇰🇿 КЗ {tk}</div><div class="informer-pill">🌡️ МСК {wm}</div><div class="informer-pill currency-pill">USD {usd_r}₽</div><div class="informer-pill currency-pill">EUR {eur_r}₽</div></div>""", unsafe_allow_html=True)

# --- ПОИСК ---
col_q, col_mic, col_b = st.columns([7, 0.6, 1.4])
with col_q: q = st.text_input("", value=st.session_state.get('q_from_hist', ""), placeholder="Найдётся всё...", key="main_search", label_visibility="collapsed")
with col_mic: 
    if st.button("🎙️"):
        components.html("""<script>
            const rec = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            rec.lang = 'ru-RU'; rec.start();
            rec.onresult = (e) => {
                const t = e.results[0][0].transcript;
                const i = window.parent.document.querySelector('input[data-testid="stTextInput"]');
                i.value = t; i.dispatchEvent(new Event('input', {bubbles:true}));
            };
        </script>""", height=0)
with col_b: btn = st.button("Найти ➔")

# --- ЗАКЛАДКИ (TOP SITES) ---
if not st.session_state.res:
    st.markdown("""
    <div class="sites-grid">
        <a class="site-item" href="https://youtube.com" target="_blank"><div class="site-icon">🔴</div><div class="site-text">YouTube</div></a>
        <a class="site-item" href="https://vk.com" target="_blank"><div class="site-icon">🔵</div><div class="site-text">ВКонтакте</div></a>
        <a class="site-item" href="https://mail.yandex.ru" target="_blank"><div class="site-icon">📧</div><div class="site-text">Почта</div></a>
        <a class="site-item" href="https://market.yandex.ru" target="_blank"><div class="site-icon">🛍️</div><div class="site-text">Маркет</div></a>
        <a class="site-item" href="https://maps.yandex.ru" target="_blank"><div class="site-icon">🗺️</div><div class="site-text">Карты</div></a>
        <a class="site-item" href="https://dzen.ru/games" target="_blank"><div class="site-icon">🎮</div><div class="site-text">Игры</div></a>
    </div>
    """, unsafe_allow_html=True)

# --- ЛОГИКА ---
if (btn or q) and q:
    if st.session_state.get('last_q') != q:
        with st.spinner(" "):
            try:
                s_key = st.secrets["SERPER_API_KEY"]
                sr = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': s_key, 'Content-Type': 'application/json'}, json={"q": q, "hl": "ru"}).json()
                ir = requests.post("https://google.serper.dev/images", headers={'X-API-KEY': s_key}, json={"q": q}).json()
                vr = requests.post("https://google.serper.dev/videos", headers={'X-API-KEY': s_key}, json={"q": q}).json()
                
                links = sr.get('organic', [])
                ans = get_ai_res([{"role":"system","content":"Ты Кусица, эрудированный ассистент. Отвечай подробно и на русском."}, {"role":"user","content":f"Вопрос: {q}\nИнфо: {links[:3]}"}])
                
                st.session_state.res = {"ans": ans, "links": links, "imgs": ir.get('images', []), "vids": vr.get('videos', []), "q": q}
                if q not in st.session_state.history: st.session_state.history.append(q)
                st.session_state.last_q = q
                st.session_state.view_img_idx = None
            except: st.error("Ошибка поиска")

# --- ВЫВОД ---
if st.session_state.res:
    res = st.session_state.res
    # 1. Конвертер
    conv = check_math_and_conv(res['q'], usd_r, eur_r)
    if conv: st.markdown(f'<div class="conv-box"><div style="color:#888;">{conv[0]}</div><div class="conv-val">{conv[1]}</div></div>', unsafe_allow_html=True)

    t1, t2, t3 = st.tabs(["🔍 Поиск", "🖼️ Картинки", "📺 Видео"])
    with t1:
        st.markdown(f'<div class="alice-card"><b>🟣 КУСИЦА АССИСТЕНТ:</b><br><br>{res["ans"]}</div>', unsafe_allow_html=True)
        u_q = st.chat_input("Уточнить у Кусицы...")
        if u_q: st.info(get_ai_res([{"role":"assistant", "content": res['ans']}, {"role":"user", "content": u_q}]))
        
        st.write("---")
        for l in res['links'][:st.session_state.limits['links']]:
            st.markdown(f'<div style="margin-bottom:20px;"><a href="{l["link"]}" target="_blank" style="font-size:19px; color:#1a0dab; text-decoration:none; font-weight:500;">{l["title"]}</a><br><small style="color:#006621;">{l["link"][:80]}...</small><div style="font-size:14px; color:#444; margin-top:5px;">{l.get("snippet","")}</div></div>', unsafe_allow_html=True)
        if st.button("Показать еще ссылки"): st.session_state.limits['links'] += 5; st.rerun()

    with t2:
        imgs = res['imgs']
        if st.session_state.view_img_idx is not None:
            idx = st.session_state.view_img_idx
            st.button("⬅️ Назад к списку", on_click=lambda: setattr(st.session_state, 'view_img_idx', None))
            c1, c2, c3 = st.columns([1, 8, 1])
            with c1: 
                if idx > 0 and st.button("◀️"): st.session_state.view_img_idx -= 1; st.rerun()
            with c2:
                st.image(imgs[idx]['imageUrl'], use_container_width=True)
                st.subheader(imgs[idx].get('title', ''))
                st.link_button(f"Источник: {imgs[idx].get('source', 'Сайт')}", imgs[idx]['link'])
            with c3:
                if idx < len(imgs)-1 and st.button("▶️"): st.session_state.view_img_idx += 1; st.rerun()
        else:
            cols = st.columns(2)
            for i, img in enumerate(imgs[:st.session_state.limits['imgs']]):
                with cols[i % 2]:
                    st.markdown(f'<div class="img-card"><img src="{img["imageUrl"]}" style="width:100%;"><br><small style="padding:5px; display:block;">{img.get("source","")}</small></div>', unsafe_allow_html=True)
                    if st.button(f"Увеличить #{i+1}", key=f"z_{i}"): st.session_state.view_img_idx = i; st.rerun()
            if st.button("Больше картинок"): st.session_state.limits['imgs'] += 10; st.rerun()

    with t3:
        for v in res['vids'][:st.session_state.limits['vids']]:
            col1, col2 = st.columns([1, 2])
            with col1: st.image(v.get('imageUrl', ''))
            with col2:
                st.markdown(f"**{v['title']}**")
                st.link_button("▶️ Смотреть", v['link'])
        if st.button("Больше видео"): st.session_state.limits['vids'] += 4; st.rerun()
else:
    # ГЛАВНАЯ (НОВОСТИ)
    st.write("---")
    st.subheader("Главное сегодня")
    for n in fetch_news(st.secrets.get("SERPER_API_KEY", "")):
        st.markdown(f"📰 [{n['title']}]({n['link']})")

st.markdown("<br><hr><center style='color:#ccc; font-size:10px;'>КУСИЦА • 2024</center>", unsafe_allow_html=True)
