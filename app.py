import streamlit as st
import requests
import uuid
import pytz
import re
from datetime import datetime
import streamlit.components.v1 as components

# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ
st.set_page_config(page_title="КУСИЦА — Супер Поиск", page_icon="🔍", layout="wide")

# 2. МАКСИМАЛЬНЫЙ CSS ДИЗАЙН (Все твои пожелания)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #fff; color: #000; }
    
    .logo { font-size: 38px; font-weight: 900; letter-spacing: -2.5px; color: #000; margin-bottom: 5px; }
    
    /* Информеры в шапке */
    .informer-box { display: flex; flex-wrap: wrap; gap: 8px; font-size: 11px; margin-bottom: 20px; }
    .informer-pill { background: #f2f2f4; padding: 4px 10px; border-radius: 12px; display: flex; align-items: center; gap: 4px; color: #555; }
    .currency-red { border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; padding: 2px 8px; border-radius: 10px; }

    /* Поисковая строка Яндекса */
    .stTextInput > div > div > input {
        font-size: 18px !important; padding: 22px 25px !important;
        border-radius: 28px !important; border: 2px solid #ffdb4d !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    }
    .stButton > button {
        height: 60px; width: 100%; border-radius: 28px;
        background-color: #ffdb4d !important; color: black !important; font-size: 24px; font-weight: bold; border: none !important;
    }

    /* Конвертер Валют */
    .converter-card {
        background: #fff; padding: 25px; border-radius: 20px; border: 2px solid #ffdb4d;
        text-align: center; margin: 15px 0; box-shadow: 0 10px 30px rgba(0,0,0,0.05);
    }
    .converter-value { font-size: 42px; font-weight: 900; color: #000; }

    /* Ассистент (Фиолетовый) */
    .alice-card { 
        background: #fdfdff; padding: 25px; border-radius: 22px; 
        box-shadow: 0 10px 40px rgba(0,0,0,0.05); border-left: 6px solid #8e44ad; margin-top: 15px; 
        line-height: 1.6; font-size: 18px;
    }

    /* Ссылки и Картинки */
    .search-title { font-size: 20px; color: #1a0dab; text-decoration: none; font-weight: 500; }
    .img-box { border: 1px solid #eee; border-radius: 12px; padding: 5px; text-align: center; background: #fff; }
    
    @media (max-width: 640px) {
        .logo { font-size: 28px; }
        .informer-box { justify-content: flex-start; }
    }
    </style>
    """, unsafe_allow_html=True)

# 3. ИНИЦИАЛИЗАЦИЯ ПАМЯТИ
if 'res' not in st.session_state: st.session_state.res = None
if 'history' not in st.session_state: st.session_state.history = []
if 'limits' not in st.session_state: st.session_state.limits = {"links": 3, "imgs": 8, "vids": 4}
if 'view_img_idx' not in st.session_state: st.session_state.view_img_idx = None

# 4. ФУНКЦИИ (ДАННЫЕ И ИИ)
@st.cache_data(ttl=600)
def get_header_data():
    try:
        tz_m, tz_k = pytz.timezone('Europe/Moscow'), pytz.timezone('Asia/Almaty')
        now = datetime.now(tz_m)
        w_m = requests.get("https://wttr.in/Moscow?format=%t", timeout=2).text.strip()
        w_s = requests.get("https://wttr.in/Saint-Petersburg?format=%t", timeout=2).text.strip()
        curr = requests.get("https://open.er-api.com/v6/latest/USD", timeout=2).json()
        usd = round(curr['rates']['RUB'], 2)
        eur = round(usd / (curr['rates']['EUR'] / curr['rates']['USD']), 2)
        return now.strftime("%d.%m"), now.strftime("%H:%M"), datetime.now(tz_k).strftime("%H:%M"), w_m, w_s, usd, eur
    except: return "??", "??", "??", "?", "?", "??", "??"

def get_ai_answer(msgs):
    try:
        auth = st.secrets["GIGACHAT_CREDENTIALS"]
        # 1. Токен (verify=False для стабильности)
        tk_res = requests.post("https://ngw.devices.sberbank.ru:9443/api/v2/oauth", 
                               headers={'Authorization': f'Basic {auth}', 'RqUID': str(uuid.uuid4()), 'Content-Type': 'application/x-www-form-urlencoded'},
                               data={'scope': 'GIGACHAT_API_PERS'}, verify=False, timeout=10).json()
        token = tk_res['access_token']
        # 2. Ответ
        chat_res = requests.post("https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                               headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
                               json={"model": "GigaChat", "messages": msgs, "temperature": 0.7}, verify=False, timeout=20).json()
        return chat_res['choices'][0]['message']['content']
    except Exception as e:
        return f"Кусица призадумалась... (Если пишет 429 - подождите 10 сек). Ошибка: {e}"

@st.cache_data(ttl=1800)
def fetch_news(key):
    try:
        r = requests.post("https://google.serper.dev/news", headers={'X-API-KEY': key}, json={"q": "главные новости", "gl": "ru", "hl": "ru"}).json()
        return r.get('news', [])[:5]
    except: return []

def check_currency_conversion(query, usd_val, eur_val):
    q = query.lower()
    match = re.search(r'(\d+)\s*(доллар|usd|бакс)', q)
    if match: return f"{match.group(1)} USD", f"{round(int(match.group(1)) * usd_val, 2)} ₽"
    match_eur = re.search(r'(\d+)\s*(евро|eur)', q)
    if match_eur: return f"{match_eur.group(1)} EUR", f"{round(int(match_eur.group(1)) * eur_val, 2)} ₽"
    return None

# --- ШАПКА ---
d, tm, tk, wm, ws, usd_r, eur_r = get_header_data()
col_logo, col_info = st.columns([1, 4])
with col_logo: st.markdown('<div class="logo">КУСИЦА</div>', unsafe_allow_html=True)
with col_info:
    st.markdown(f"""
    <div class="informer-box">
        <div class="informer-pill">📅 {d}</div><div class="informer-pill">🕒 МСК {tm}</div>
        <div class="informer-pill">🇰🇿 КЗ {tk}</div><div class="informer-pill">🌡️ МСК {wm}</div>
        <div class="informer-pill">🌡️ СПБ {ws}</div>
        <div class="currency-red">USD {usd_r}₽</div><div class="currency-red">EUR {eur_r}₽</div>
    </div>
    """, unsafe_allow_html=True)

# --- ПОИСК + ГОЛОС ---
col_q, col_mic, col_b = st.columns([7, 0.5, 1])
with col_q: q = st.text_input("", placeholder="Найдётся всё...", key="main_search", label_visibility="collapsed")
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
with col_b: btn = st.button("➔")

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
                h = {'X-API-KEY': s_key, 'Content-Type': 'application/json'}
                sr = requests.post("https://google.serper.dev/search", headers=h, json={"q": q, "hl": "ru"}).json()
                ir = requests.post("https://google.serper.dev/images", headers=h, json={"q": q}).json()
                vr = requests.post("https://google.serper.dev/videos", headers=h, json={"q": q}).json()
                links = sr.get('organic', [])
                
                # Умный ассистент (GigaChat)
                ans = get_ai_answer([
                    {"role": "system", "content": "Ты — Кусица, невероятно умный и подробный ассистент Яндекса. Не ленись, пиши подробно."},
                    {"role": "user", "content": f"Вопрос: {q}\nДанные из сети: {links[:5]}"}
                ])
                
                st.session_state.res = {"ans": ans, "links": links, "imgs": ir.get('images', []), "vids": vr.get('videos', []), "q": q}
                if q not in st.session_state.history: st.session_state.history.append(q)
                st.session_state.last_q = q
                st.session_state.limits = {"links": 3, "imgs": 8, "vids": 4}
                st.session_state.view_img_idx = None
            except: st.error("Ошибка поиска")

# --- ВЫВОД РЕЗУЛЬТАТОВ ---
if st.session_state.res:
    res = st.session_state.res
    # Умный Конвертер
    conv = check_currency_conversion(res['q'], usd_r, eur_r)
    if conv: st.markdown(f'<div class="converter-card"><div style="color:#888;">{conv[0]}</div><div class="converter-value">{conv[1]}</div></div>', unsafe_allow_html=True)

    t1, t2, t3 = st.tabs(["🔍 Поиск", "🖼️ Картинки", "📺 Видео"])
    
    with t1:
        st.markdown(f'<div class="alice-card"><b>🟣 КУСИЦА АССИСТЕНТ</b><br><br>{res["ans"]}</div>', unsafe_allow_html=True)
        # Уточнение
        with st.expander("💬 Уточнить у ассистента"):
            u_q = st.text_input("Задайте вопрос...")
            if u_q: st.info(get_ai_answer([{"role":"assistant", "content": res['ans']}, {"role":"user", "content": u_q}]))
        
        st.write("---")
        for l in res['links'][:st.session_state.limits['links']]:
            st.markdown(f'<div style="margin-bottom:20px;"><a class="search-title" href="{l["link"]}" target="_blank">{l["title"]}</a><br><small style="color:#006621;">{l["link"][:80]}...</small><div style="font-size:14px; color:#444;">{l.get("snippet","")}</div></div>', unsafe_allow_html=True)
        if st.button("Показать еще ссылки"): st.session_state.limits['links'] += 5; st.rerun()

    with t2:
        imgs = res['imgs']
        if st.session_state.view_img_idx is not None:
            idx = st.session_state.view_img_idx
            st.button("⬅️ Назад", on_click=lambda: setattr(st.session_state, 'view_img_idx', None))
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
                    st.markdown(f'<div class="img-box"><img src="{img["imageUrl"]}" style="width:100%; border-radius:10px;"><br><small>{img.get("source","")}</small></div>', unsafe_allow_html=True)
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
