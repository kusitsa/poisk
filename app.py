import streamlit as st
import httpx
from datetime import datetime
import pytz
import uuid

# 1. Настройка страницы
st.set_page_config(page_title="КУСИЦА", page_icon="🔍", layout="wide")

# 2. CSS (Адаптация под мобильные и дизайн)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    .logo { font-size: 32px; font-weight: 900; letter-spacing: -1.5px; margin-bottom: 10px; }
    
    .informer-box { display: flex; flex-wrap: wrap; gap: 8px; font-size: 12px; margin-bottom: 15px; }
    .informer-item { background: #f0f0f2; padding: 4px 8px; border-radius: 6px; white-space: nowrap; }
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
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 1px solid #eee; margin-top: 15px; 
    }
    
    .source-item { margin-top: 15px; padding-bottom: 10px; border-bottom: 1px solid #f0f0f0; }
    .source-link { color: #1a0dab; text-decoration: none; font-weight: bold; font-size: 16px; }
    .source-snippet { color: #4d5156; font-size: 13px; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 3. Инициализация переменных в памяти
if 'history' not in st.session_state: st.session_state.history = None
if 'show_more' not in st.session_state: st.session_state.show_more = False

# 4. Данные шапки (Время, Погода)
@st.cache_data(ttl=600)
def get_top_data():
    try:
        t_m = datetime.now(pytz.timezone('Europe/Moscow')).strftime("%H:%M")
        t_k = datetime.now(pytz.timezone('Asia/Almaty')).strftime("%H:%M")
        w_m = httpx.get("https://wttr.in/Moscow?format=%t", timeout=2).text.strip()
        curr = httpx.get("https://open.er-api.com/v6/latest/USD", timeout=2).json()
        usd = round(curr['rates']['RUB'], 1)
        return t_m, t_k, w_m, usd
    except: return "??", "??", "?°C", "??"

t_m, t_k, w_m, u_r = get_top_data()

# 5. Интерфейс шапки
st.markdown('<div class="logo">КУСИЦА</div>', unsafe_allow_html=True)
st.markdown(f"""
    <div class="informer-box">
        <div class="informer-item">🕒 МСК {t_m}</div>
        <div class="informer-item">🇰🇿 КЗ {t_k}</div>
        <div class="informer-item">☁️ МСК {w_m}</div>
        <div class="informer-item currency-red">USD {u_r}₽</div>
    </div>
    """, unsafe_allow_html=True)

# 6. Функции API
def get_ai_res(msgs):
    auth = st.secrets["GIGACHAT_CREDENTIALS"]
    uid = str(uuid.uuid4())
    with httpx.Client(verify=False) as cl:
        tk_res = cl.post("https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded", "RqUID": uid},
            data={"scope": "GIGACHAT_API_PERS"})
        tk = tk_res.json()["access_token"]
        rs = cl.post("https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {tk}", "Content-Type": "application/json"},
            json={"model": "GigaChat", "messages": msgs, "temperature": 0.7})
        return rs.json()["choices"][0]["message"]["content"]

# 7. Поисковая область
query = st.text_input("", placeholder="Найти в Кусице...", label_visibility="collapsed")
btn_clicked = st.button("Найти ➔")

# Логика самого поиска
if (btn_clicked or query) and query:
    # Запускаем поиск, только если это новый запрос
    if st.session_state.history is None or st.session_state.get('last_query') != query:
        with st.spinner("Ищу..."):
            try:
                # 1. Поиск
                s_api = st.secrets["SERPER_API_KEY"]
                s_res = httpx.post("https://google.serper.dev/search",
                    headers={'X-API-KEY': s_api, 'Content-Type': 'application/json'},
                    json={"q": query, "hl": "ru"}, timeout=10).json()
                
                links = s_res.get('organic', [])
                context = "\n".join([f"{l.get('title')}: {l.get('snippet')}" for l in links[:5]])
                
                # 2. Нейросеть
                ans = get_ai_res([{"role":"system","content":"Ты Кусица. Отвечай кратко."},
                                  {"role":"user","content":f"Вопрос: {query}\nИнфо: {context}"}])
                
                # Сохраняем в память
                st.session_state.history = {"ans": ans, "links": links, "ctx": context}
                st.session_state.last_query = query
                st.session_state.show_more = False
            except Exception as e:
                st.error(f"Произошла ошибка: {e}")

# 8. Отображение результатов
if st.session_state.history:
    res = st.session_state.history
    
    # Ответ ассистента
    st.markdown(f'<div class="answer-card"><b>КУСИЦА АССИСТЕНТ</b><br><br>{res["ans"]}</div>', unsafe_allow_html=True)
    
    # Поле уточнения
    u_query = st.text_input("Уточнить детали...", key="u_query")
    if u_query:
        with st.spinner(" "):
            try:
                u_ans = get_ai_res([{"role":"system","content":f"Контекст: {res['ctx']}"},
                                    {"role":"assistant","content":res['ans']},
                                    {"role":"user","content":u_query}])
                st.info(u_ans)
            except: st.error("Ошибка ИИ")

    # Ссылки
    st.write("---")
    st.subheader("🌐 Ссылки")
    
    # Кнопка показать еще
    display_links = res["links"] if st.session_state.show_more else res["links"][:2]
    
    for l in display_links:
        st.markdown(f"""
        <div class="source-item">
            <a class="source-link" href="{l.get('link')}" target="_blank">{l.get('title')}</a>
            <div class="source-snippet">{l.get('snippet')}</div>
        </div>
        """, unsafe_allow_html=True)
    
    if not st.session_state.show_more and len(res["links"]) > 2:
        if st.button("Показать еще"):
            st.session_state.show_more = True
            st.rerun()

st.markdown("<br><center style='color:#ccc; font-size:10px;'>КУСИЦА ПОИСК 2024</center>", unsafe_allow_html=True)
