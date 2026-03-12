import streamlit as st
import httpx
from datetime import datetime
import pytz
import uuid

# 1. Настройка страницы
st.set_page_config(page_title="КУСИЦА", page_icon="🔍", layout="wide")

# 2. CSS (Адаптивный Яндекс-стайл)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #fff; }
    
    .logo { font-size: 32px; font-weight: 900; letter-spacing: -1.5px; margin-bottom: 5px; color: #000; }
    
    .informer-box { display: flex; flex-wrap: wrap; gap: 6px; font-size: 12px; margin-bottom: 15px; }
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
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 1px solid #eee; margin-top: 15px; 
    }
    .source-item { margin-top: 12px; padding-bottom: 8px; border-bottom: 1px solid #f0f0f0; }
    .source-link { color: #1a0dab; text-decoration: none; font-weight: bold; font-size: 15px; }
    .source-snippet { color: #4d5156; font-size: 12px; margin-top: 3px; }
    </style>
    """, unsafe_allow_html=True)

# 3. Инициализация памяти
if 'history' not in st.session_state: st.session_state.history = None
if 'show_more' not in st.session_state: st.session_state.show_more = False

# 4. Данные шапки (Дата, Время, Погода, Валюта)
@st.cache_data(ttl=600)
def get_top_data():
    try:
        # Время и Дата (МСК)
        tz_m = pytz.timezone('Europe/Moscow')
        now_m = datetime.now(tz_m)
        date_str = now_m.strftime("%d.%m")
        time_m = now_m.strftime("%H:%M")
        
        # Время (КЗ)
        time_k = datetime.now(pytz.timezone('Asia/Almaty')).strftime("%H:%M")
        
        # Погода (wttr.in)
        w_m = httpx.get("https://wttr.in/Moscow?format=%t", timeout=3).text.strip()
        w_s = httpx.get("https://wttr.in/Saint-Petersburg?format=%t", timeout=3).text.strip()
        
        # Валюта
        curr = httpx.get("https://open.er-api.com/v6/latest/USD", timeout=3).json()
        usd = round(curr['rates']['RUB'], 1)
        
        return date_str, time_m, time_k, w_m, w_s, usd
    except:
        return "??.??", "??:??", "??:??", "?°C", "?°C", "??"

d_m, t_m, t_k, w_m, w_s, u_r = get_top_data()

# Вывод шапки
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

# 5. Функция GigaChat
def get_ai_res(msgs):
    try:
        auth = st.secrets["GIGACHAT_CREDENTIALS"]
        uid = str(uuid.uuid4())
        with httpx.Client(verify=False) as cl:
            tk_res = cl.post("https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                headers={"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded", "RqUID": uid},
                data={"scope": "GIGACHAT_API_PERS"})
            if tk_res.status_code != 200: return f"Ошибка авторизации: {tk_res.text}"
            tk = tk_res.json().get("access_token")
            
            rs = cl.post("https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {tk}", "Content-Type": "application/json"},
                json={"model": "GigaChat", "messages": msgs, "temperature": 0.7}, timeout=20)
            
            res_json = rs.json()
            if "choices" in res_json:
                return res_json["choices"][0]["message"]["content"]
            else:
                return f"Ошибка нейросети: {res_json.get('message', 'Неизвестно')}"
    except Exception as e:
        return f"Технический сбой: {str(e)}"

# 6. Поисковая зона
query = st.text_input("", placeholder="Найти в Кусице...", key="main_input", label_visibility="collapsed")
btn_clicked = st.button("Найти ➔")

if (btn_clicked or query) and query:
    if st.session_state.history is None or st.session_state.get('last_query') != query:
        with st.spinner(" "):
            try:
                s_res = httpx.post("https://google.serper.dev/search",
                    headers={'X-API-KEY': st.secrets["SERPER_API_KEY"], 'Content-Type': 'application/json'},
                    json={"q": query, "hl": "ru"}, timeout=15).json()
                
                links = s_res.get('organic', [])
                context = "\n".join([f"{l.get('title')}: {l.get('snippet')}" for l in links[:5]])
                ans = get_ai_res([{"role":"system","content":"Ты Кусица. Отвечай кратко."},
                                  {"role":"user","content":f"Вопрос: {query}\nИнфо: {context}"}])
                
                st.session_state.history = {"ans": ans, "links": links, "ctx": context}
                st.session_state.last_query = query
                st.session_state.show_more = False
            except Exception as e:
                st.error(f"Ошибка поиска: {e}")

# 7. Вывод результатов
if st.session_state.history:
    res = st.session_state.history
    st.markdown(f'<div class="answer-card"><b>КУСИЦА АССИСТЕНТ</b><br><br>{res["ans"]}</div>', unsafe_allow_html=True)
    
    u_query = st.text_input("Уточнить детали...", key="u_input")
    if u_query:
        with st.spinner(" "):
            u_ans = get_ai_res([{"role":"system","content":f"Контекстный поиск: {res['ctx']}"},
                                {"role":"assistant","content":res['ans']},
                                {"role":"user","content":u_query}])
            st.info(u_ans)

    st.write("---")
    st.subheader("🌐 Ссылки")
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
