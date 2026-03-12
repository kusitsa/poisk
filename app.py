import streamlit as st
import httpx
from datetime import datetime
import pytz
import uuid

# 1. Настройка страницы
st.set_page_config(page_title="КУСИЦА", page_icon="🔍", layout="wide")

# 2. Адаптивный CSS (для ПК и Телефонов)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #fff; }

    /* Логотип адаптивный */
    .logo { 
        font-size: 36px; font-weight: 900; color: #000; 
        letter-spacing: -2px; margin-bottom: 10px;
    }

    /* Информеры: на мобилках в ряд с переносом */
    .informer-box { 
        display: flex; flex-wrap: wrap; gap: 8px; 
        font-size: 12px; color: #555; margin-bottom: 20px; 
    }
    .informer-item { 
        background: #f0f0f2; padding: 4px 8px; border-radius: 6px; 
        white-space: nowrap; 
    }
    .currency-red { 
        border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; 
    }

    /* Поисковая строка для мобилок */
    .stTextInput > div > div > input {
        font-size: 18px !important; padding: 15px !important;
        border-radius: 12px !important; border: 2px solid #ffdb4d !important;
    }
    
    /* Кнопка поиска */
    .stButton > button {
        height: 55px; width: 100%; border-radius: 12px;
        background-color: #ffdb4d; color: black; border: none; font-size: 22px;
    }

    /* Карточка ответа */
    .answer-card { 
        background: #fff; padding: 20px; border-radius: 15px; 
        box-shadow: 0 5px 20px rgba(0,0,0,0.05); border: 1px solid #eee; margin-top: 15px; 
    }

    /* Ссылки */
    .source-item { margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #f9f9f9; }
    .source-link { color: #1a0dab; text-decoration: none; font-weight: bold; font-size: 16px; display: block; }
    .source-snippet { color: #4d5156; font-size: 13px; line-height: 1.4; }
    
    /* Убираем лишние отступы Streamlit на мобилках */
    @media (max-width: 640px) {
        .logo { font-size: 28px; text-align: center; }
        .informer-box { justify-content: center; }
    }
    </style>
    """, unsafe_allow_html=True)

# 3. Инициализация сессии
if 'show_more' not in st.session_state: st.session_state.show_more = False
if 'history' not in st.session_state: st.session_state.history = []

# 4. Данные (Время, Погода, Валюта)
@st.cache_data(ttl=600)
def get_header_data():
    tz_m = datetime.now(pytz.timezone('Europe/Moscow')).strftime("%H:%M")
    tz_k = datetime.now(pytz.timezone('Asia/Almaty')).strftime("%H:%M")
    try:
        w_m = httpx.get("https://wttr.in/Moscow?format=%t", timeout=3).text.strip()
        w_s = httpx.get("https://wttr.in/Saint-Petersburg?format=%t", timeout=3).text.strip()
    except: w_m, w_s = "?°C", "?°C"
    try:
        curr = httpx.get("https://open.er-api.com/v6/latest/USD", timeout=3).json()
        usd = round(curr['rates']['RUB'], 1)
        eur = round(usd / (curr['rates']['EUR'] / curr['rates']['USD']), 1)
    except: usd, eur = "??", "??"
    return tz_m, tz_k, w_m, w_s, usd, eur

t_m, t_k, w_m, w_s, u_r, e_r = get_header_data()

# 5. Шапка
st.markdown('<div class="logo">КУСИЦА</div>', unsafe_allow_html=True)
st.markdown(f"""
    <div class="informer-box">
        <div class="informer-item">🕒 МСК {t_m}</div>
        <div class="informer-item">🇰🇿 КЗ {t_k}</div>
        <div class="informer-item">☁️ МСК {w_m}</div>
        <div class="informer-item">☁️ СПБ {w_s}</div>
        <div class="informer-item currency-red">USD {u_r}₽</div>
        <div class="informer-item currency-red">EUR {e_r}₽</div>
    </div>
    """, unsafe_allow_html=True)

# 6. Функции API
def get_giga_answer(msgs):
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

# 7. Поиск
col_query, col_go = st.columns([5, 1])
with col_query:
    q = st.text_input("", placeholder="Найти в Кусице...", label_visibility="collapsed")
with col_go:
    btn = st.button("➔")

if (btn or q) and q:
    if 'last_q' not in st.session_state or st.session_state.last_q != q:
        st.session_state.last_q = q
        st.session_state.show_more = False # Сбрасываем кнопку при новом поиске
        with st.spinner(" "):
            try:
                s_res = httpx.post("https://google.serper.dev/search",
                    headers={'X-API-KEY': st.secrets["SERPER_API_KEY"], 'Content-Type': 'application/json'},
                    json={"q": q, "hl": "ru"}).json()
                links = s_res.get('organic', [])
                context = "\n".join([f"{l.get('title')}: {l.get('snippet')}" for l in links[:5]])
                ans = get_giga_answer([{"role":"system","content":"Ты Кусица. Отвечай кратко."},
                                       {"role":"user","content":f"Вопрос: {q}\nИнфо: {context}"}])
                st.session_state.history = [{"ans": ans, "links": links, "ctx": context}]
            except: st.error("Ошибка связи. Проверьте ключи.")

# 8. Вывод
if st.session_state.history:
    res = st.session_state.history[0]
    
    # Ответ
    st.markdown(f'<div class="answer-card"><b>КУСИЦА АССИСТЕНТ</b><br><br>{res["ans"]}</div>', unsafe_allow_html=True)
    
    # Уточнение
    sub_q = st.text_input("Уточнить детали...", key="sub")
    if sub_q:
        with st.spinner(" "):
            sub_ans = get_giga_answer([{"role":"system","content":f"Контекст: {res['ctx']}"},
                                       {"role":"assistant","content":res['ans']},
                                       {"role":"user","content":sub_q}])
            st.info(sub_ans)

    # Ссылки
    st.write("---")
    st.subheader("🌐 Источники")
    
    # Сначала показываем 2 ссылки
    visible_links = res["links"] if st.session_state.show_more else res["links"][:2]
    
    for l in visible_links:
        st.markdown(f"""
        <div class="source-item">
            <a class="source-link" href="{l.get('link')}" target="_blank">{l.get('title')}</a>
            <div class="source-snippet">{l.get('snippet')}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Кнопка Показать еще
    if not st.session_state.show_more and len(res["links"]) > 2:
        if st.button("Показать еще ссылки"):
            st.session_state.show_more = True
            st.rerun()

st.markdown("<br><center style='color:#ccc; font-size:10px;'>КУСИЦА ПОИСК 2024</center>", unsafe_allow_html=True)
