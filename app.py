import streamlit as st
import requests
import uuid
import pytz
import re
from datetime import datetime
import streamlit.components.v1 as components

# 1. КОНФИГУРАЦИЯ И СТИЛИ
st.set_page_config(page_title="КУСИЦА — Супер Поиск", page_icon="🔍", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #fff; color: #000; }
    
    .logo { font-size: 38px; font-weight: 900; letter-spacing: -2.5px; color: #000; margin-bottom: 5px; }
    .informer-box { display: flex; flex-wrap: wrap; gap: 8px; font-size: 11px; margin-bottom: 20px; }
    .informer-pill { background: #f2f2f4; padding: 4px 10px; border-radius: 12px; display: flex; align-items: center; gap: 4px; color: #555; }
    .currency-red { border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; padding: 2px 8px; border-radius: 10px; }

    /* Конвертер Валют (Большая карточка) */
    .converter-card {
        background: linear-gradient(135deg, #fff 0%, #f9f9f9 100%);
        padding: 30px; border-radius: 25px; border: 2px solid #ffdb4d;
        margin: 20px 0; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.05);
    }
    .converter-value { font-size: 48px; font-weight: 900; color: #000; margin: 10px 0; }

    /* Поиск */
    .stTextInput > div > div > input {
        font-size: 18px !important; padding: 20px 25px !important;
        border-radius: 28px !important; border: 2px solid #ffdb4d !important;
    }
    .stButton > button {
        height: 56px; width: 100%; border-radius: 28px;
        background-color: #ffdb4d; color: black; border: none; font-size: 24px; font-weight: bold;
    }
    
    .alice-card { 
        background: #fdfdff; padding: 25px; border-radius: 22px; 
        box-shadow: 0 10px 40px rgba(0,0,0,0.05); border-left: 6px solid #8e44ad; margin-top: 15px; 
        line-height: 1.6; font-size: 18px;
    }
    
    .img-box { border: 1px solid #eee; border-radius: 12px; padding: 5px; text-align: center; background: #fff; height: 100%; }
    </style>
    """, unsafe_allow_html=True)

# 2. ПАМЯТЬ
if 'res' not in st.session_state: st.session_state.res = None
if 'history' not in st.session_state: st.session_state.history = []
if 'limits' not in st.session_state: st.session_state.limits = {"links": 3, "imgs": 8, "vids": 4}
if 'view_img_idx' not in st.session_state: st.session_state.view_img_idx = None

# 3. ФУНКЦИИ
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

def get_ai_res(msgs):
    try:
        auth = st.secrets["GIGACHAT_CREDENTIALS"]
        tk_r = requests.post("https://ngw.devices.sberbank.ru:9443/api/v2/oauth", 
                           headers={'Authorization': f'Basic {auth}', 'RqUID': str(uuid.uuid4()), 'Content-Type': 'application/x-www-form-urlencoded'},
                           data={'scope': 'GIGACHAT_API_PERS'}, verify=False, timeout=10).json()
        token = tk_r['access_token']
        chat_r = requests.post("https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                             headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
                             json={"model": "GigaChat", "messages": msgs, "temperature": 0.7}, verify=False, timeout=20).json()
        return chat_r['choices'][0]['message']['content']
    except: return "Ошибка ассистента."

# --- ГОЛОСОВОЙ ВВОД (JS Компонент) ---
def voice_input():
    components.html("""
        <script>
        const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        recognition.lang = 'ru-RU';
        recognition.onresult = (event) => {
            const text = event.results[0][0].transcript;
            window.parent.postMessage({type: 'streamlit:set_widget_value', key: 'main_search', value: text}, '*');
            const btn = window.parent.document.querySelector('button[kind="primary"]');
            if(btn) btn.click();
        };
        window.parent.document.addEventListener('voice_start', () => recognition.start());
        </script>
    """, height=0)

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

# --- ПОИСК ---
col_q, col_mic, col_b = st.columns([7, 0.5, 1])
with col_q: 
    q = st.text_input("", placeholder="Найдётся всё...", key="main_search", label_visibility="collapsed")
with col_mic:
    if st.button("🎙️"):
        st.write('<script>window.parent.document.dispatchEvent(new Event("voice_start"));</script>', unsafe_allow_html=True)
        voice_input()
with col_b: btn = st.button("➔")

# --- ЛОГИКА КОНВЕРТЕРА ВАЛЮТ ---
def check_currency_conversion(query, usd_val, eur_val):
    q = query.lower()
    match = re.search(r'(\d+)\s*(доллар|usd|бакс)', q)
    if match:
        amount = int(match.group(1))
        res = round(amount * usd_val, 2)
        return f"{amount} USD", f"{res} ₽"
    match_eur = re.search(r'(\d+)\s*(евро|eur)', q)
    if match_eur:
        amount = int(match_eur.group(1))
        res = round(amount * eur_val, 2)
        return f"{amount} EUR", f"{res} ₽"
    return None

# --- ИСТОРИЯ В САЙДБАРЕ ---
with st.sidebar:
    st.title("📜 История")
    for h in reversed(st.session_state.history[-5:]):
        st.button(f"🔍 {h}", key=f"h_{h}", on_click=lambda h=h: setattr(st.session_state, 'query_from_history', h))

# --- ЛОГИКА ПОИСКА ---
if (btn or q) and q:
    if st.session_state.get('last_q') != q:
        with st.spinner(" "):
            try:
                s_key = st.secrets["SERPER_API_KEY"]
                sr = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': s_key}, json={"q": q, "hl": "ru"}).json()
                ir = requests.post("https://google.serper.dev/images", headers={'X-API-KEY': s_key}, json={"q": q}).json()
                vr = requests.post("https://google.serper.dev/videos", headers={'X-API-KEY': s_key}, json={"q": q}).json()
                
                links = sr.get('organic', [])
                ans = get_ai_res([
                    {"role": "system", "content": "Ты — Кусица, эрудированный ассистент Яндекса. Отвечай подробно и интересно."},
                    {"role": "user", "content": f"Запрос: {q}\nДанные: {links[:5]}"}
                ])
                st.session_state.res = {"ans": ans, "links": links, "imgs": ir.get('images', []), "vids": vr.get('videos', []), "q": q, "suggest": sr.get('peopleAlsoAsk', [])}
                if q not in st.session_state.history: st.session_state.history.append(q)
                st.session_state.last_q = q
            except: st.error("Ошибка поиска")

# --- ВЫВОД РЕЗУЛЬТАТОВ ---
if st.session_state.res:
    # 1. Сначала проверяем Конвертер
    conv = check_currency_conversion(st.session_state.res['q'], usd_r, eur_r)
    if conv:
        st.markdown(f"""<div class="converter-card"><div style="color:#888;">{conv[0]} по курсу КУСИЦЫ</div><div class="converter-value">{conv[1]}</div></div>""", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🔍 Поиск", "🖼️ Картинки", "📺 Видео"])
    
    with tab1:
        st.markdown(f'<div class="alice-card"><div style="color:#8e44ad; font-weight:bold; margin-bottom:10px;">🟣 КУСИЦА АССИСТЕНТ</div>{st.session_state.res["ans"]}</div>', unsafe_allow_html=True)
        
        with st.expander("💬 Уточнить у ассистента"):
            u_q = st.text_input("Ваш вопрос...")
            if u_q: st.info(get_ai_res([{"role":"assistant", "content": st.session_state.res['ans']}, {"role":"user", "content": u_q}]))

        st.write("---")
        for l in st.session_state.res['links'][:st.session_state.limits['links']]:
            st.markdown(f'<div style="margin-bottom:20px;"><a href="{l["link"]}" target="_blank" style="font-size:19px; color:#1a0dab; text-decoration:none;">{l["title"]}</a><br><small style="color:#006621;">{l["link"][:80]}...</small><div style="font-size:14px; color:#444;">{l.get("snippet","")}</div></div>', unsafe_allow_html=True)
        if st.button("Показать еще ссылки"): st.session_state.limits['links'] += 5; st.rerun()

    with tab2:
        imgs = st.session_state.res['imgs']
        if st.session_state.view_img_idx is not None:
            idx = st.session_state.view_img_idx
            st.button("⬅️ Галерея", on_click=lambda: setattr(st.session_state, 'view_img_idx', None))
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
                    if st.button(f"Увеличить #{i+1}", key=f"img_z_{i}"): st.session_state.view_img_idx = i; st.rerun()
            if st.button("Больше картинок"): st.session_state.limits['imgs'] += 10; st.rerun()

    with tab3:
        for v in st.session_state.res['vids'][:st.session_state.limits['vids']]:
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
