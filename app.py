import streamlit as st
import httpx
from datetime import datetime
import pytz
import uuid

# 1. Настройка страницы
st.set_page_config(page_title="КУСИЦА ПОИСК", page_icon="🔍", layout="wide")

# 2. Яндекс-стайл CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .logo { font-size: 42px; font-weight: 900; color: #000; letter-spacing: -2px; }
    .informer-box { display: flex; flex-wrap: wrap; gap: 15px; font-size: 14px; color: #555; margin-top: 5px; }
    .informer-item { display: flex; align-items: center; gap: 5px; background: #f5f5f7; padding: 4px 10px; border-radius: 8px; }
    .currency-red-box { border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; }
    .stTextInput > div > div > input {
        font-size: 20px !important; padding: 25px 20px !important;
        border-radius: 12px !important; border: 2px solid #ffdb4d !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.07);
    }
    .stButton > button {
        height: 64px; width: 100%; border-radius: 12px;
        background-color: #ffdb4d; color: black; border: none; font-size: 28px; font-weight: bold;
    }
    .answer-card { background: white; padding: 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); border: 1px solid #eee; margin-top: 30px; }
    </style>
    """, unsafe_allow_html=True)

# 3. Функции для получения данных
def get_data():
    m_time = datetime.now(pytz.timezone('Europe/Moscow')).strftime("%H:%M")
    k_time = datetime.now(pytz.timezone('Asia/Almaty')).strftime("%H:%M")
    try:
        w_m = httpx.get("https://wttr.in/Moscow?format=%t", timeout=5).text.strip()
        w_s = httpx.get("https://wttr.in/Saint-Petersburg?format=%t", timeout=5).text.strip()
    except: w_m, w_s = "?°C", "?°C"
    try:
        curr = httpx.get("https://open.er-api.com/v6/latest/USD", timeout=5).json()
        usd = round(curr['rates']['RUB'], 1)
        eur = round(usd / (curr['rates']['EUR'] / curr['rates']['USD']), 1)
    except: usd, eur = "??", "??"
    return m_time, k_time, w_m, w_s, usd, eur

m_t, k_t, m_w, s_w, usd_r, eur_r = get_data()

# 4. Шапка
col_l, col_i = st.columns([1, 4])
with col_l: st.markdown('<div class="logo">КУСИЦА</div>', unsafe_allow_html=True)
with col_i:
    st.markdown(f"""
    <div class="informer-box">
        <div class="informer-item">🕒 МСК <b>{m_t}</b></div>
        <div class="informer-item">🇰🇿 КЗ <b>{k_t}</b></div>
        <div class="informer-item">☁️ МСК <b>{m_w}</b></div>
        <div class="informer-item">☁️ СПБ <b>{s_w}</b></div>
        <div class="informer-item currency-red-box">USD {usd_r}₽</div>
        <div class="informer-item currency-red-box">EUR {eur_r}₽</div>
    </div>
    """, unsafe_allow_html=True)

# 5. Поиск
st.write("")
col_search, col_btn = st.columns([7, 1])
with col_search: query = st.text_input("", placeholder="Спроси Кусицу...", label_visibility="collapsed")
with col_btn: search_clicked = st.button("➔")

# 6. Работа с GigaChat API
def get_gigachat_answer(prompt_text):
    auth_data = st.secrets["GIGACHAT_CREDENTIALS"]
    rquid = str(uuid.uuid4())
    
    # Шаг 1: Получаем токен
    with httpx.Client(verify=False) as client:
        auth_res = client.post(
            "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            headers={
                "Authorization": f"Basic {auth_data}",
                "Content-Type": "application/x-www-form-urlencoded",
                "RqUID": rquid
            },
            data={"scope": "GIGACHAT_API_PERS"}
        )
        token = auth_res.json()["access_token"]
        
        # Шаг 2: Запрос к нейросети
        chat_res = client.post(
            "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "model": "GigaChat",
                "messages": [{"role": "user", "content": prompt_text}],
                "temperature": 0.7
            }
        )
        return chat_res.json()["choices"][0]["message"]["content"]

# 7. Логика
if (search_clicked or query) and query:
    try:
        with st.spinner("Ищу ответы..."):
            # Поиск через Serper
            s_res = httpx.post(
                "https://google.serper.dev/search",
                headers={'X-API-KEY': st.secrets["SERPER_API_KEY"], 'Content-Type': 'application/json'},
                json={"q": query, "hl": "ru"}
            ).json()
            context = "\n".join([r.get('snippet', '') for r in s_res.get('organic', [])[:5]])
            
            # Ответ GigaChat
            full_prompt = f"Вопрос: {query}. Данные интернета: {context}. Ответь кратко."
            answer = get_gigachat_answer(full_prompt)
            
            st.markdown(f'<div class="answer-card"><b>КУСИЦА АССИСТЕНТ:</b><br><br>{answer}</div>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Ошибка: {str(e)}. Проверьте ключи GIGACHAT_CREDENTIALS и SERPER_API_KEY.")

st.markdown("<br><hr><center>КУСИЦА 2024</center>", unsafe_allow_html=True)
