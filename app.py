import streamlit as st
import httpx
import google.generativeai as genai
from datetime import datetime
import pytz

# 1. Настройка страницы
st.set_page_config(page_title="КУСИЦА ПОИСК", page_icon="🔍", layout="wide")

# 2. Улучшенный CSS стиль (Яндекс-стайл)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Логотип КУСИЦА */
    .logo {
        font-size: 32px;
        font-weight: 800;
        color: #000;
        letter-spacing: -1.5px;
        margin-bottom: 20px;
    }
    
    /* Компактные иконки информеры */
    .informer-box {
        display: flex;
        gap: 20px;
        font-size: 14px;
        color: #555;
        margin-bottom: 30px;
    }
    
    .informer-item {
        display: flex;
        align-items: center;
        gap: 5px;
    }

    /* Красная рамка для валют (как просили) */
    .currency-red-box {
        border: 1px solid #ff4b4b;
        padding: 2px 8px;
        border-radius: 5px;
        color: #ff4b4b;
        font-weight: bold;
    }

    /* Стилизация большой поисковой строки */
    .stTextInput > div > div > input {
        font-size: 20px !important;
        padding: 25px 20px !important;
        border-radius: 15px !important;
        border: 2px solid #e2e2e2 !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    
    /* Кнопка-стрелочка */
    .stButton > button {
        height: 60px;
        width: 100%;
        border-radius: 15px;
        background-color: #fc3f1d; /* Фирменный красный */
        color: white;
        border: none;
        font-size: 24px;
    }
    
    .answer-card {
        background: white;
        padding: 30px;
        border-radius: 20px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        border: 1px solid #f0f0f0;
        margin-top: 30px;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. Вспомогательные функции
def get_data():
    # Время
    msk_time = datetime.now(pytz.timezone('Europe/Moscow')).strftime("%H:%M")
    kz_time = datetime.now(pytz.timezone('Asia/Almaty')).strftime("%H:%M")
    
    # Погода (Цельсий)
    try:
        w_msk = httpx.get("https://wttr.in/Moscow?format=%t").text.strip()
        w_spb = httpx.get("https://wttr.in/Saint-Petersburg?format=%t").text.strip()
    except:
        w_msk, w_spb = "?°C", "?°C"
        
    # Валюта
    try:
        curr = httpx.get("https://open.er-api.com/v6/latest/USD").json()
        usd = round(curr['rates']['RUB'], 1)
        eur = round(usd / (curr['rates']['EUR'] / curr['rates']['USD']), 1)
    except:
        usd, eur = "??", "??"
        
    return moscow_time, kz_time, w_msk, w_spb, usd, eur

moscow_time, kazakh_time, weather_msk, weather_spb, usd_rate, eur_rate = get_data()

# 4. ВЕРХНЯЯ ЧАСТЬ (Лого и Информеры)
col_logo, col_info = st.columns([1, 4])

with col_logo:
    st.markdown('<div class="logo">КУСИЦА</div>', unsafe_allow_html=True)

with col_info:
    st.markdown(f"""
    <div class="informer-box">
        <div class="informer-item">🕒 МСК {moscow_time}</div>
        <div class="informer-item">🇰🇿 КЗ {kazakh_time}</div>
        <div class="informer-item">☁️ МСК {weather_msk}</div>
        <div class="informer-item">☁️ СПБ {weather_spb}</div>
        <div class="informer-item currency-red-box">USD {usd_rate}₽</div>
        <div class="informer-item currency-red-box">EUR {eur_rate}₽</div>
    </div>
    """, unsafe_allow_html=True)

# 5. ЦЕНТРАЛЬНАЯ ЧАСТЬ (Поиск)
st.write("") # Отступ
st.write("") 

col_search, col_btn = st.columns([6, 1])

with col_search:
    query = st.text_input("", placeholder="Найти в интернете...", label_visibility="collapsed")

with col_btn:
    search_clicked = st.button("➔")

# 6. ЛОГИКА ИИ И ВЫВОД
if (search_clicked or query != "") and query:
    # Проверка ключей
    try:
        SERPER_KEY = st.secrets["SERPER_API_KEY"]
        GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        with st.spinner(" "):
            # Поиск
            url = "https://google.serper.dev/search"
            headers = {'X-API-KEY': SERPER_KEY, 'Content-Type': 'application/json'}
            payload = {"q": query, "hl": "ru"}
            
            with httpx.Client() as client:
                res = client.post(url, headers=headers, json=payload, timeout=15).json()
                context = "\n".join([r.get('snippet', '') for r in res.get('organic', [])[:5]])
            
            # Ответ
            prompt = f"Вопрос: {query}. Данные интернета: {context}. Ответь кратко и понятно."
            answer = model.generate_content(prompt).text
            
            st.markdown(f"""
            <div class="answer-card">
                <div style="color: #888; font-size: 14px; margin-bottom: 10px;">ОТВЕТ ИИ</div>
                <div style="font-size: 18px; color: #111;">{answer}</div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("Источники"):
                st.write(context)
                
    except Exception as e:
        st.error(f"Ошибка: {e}. Проверьте ключи в Secrets.")

# 7. ФИШКА: СОВЕТ ДНЯ (внизу)
st.write("")
st.write("")
st.write("")
st.markdown("---")
st.markdown(f"<div style='color: #999; text-align: center; font-size: 13px;'>Кусица Поиск 2024 • Сделано для тебя</div>", unsafe_allow_html=True)
