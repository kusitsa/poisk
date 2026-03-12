import streamlit as st
import requests
import uuid
import pytz
from datetime import datetime

# 1. Настройка страницы
st.set_page_config(page_title="КУСИЦА — Поиск", page_icon="🔍", layout="wide")

# 2. CSS Яндекс-портал
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #fff; color: #000; }
    .logo { font-size: 38px; font-weight: 900; letter-spacing: -2px; color: #000; margin-bottom: 5px; }
    .informer-box { display: flex; flex-wrap: wrap; gap: 8px; font-size: 11px; margin-bottom: 20px; }
    .informer-item { background: #f2f2f4; padding: 4px 12px; border-radius: 15px; display: flex; align-items: center; gap: 4px; color: #555; }
    .currency-red { border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; padding: 2px 8px; border-radius: 10px; }
    .stTextInput > div > div > input {
        font-size: 18px !important; padding: 22px 25px !important;
        border-radius: 30px !important; border: 2px solid #ffdb4d !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    }
    .stButton > button {
        height: 60px; width: 100%; border-radius: 30px;
        background-color: #ffdb4d; color: black; border: none; font-size: 26px; font-weight: bold;
    }
    .alice-card { 
        background: #fdfdff; padding: 25px; border-radius: 20px; 
        box-shadow: 0 10px 40px rgba(0,0,0,0.05); border-left: 6px solid #8e44ad; margin: 20px 0;
        line-height: 1.6; font-size: 17px;
    }
    .result-item { margin-bottom: 25px; border-bottom: 1px solid #f0f0f0; padding-bottom: 15px; }
    .result-title { font-size: 20px; color: #1a0dab; text-decoration: none; font-weight: 500; }
    .result-url { color: #006621; font-size: 13px; display: block; margin-top: 2px; }
    .result-snippet { color: #444; font-size: 14px; margin-top: 5px; line-height: 1.5; }
    </style>
    """, unsafe_allow_html=True)

# 3. Работа с данными
if 'search_data' not in st.session_state: st.session_state.search_data = None

@st.cache_data(ttl=600)
def get_header():
    try:
        tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(tz)
        w_m = requests.get("https://wttr.in/Moscow?format=%t", timeout=3).text.strip()
        curr = requests.get("https://open.er-api.com/v6/latest/USD", timeout=3).json()
        usd = round(curr['rates']['RUB'], 1)
        eur = round(usd / (curr['rates']['EUR'] / curr['rates']['USD']), 1)
        return now.strftime("%d.%m"), now.strftime("%H:%M"), w_m, usd, eur
    except: return "??", "??", "?", "??", "??"

def get_ai_answer(msgs):
    try:
        auth = st.secrets["GIGACHAT_CREDENTIALS"]
        tk_res = requests.post("https://ngw.devices.sberbank.ru:9443/api/v2/oauth", 
                             headers={'Authorization': f'Basic {auth}', 'RqUID': str(uuid.uuid4()), 'Content-Type': 'application/x-www-form-urlencoded'},
                             data={'scope': 'GIGACHAT_API_PERS'}, verify=False, timeout=15).json()
        token = tk_res['access_token']
        chat_res = requests.post("https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                               headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
                               json={"model": "GigaChat", "messages": msgs, "temperature": 0.8}, verify=False, timeout=30).json()
        return chat_res['choices'][0]['message']['content']
    except Exception as e: return f"Кусица: Не удалось получить ответ ({e})"

# --- ШАПКА ---
d, tm, wm, usd, eur = get_header()
st.markdown('<div class="logo">КУСИЦА</div>', unsafe_allow_html=True)
st.markdown(f"""
    <div class="informer-box">
        <div class="informer-item">📅 {d}</div><div class="informer-item">🕒 {tm} МСК</div>
        <div class="informer-item">🌡️ МСК {wm}</div>
        <div class="currency-red">USD {usd}₽</div><div class="currency-red">EUR {eur}₽</div>
    </div>
    """, unsafe_allow_html=True)

# --- ПОИСК ---
q = st.text_input("", placeholder="Что вы хотите найти?", key="search_bar", label_visibility="collapsed")
if st.button("Найти ответ ➔") or q:
    if q and st.session_state.get('last_q') != q:
        with st.spinner("Кусица ищет..."):
            try:
                s_key = st.secrets["SERPER_API_KEY"]
                headers = {'X-API-KEY': s_key, 'Content-Type': 'application/json'}
                payload = {"q": q, "hl": "ru", "gl": "ru"}
                
                # Поиск текста
                s_res = requests.post("https://google.serper.dev/search", headers=headers, json=payload, timeout=15).json()
                # Поиск картинок
                i_res = requests.post("https://google.serper.dev/images", headers=headers, json={"q": q}, timeout=15).json()
                
                links = s_res.get('organic', [])
                
                # Если органики нет, ищем в других блоках
                if not links:
                    answer_box = s_res.get('answerBox', {}).get('answer') or s_res.get('answerBox', {}).get('snippet')
                    if answer_box:
                        links = [{"title": "Прямой ответ", "link": "#", "snippet": answer_box}]
                
                if not links:
                    st.error(f"Поиск не дал результатов. Ответ сервера: {s_res.get('message', 'Ничего не найдено')}")
                else:
                    context = "\n".join([f"Источник {i+1}: {l.get('snippet', '')}" for i, l in enumerate(links[:5])])
                    prompt = [
                        {"role": "system", "content": "Ты — Кусица, эрудированный ассистент. Отвечай подробно и на русском языке."},
                        {"role": "user", "content": f"Вопрос: {q}\nИнфо: {context}"}
                    ]
                    answer = get_ai_answer(prompt)
                    st.session_state.search_data = {"ans": answer, "links": links, "imgs": i_res.get('images', []), "q": q}
                    st.session_state.last_q = q
            except Exception as e:
                st.error(f"Техническая ошибка: {e}")

# --- ВЫВОД ---
if st.session_state.search_data:
    res = st.session_state.search_data
    t1, t2 = st.tabs(["🔍 Поиск", "🖼️ Картинки"])
    
    with t1:
        st.markdown(f'<div class="alice-card"><b>✨ Кусица:</b><br><br>{res["ans"]}</div>', unsafe_allow_html=True)
        st.write("---")
        for l in res['links'][:5]:
            st.markdown(f"""
            <div class="result-item">
                <a class="result-title" href="{l.get('link')}" target="_blank">{l.get('title')}</a>
                <span class="result-url">{l.get('link')[:80]}</span>
                <div class="result-snippet">{l.get('snippet', '')}</div>
            </div>
            """, unsafe_allow_html=True)

    with t2:
        imgs = res.get('imgs', [])
        if not imgs: st.write("Картинки не найдены")
        else:
            cols = st.columns(2)
            for i, img in enumerate(imgs[:10]):
                with cols[i % 2]: st.image(img['imageUrl'], use_container_width=True)
else:
    # НОВОСТИ
    st.write("---")
    st.subheader("Главное сегодня")
    try:
        news_r = requests.post("https://google.serper.dev/news", headers={'X-API-KEY': st.secrets["SERPER_API_KEY"]}, 
                              json={"q": "новости сегодня Россия", "gl": "ru", "hl": "ru"}, timeout=5).json()
        for n in news_r.get('news', [])[:5]:
            st.markdown(f"📰 [{n['title']}]({n['link']})")
    except: st.write("Новости загружаются...")

st.markdown("<br><hr><center style='color:#999; font-size:11px;'>КУСИЦА • 2024</center>", unsafe_allow_html=True)
