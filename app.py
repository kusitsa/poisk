import streamlit as st
import httpx
import google.generativeai as genai
from datetime import datetime
import pytz

# 1. Настройка страницы
st.set_page_config(page_title="КУСИЦА ПОИСК", page_icon="🔍", layout="wide")

# 2. CSS стиль (Яндекс-стайл)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #fff;
    }

    .logo {
        font-size: 38px;
        font-weight: 900;
        color: #000;
        letter-spacing: -2px;
        margin-top: -10px;
    }
    
    .informer-box {
        display: flex;
        flex-wrap: wrap;
        gap: 15px;
        font-size: 14px;
        color: #555;
        margin-top: 5px;
    }
    
    .informer-item {
        display: flex;
        align-items: center;
        gap: 5px;
        background: #f5f5f7;
        padding: 4px 10px;
        border-radius: 8px;
    }

    .currency-red-box {
        border: 1px solid #ff4b4b;
        background: #fff5f5;
        color: #ff4b4b;
        font-weight: bold;
    }

    .stTextInput > div > div > input {
        font-size: 20px !important;
        padding: 25px 20px !important;
        border-radius: 12px !important;
        border: 2px solid #ffdb4d !important; /* Желтая кайма как у Яндекса */
        box-shadow: 0 4px 15px rgba(0,0,0,0.07);
    }
    
    .stButton > button {
        height: 64px;
        width: 100%;
        border-radius: 12px;
        background-color: #ffdb4d; 
        color: black;
        border: none;
        font-size: 28px;
        font-weight: bold;
        transition: 0.3s;
    }
    .stButton > button:hover {
        background-color: #ffd200;
        border: none;
    }
    
    .answer-card {
        background: white;
        padding: 30px;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        border: 1px solid #eee;
        margin-top: 30px;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. Вспомогательные функции получения данных
def get_data():
    # Время
    moscow_time = datetime.now(pytz.timezone('Europe/Moscow')).strftime("%H:%M")
    kazakh_time = datetime.now(pytz.timezone('Asia/Almaty')).strftime("%H:%M")
    
    # Погода (Цельсий)
    try:
        w_msk = httpx.get("https://wttr.in/Moscow?format=%t", timeout=5).text.strip()
        w_spb = httpx.get("https://wttr.in/Saint-Petersburg?format=%t", timeout=5).text.strip()
    except:
        w_msk, w_spb = "?°C", "?°C"
        
    # Валюта
    try:
        curr = httpx.get("https://open.er-api.com/v6/latest/USD", timeout=5).json()
        usd = round(curr['rates']['RUB'], 1)
        eur = round(usd / (curr['rates']['EUR'] / curr['rates']['USD']), 1)
    except:
        usd, eur = "??", "??"
        
    return moscow_time, kazakh_time, w_msk, w_spb, usd, eur

# Получаем данные
m_time, k_time, m_weather, s_weather, usd_r, eur_r = get_data()

# 4. ШАПКА (Логотип + Информеры)
col_logo, col_info = st.columns([1, 4])

with col_logo:
    st.markdown('<div class="logo">КУСИЦА</div>', unsafe_allow_html=True)

with col_info:
    st.markdown(f"""
    <div class="informer-box">
        <div class="informer-item">🕒 МСК <b>{m_time}</b></div>
        <div class="informer-item">🇰🇿 КЗ <b>{k_time}</b></div>
        <div class="informer-item">☁️ МСК <b>{m_weather}</b></div>
        <div class="informer-item">☁️ СПБ <b>{s_weather}</b></div>
        <div class="informer-item currency-red-box">USD {usd_r}₽</div>
        <div class="informer-item currency-red-box">EUR {eur_r}₽</div>
    </div>
    """, unsafe_allow_html=True)

st.write("") # Отступ

# 5. ПОИСКОВАЯ СТРОКА
col_search, col_btn = st.columns([7, 1])

with col_search:
    query = st.text_input("", placeholder="Найти в КУСИЦЕ...", label_visibility="collapsed")

with col_btn:
    search_clicked = st.button("➔")

# 6. ЛОГИКА ИИ
if (search_clicked or query) and query:
    try:
        SERPER_KEY = st.secrets["SERPER_API_KEY"]
        GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
        
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        with st.spinner(" "):
            # Поиск через Serper
            url = "https://google.serper.dev/search"
            headers = {'X-API-KEY': SERPER_KEY, 'Content-Type': 'application/json'}
            payload = {"q": query, "hl": "ru"}
            
            with httpx.Client() as client:
                res = client.post(url, headers=headers, json=payload, timeout=15).json()
                results = res.get('organic', [])
                context = "\n".join([r.get('snippet', '') for r in results[:5]])
            
            # Генерация ответа ИИ
            prompt = f"Ты современный поисковик КУСИЦА. На основе данных ответь на вопрос кратко.\nВопрос: {query}\nДанные: {context}"
            ai_response = model.generate_content(prompt).text
            
            st.markdown(f"""
            <div class="answer-card">
                <div style="color: #ff4b4b; font-weight: bold; margin-bottom: 10px;">ОТВЕТ АССИСТЕНТА</div>
                <div style="font-size: 19px; line-height: 1.5; color: #222;">{ai_response}</div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("Источники"):
                for r in results[:5]:
                    st.markdown(f"**[{r.get('title')}]({r.get('link')})**")
                    st.write(r.get('snippet'))
                    st.write("---")
                
    except Exception as e:
        st.error("Проверьте ключи API в настройках Secrets!")

# 7. ПОДВАЛ
st.markdown("<br><br><br><br><hr><div style='text-align: center; color: #aaa;'>КУСИЦА ПОИСК • 2024</div>", unsafe_allow_html=True)
