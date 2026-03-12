import streamlit as st
import requests
import uuid
import pytz
from datetime import datetime

# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ
st.set_page_config(page_title="КУСИЦА", page_icon="🔍", layout="wide")

# 2. АДАПТИВНЫЙ ДИЗАЙН (CSS)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #fff; }
    
    /* Лого и Хедер */
    .logo { font-size: 32px; font-weight: 900; letter-spacing: -2px; color: #000; }
    .informer-box { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 15px; }
    .informer-item { background: #f2f2f4; padding: 4px 8px; border-radius: 8px; font-size: 11px; color: #555; white-space: nowrap; }
    .currency-pill { border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; }

    /* Поиск */
    .stTextInput > div > div > input {
        font-size: 18px !important; padding: 15px !important;
        border-radius: 15px !important; border: 2px solid #ffdb4d !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .stButton > button {
        height: 52px; width: 100%; border-radius: 15px;
        background-color: #ffdb4d; color: black; border: none; font-size: 20px; font-weight: bold;
    }

    /* Мобильная адаптация для карточек */
    .result-card { margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid #eee; }
    .result-title { font-size: 18px; color: #1a0dab; text-decoration: none; font-weight: 500; }
    .result-url { color: #006621; font-size: 12px; display: block; word-break: break-all; }
    
    /* Карточка ответа ИИ */
    .alice-card { 
        background: #fdfdff; padding: 20px; border-radius: 15px; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); border-left: 5px solid #8e44ad; margin: 15px 0;
        font-size: 16px; line-height: 1.5;
    }

    /* Галерея картинок */
    .image-box { border: 1px solid #eee; border-radius: 12px; padding: 8px; margin-bottom: 15px; height: 100%; }
    .image-title { font-size: 13px; font-weight: 600; margin-top: 5px; color: #333; height: 40px; overflow: hidden; }
    .image-source { font-size: 11px; color: #006621; text-decoration: none; }

    @media (max-width: 640px) {
        .logo { font-size: 26px; }
        .stButton > button { height: 45px; font-size: 18px; }
    }
    </style>
    """, unsafe_allow_html=True)

# 3. ИНИЦИАЛИЗАЦИЯ ПАМЯТИ
if 'search_results' not in st.session_state: st.session_state.search_results = None
if 'img_results' not in st.session_state: st.session_state.img_results = None
if 'link_limit' not in st.session_state: st.session_state.link_limit = 5
if 'img_limit' not in st.session_state: st.session_state.img_limit = 10
if 'chat_history' not in st.session_state: st.session_state.chat_history = []

# 4. ФУНКЦИИ (ДАННЫЕ И API)
@st.cache_data(ttl=600)
def get_header_info():
    try:
        tz_m, tz_k = pytz.timezone('Europe/Moscow'), pytz.timezone('Asia/Almaty')
        w = requests.get("https://wttr.in/Moscow?format=%t", timeout=3).text.strip()
        c = requests.get("https://open.er-api.com/v6/latest/USD", timeout=3).json()
        usd = round(c['rates']['RUB'], 1)
        eur = round(usd / (c['rates']['EUR'] / c['rates']['USD']), 1)
        return datetime.now(tz_m).strftime("%d.%m"), datetime.now(tz_m).strftime("%H:%M"), datetime.now(tz_k).strftime("%H:%M"), w, usd, eur
    except: return "??", "??", "??", "?", "??", "??"

def get_ai_res(msgs):
    try:
        auth = st.secrets["GIGACHAT_CREDENTIALS"]
        tk_res = requests.post("https://ngw.devices.sberbank.ru:9443/api/v2/oauth", 
                             headers={'Authorization': f'Basic {auth}', 'RqUID': str(uuid.uuid4()), 'Content-Type': 'application/x-www-form-urlencoded'},
                             data={'scope': 'GIGACHAT_API_PERS'}, verify=False, timeout=10)
        if tk_res.status_code == 401: return "ERROR_AUTH_GIGA"
        token = tk_res.json()['access_token']
        chat_res = requests.post("https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                               headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
                               json={"model": "GigaChat", "messages": msgs, "temperature": 0.7}, verify=False, timeout=20)
        return chat_res.json()['choices'][0]['message']['content']
    except: return "Ошибка связи с ИИ"

# --- ШАПКА ---
d, tm, tk, w, u, e = get_header_info()
st.markdown(f'<div class="logo">КУСИЦА</div>', unsafe_allow_html=True)
st.markdown(f"""
    <div class="informer-box">
        <div class="informer-item">📅 {d}</div><div class="informer-item">🕒 МСК {tm}</div>
        <div class="informer-item">🇰🇿 КЗ {tk}</div><div class="informer-item">🌡️ {w}</div>
        <div class="informer-item currency-pill">USD {u}₽</div><div class="informer-item currency-pill">EUR {e}₽</div>
    </div>
    """, unsafe_allow_html=True)

# --- ПОИСК ---
query = st.text_input("", placeholder="Найдётся всё...", key="main_search", label_visibility="collapsed")
if st.button("Найти ответ ➔") or (query and st.session_state.get('last_q') != query):
    if query:
        with st.spinner(" "):
            try:
                s_key = st.secrets["SERPER_API_KEY"]
                headers = {'X-API-KEY': s_key, 'Content-Type': 'application/json'}
                # Текст
                r_text = requests.post("https://google.serper.dev/search", headers=headers, json={"q": query, "hl": "ru", "gl": "ru"}, timeout=10)
                if r_text.status_code == 401: st.error("Ошибка: Неверный SERPER_API_KEY"); st.stop()
                # Картинки
                r_img = requests.post("https://google.serper.dev/images", headers=headers, json={"q": query}, timeout=10)
                
                st.session_state.search_results = r_text.json().get('organic', [])
                st.session_state.img_results = r_img.json().get('images', [])
                st.session_state.last_q = query
                
                # Первый ответ ИИ
                ctx = "\n".join([l.get('snippet','') for l in st.session_state.search_results[:3]])
                ans = get_ai_res([{"role":"user", "content": f"Вопрос: {query}\nИнформация: {ctx}"}])
                if ans == "ERROR_AUTH_GIGA": st.error("Ошибка: Неверный GIGACHAT_CREDENTIALS"); st.stop()
                st.session_state.chat_history = [{"role": "assistant", "content": ans}]
            except Exception as ex: st.error(f"Сбой: {ex}")

# --- РЕЗУЛЬТАТЫ ---
if st.session_state.search_results:
    tab1, tab2 = st.tabs(["🔍 Поиск", "🖼️ Картинки"])
    
    with tab1:
        # Карточка ответа ИИ
        st.markdown(f'<div class="alice-card"><b>Кусица Ассистент:</b><br><br>{st.session_state.chat_history[0]["content"]}</div>', unsafe_allow_html=True)
        
        # Уточняющий вопрос
        with st.expander("💬 Уточнить у ассистента"):
            u_q = st.text_input("Ваш вопрос...", key="chat_input")
            if u_q:
                with st.spinner(" "):
                    new_ans = get_ai_res([{"role":"assistant", "content": st.session_state.chat_history[0]["content"]}, {"role":"user", "content": u_q}])
                    st.write(f"**Ответ:** {new_ans}")

        st.write("---")
        # Список ссылок
        for l in st.session_state.search_results[:st.session_state.link_limit]:
            st.markdown(f"""
            <div class="result-card">
                <a class="result-title" href="{l['link']}" target="_blank">{l['title']}</a>
                <span class="result-url">{l['link'][:70]}...</span>
                <div style="font-size:14px; color:#444;">{l.get('snippet','')}</div>
            </div>
            """, unsafe_allow_html=True)
        
        if st.session_state.link_limit < len(st.session_state.search_results):
            if st.button("Показать еще ссылки"):
                st.session_state.link_limit += 10
                st.rerun()

    with tab2:
        imgs = st.session_state.img_results
        if not imgs: st.write("Картинки не найдены")
        else:
            cols = st.columns(2 if st.session_state.get('mobile', False) else 4) # Адаптация колонок
            for i, img in enumerate(imgs[:st.session_state.img_limit]):
                with cols[i % (2 if st.session_state.get('mobile', False) else 4)]:
                    st.markdown(f"""
                    <div class="image-box">
                        <a href="{img['link']}" target="_blank">
                            <img src="{img['imageUrl']}" style="width:100%; border-radius:8px; height:150px; object-fit:cover;">
                        </a>
                        <div class="image-title">{img['title'][:40]}...</div>
                        <a class="image-source" href="{img['link']}" target="_blank">🔗 {img['source']}</a>
                    </div>
                    """, unsafe_allow_html=True)
            
            if st.session_state.img_limit < len(imgs):
                if st.button("Загрузить еще картинки"):
                    st.session_state.img_limit += 12
                    st.rerun()
else:
    # НОВОСТИ НА ГЛАВНОЙ
    st.write("---")
    st.subheader("Главное сегодня")
    try:
        n_res = requests.post("https://google.serper.dev/news", headers={'X-API-KEY': st.secrets["SERPER_API_KEY"]}, json={"q": "новости сегодня Россия", "hl": "ru"}, timeout=5).json()
        for n in n_res.get('news', [])[:5]:
            st.markdown(f"📰 [{n['title']}]({n['link']})")
    except: st.write("Загрузка новостей...")

st.markdown("<br><hr><center style='color:#999; font-size:10px;'>КУСИЦА • 2024</center>", unsafe_allow_html=True)
