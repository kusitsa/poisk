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
    .logo { font-size: 42px; font-weight: 900; color: #000; letter-spacing: -2px; text-decoration: none; }
    .informer-box { display: flex; flex-wrap: wrap; gap: 15px; font-size: 14px; color: #555; margin-top: 5px; }
    .informer-item { display: flex; align-items: center; gap: 5px; background: #f5f5f7; padding: 4px 10px; border-radius: 8px; }
    .currency-red-box { border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; }
    
    /* Стилизация поиска */
    .stTextInput > div > div > input {
        font-size: 20px !important; padding: 25px 20px !important;
        border-radius: 12px !important; border: 2px solid #ffdb4d !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.07);
    }
    .stButton > button {
        height: 64px; width: 100%; border-radius: 12px;
        background-color: #ffdb4d; color: black; border: none; font-size: 28px; font-weight: bold;
    }
    
    /* Карточки результатов */
    .answer-card { background: #fff; padding: 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); border: 1px solid #eee; margin-top: 20px; }
    .source-link { color: #1a0dab; text-decoration: none; font-weight: bold; font-size: 18px; }
    .source-link:hover { text-decoration: underline; }
    .source-snippet { color: #4d5156; font-size: 14px; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# 3. Инициализация сессии (чтобы хранить контекст)
if 'history' not in st.session_state:
    st.session_state.history = []
if 'context' not in st.session_state:
    st.session_state.context = ""

# 4. Функции для данных
def get_data():
    m_t = datetime.now(pytz.timezone('Europe/Moscow')).strftime("%H:%M")
    k_t = datetime.now(pytz.timezone('Asia/Almaty')).strftime("%H:%M")
    try:
        w_m = httpx.get("https://wttr.in/Moscow?format=%t", timeout=5).text.strip()
        w_s = httpx.get("https://wttr.in/Saint-Petersburg?format=%t", timeout=5).text.strip()
    except: w_m, w_s = "?°C", "?°C"
    try:
        curr = httpx.get("https://open.er-api.com/v6/latest/USD", timeout=5).json()
        usd = round(curr['rates']['RUB'], 1)
        eur = round(usd / (curr['rates']['EUR'] / curr['rates']['USD']), 1)
    except: usd, eur = "??", "??"
    return m_t, k_t, w_m, w_s, usd, eur

m_t, k_t, m_w, s_w, usd_r, eur_r = get_data()

# 5. Шапка (Лого + Информеры)
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

# 6. Взаимодействие с GigaChat
def get_gigachat_answer(messages):
    auth_data = st.secrets["GIGACHAT_CREDENTIALS"]
    rquid = str(uuid.uuid4())
    with httpx.Client(verify=False) as client:
        # Токен
        token = client.post("https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            headers={"Authorization": f"Basic {auth_data}", "Content-Type": "application/x-www-form-urlencoded", "RqUID": rquid},
            data={"scope": "GIGACHAT_API_PERS"}).json()["access_token"]
        # Чат
        res = client.post("https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"model": "GigaChat", "messages": messages, "temperature": 0.7}).json()
        return res["choices"][0]["message"]["content"]

# 7. Главный Поиск
st.write("")
col_search, col_btn = st.columns([7, 1])
with col_search:
    query = st.text_input("", placeholder="Спроси Кусицу...", label_visibility="collapsed", key="main_search")
with col_btn:
    search_clicked = st.button("➔")

if (search_clicked or query) and query:
    if 'last_query' not in st.session_state or st.session_state.last_query != query:
        st.session_state.last_query = query
        try:
            with st.spinner(" "):
                # Поиск через Serper
                s_res = httpx.post("https://google.serper.dev/search",
                    headers={'X-API-KEY': st.secrets["SERPER_API_KEY"], 'Content-Type': 'application/json'},
                    json={"q": query, "hl": "ru"}).json()
                
                links = s_res.get('organic', [])
                context = "\n".join([f"{r.get('title')}: {r.get('snippet')}" for r in links[:5]])
                st.session_state.context = context
                st.session_state.links = links[:5]
                
                # Запрос к нейросети
                prompt = [{"role": "system", "content": "Ты поисковик Кусица. Отвечай кратко на основе данных."},
                          {"role": "user", "content": f"Вопрос: {query}\nДанные из сети: {context}"}]
                
                answer = get_gigachat_answer(prompt)
                st.session_state.history = [{"role": "assistant", "content": answer}]
        except Exception as e:
            st.error(f"Ошибка: {e}")

# 8. Вывод результатов
if st.session_state.history:
    # Ответ ассистента
    st.markdown(f"""
    <div class="answer-card">
        <div style="color: #ff4b4b; font-weight: bold; margin-bottom: 15px; font-size: 14px;">КУСИЦА АССИСТЕНТ</div>
        <div style="font-size: 19px; line-height: 1.6;">{st.session_state.history[0]['content']}</div>
    </div>
    """, unsafe_allow_html=True)

    # Уточнение (Дополнительный вопрос)
    st.write("")
    follow_up = st.text_input("Уточнить у ассистента...", key="follow_up")
    if follow_up:
        with st.spinner("Уточняю..."):
            messages = [
                {"role": "system", "content": f"Ты Кусица. Предыдущий контекст поиска: {st.session_state.context}"},
                {"role": "assistant", "content": st.session_state.history[0]['content']},
                {"role": "user", "content": follow_up}
            ]
            new_answer = get_gigachat_answer(messages)
            st.markdown(f"""<div class="answer-card" style="background: #f9f9f9;"><b>Уточнение:</b><br>{new_answer}</div>""", unsafe_allow_html=True)

    # Ссылки (Источники)
    st.write("")
    st.subheader("🌐 Полезные ссылки")
    for link in st.session_state.links:
        st.markdown(f"""
        <div>
            <a class="source-link" href="{link.get('link')}" target="_blank">{link.get('title')}</a>
            <div class="source-snippet">{link.get('snippet')}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br><hr><center>КУСИЦА ПОИСК • 2024</center>", unsafe_allow_html=True)
