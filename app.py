import streamlit as st
import httpx
from datetime import datetime
import pytz
import uuid

# 1. Настройка страницы
st.set_page_config(page_title="КУСИЦА", page_icon="🔍", layout="wide")

# 2. CSS (Адаптивный дизайн)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #fff; }
    
    .logo { font-size: 32px; font-weight: 900; letter-spacing: -1.5px; margin-bottom: 5px; color: #000; }
    
    .informer-box { display: flex; flex-wrap: wrap; gap: 6px; font-size: 11px; margin-bottom: 15px; }
    .informer-item { background: #f0f0f2; padding: 4px 8px; border-radius: 6px; white-space: nowrap; display: flex; align-items: center; gap: 4px; }
    .currency-red { border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; }

    .stTextInput > div > div > input {
        font-size: 18px !important; padding: 12px !important;
        border-radius: 12px !important; border: 2px solid #ffdb4d !important;
    }
    
    .stButton > button {
        height: 52px; width: 100%; border-radius: 12px;
        background-color: #ffdb4d; color: black; border: none; font-size: 20px; font-weight: bold;
    }

    .answer-card { 
        background: #fff; padding: 20px; border-radius: 15px; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 1px solid #eee; margin-top: 10px; 
    }
    
    .img-card { border-radius: 10px; overflow: hidden; margin-bottom: 10px; border: 1px solid #eee; }
    
    /* Стили вкладок (Табов) */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 40px; white-space: pre-wrap; background-color: #f0f0f2;
        border-radius: 8px; padding: 0px 15px; font-weight: bold; color: #555;
    }
    .stTabs [aria-selected="true"] { background-color: #ffdb4d !important; color: #000 !important; }
    </style>
    """, unsafe_allow_html=True)

# 3. Инициализация памяти
if 'history' not in st.session_state: st.session_state.history = None
if 'images' not in st.session_state: st.session_state.images = []

# 4. Данные шапки
@st.cache_data(ttl=600)
def get_top_data():
    try:
        tz_m = pytz.timezone('Europe/Moscow')
        now_m = datetime.now(tz_m)
        d, t_m = now_m.strftime("%d.%m"), now_m.strftime("%H:%M")
        t_k = datetime.now(pytz.timezone('Asia/Almaty')).strftime("%H:%M")
        w_m = httpx.get("https://wttr.in/Moscow?format=%t", timeout=3).text.strip()
        w_s = httpx.get("https://wttr.in/Saint-Petersburg?format=%t", timeout=3).text.strip()
        curr = httpx.get("https://open.er-api.com/v6/latest/USD", timeout=3).json()
        usd = round(curr['rates']['RUB'], 1)
        return d, t_m, t_k, w_m, w_s, usd
    except: return "??.??", "??:??", "??:??", "?°C", "?°C", "??"

d_m, t_m, t_k, w_m, w_s, u_r = get_top_data()

st.markdown('<div class="logo">КУСИЦА</div>', unsafe_allow_html=True)
st.markdown(f"""
    <div class="informer-box">
        <div class="informer-item">📅 {d_m}</div>
        <div class="informer-item">🕒 МСК {t_m}</div>
        <div class="informer-item">🇰🇿 КЗ {t_k}</div>
        <div class="informer-item">🌡️ МСК {w_m}</div>
        <div class="informer-item">🌡️ СПБ {w_s}</div>
        <div class="informer-item currency-red">USD {u_r}₽</div>
    </div>
    """, unsafe_allow_html=True)

# 5. Функция ИИ (GigaChat)
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
                json={"model": "GigaChat", "messages": msgs, "temperature": 0.7}, timeout=20).json()
            return rs["choices"][0]["message"]["content"]
    except Exception as e: return f"Ошибка нейросети: {str(e)}"

# 6. Поиск
query = st.text_input("", placeholder="Найти в Кусице...", key="main_input", label_visibility="collapsed")
btn_clicked = st.button("Найти ➔")

if (btn_clicked or query) and query:
    if st.session_state.get('last_query') != query:
        with st.spinner(" "):
            try:
                s_api = st.secrets["SERPER_API_KEY"]
                # 1. Поиск текста
                s_res = httpx.post("https://google.serper.dev/search",
                    headers={'X-API-KEY': s_api, 'Content-Type': 'application/json'},
                    json={"q": query, "hl": "ru"}, timeout=15).json()
                
                # 2. Поиск картинок
                img_res = httpx.post("https://google.serper.dev/images",
                    headers={'X-API-KEY': s_api, 'Content-Type': 'application/json'},
                    json={"q": query}, timeout=15).json()
                
                links = s_res.get('organic', [])
                context = "\n".join([f"{l.get('title')}: {l.get('snippet')}" for l in links[:5]])
                ans = get_ai_res([{"role":"system","content":"Ты Кусица. Отвечай кратко."},
                                  {"role":"user","content":f"Вопрос: {query}\nИнфо: {context}"}])
                
                st.session_state.history = {"ans": ans, "links": links, "ctx": context}
                st.session_state.images = img_res.get('images', [])
                st.session_state.last_query = query
            except Exception as e: st.error(f"Ошибка: {e}")

# 7. Вывод результатов через Вкладки (Табы)
if st.session_state.history:
    tab1, tab2 = st.tabs(["🔍 Поиск", "🖼️ Картинки"])
    
    with tab1:
        res = st.session_state.history
        st.markdown(f'<div class="answer-card"><b>КУСИЦА АССИСТЕНТ</b><br><br>{res["ans"]}</div>', unsafe_allow_html=True)
        
        # Уточнение
        u_query = st.text_input("Уточнить...", key="u_input")
        if u_query:
            with st.spinner(" "):
                u_ans = get_ai_res([{"role":"system","content":f"Контекст: {res['ctx']}"},
                                    {"role":"assistant","content":res['ans']},
                                    {"role":"user","content":u_query}])
                st.info(u_ans)

        st.write("---")
        for l in res["links"][:5]:
            st.markdown(f"""<div style="margin-bottom:15px;"><a href="{l.get('link')}" target="_blank" style="color:#1a0dab; font-weight:bold;">{l.get('title')}</a><br><small style="color:#4d5156;">{l.get('snippet')}</small></div>""", unsafe_allow_html=True)

    with tab2:
        if st.session_state.images:
            cols = st.columns(2) # 2 колонки для мобилок
            for idx, img in enumerate(st.session_state.images[:10]):
                with cols[idx % 2]:
                    st.markdown(f'<div class="img-card"><a href="{img.get("link")}" target="_blank"><img src="{img.get("imageUrl")}" style="width:100%"></a></div>', unsafe_allow_html=True)
        else:
            st.write("Картинки не найдены")

st.markdown("<br><center style='color:#ccc; font-size:10px;'>КУСИЦА 2024</center>", unsafe_allow_html=True)
