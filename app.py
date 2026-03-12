import streamlit as st
import httpx
import google.generativeai as genai
from datetime import datetime
import pytz

# 1. Настройка страницы
st.set_page_config(page_title="Super AI Search", page_icon="🌐", layout="wide")

# 2. Стили CSS (включая красную рамку для валют)
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .currency-container {
        border: 2px solid #ff4b4b;
        padding: 15px;
        border-radius: 10px;
        background-color: #fff5f5;
        text-align: center;
    }
    .time-container {
        font-size: 18px;
        font-weight: bold;
        color: #1f1f1f;
        padding: 10px;
        background: #e1e4e8;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .weather-card {
        padding: 10px;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stTextInput > div > div > input { border-radius: 20px; }
    </style>
    """, unsafe_allow_html=True)

# 3. Функции данных
def get_time():
    moscow = datetime.now(pytz.timezone('Europe/Moscow')).strftime("%H:%M")
    kazakhstan = datetime.now(pytz.timezone('Asia/Almaty')).strftime("%H:%M")
    return moscow, kazakhstan

def get_currency():
    try:
        # Используем бесплатное API курсов
        res = httpx.get("https://open.er-api.com/v6/latest/USD").json()
        usd_rub = res['rates']['RUB']
        eur_rub = usd_rub / (res['rates']['EUR'] / res['rates']['USD'])
        return f"USD: {usd_rub:.2f} ₽ | EUR: {eur_rub:.2f} ₽"
    except:
        return "Курс временно недоступен"

def get_weather(city):
    try:
        # Простой сервис погоды без ключа
        res = httpx.get(f"https://wttr.in/{city}?format=%c%t").text
        return res
    except:
        return "Нет данных"

# 4. Проверка ключей
try:
    SERPER_KEY = st.secrets["SERPER_API_KEY"]
    GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception:
    st.error("Настройте ключи SERPER_API_KEY и GEMINI_API_KEY в Secrets!")
    st.stop()

# 5. Поисковые функции
def search_internet(query):
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': SERPER_KEY, 'Content-Type': 'application/json'}
    payload = {"q": query, "hl": "ru"}
    with httpx.Client() as client:
        response = client.post(url, headers=headers, json=payload, timeout=15)
        results = response.json()
    return "\n\n".join([f"{r.get('title')}: {r.get('snippet')}" for r in results.get("organic", [])[:5]])

# --- ВЕРХНЯЯ ПАНЕЛЬ (ВРЕМЯ) ---
msk, kz = get_time()
st.markdown(f"""
    <div class="time-container">
        🕒 Москва: {msk} | 🇰🇿 Казахстан (Астана): {kz}
    </div>
    """, unsafe_allow_html=True)

# --- ГЛАВНЫЙ ИНТЕРФЕЙС (КОЛОНКИ) ---
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    st.markdown("### 🌤 Погода")
    st.markdown(f"<div class='weather-card'><b>МСК:</b> {get_weather('Moscow')}</div>", unsafe_allow_html=True)
    st.write("")
    st.markdown(f"<div class='weather-card'><b>СПБ:</b> {get_weather('Saint-Petersburg')}</div>", unsafe_allow_html=True)

with col2:
    st.title("🚀 Smart Search AI")
    query = st.text_input("", placeholder="Спроси меня о чем угодно...")
    search_button = st.button("Найти ответ")

with col3:
    st.markdown("### 💸 Валюта")
    st.markdown(f"""
        <div class="currency-container">
            <b>Курс ЦБ (прим.)</b><br>
            {get_currency()}
        </div>
        """, unsafe_allow_html=True)

# --- ЛОГИКА ПОИСКА ---
if search_button and query:
    with st.spinner("Ищу по всему интернету..."):
        try:
            context = search_internet(query)
            prompt = f"Ты современный поисковик. Дай четкий и короткий ответ на вопрос: {query}. Используй данные: {context}"
            response = model.generate_content(prompt)
            
            st.markdown("---")
            st.subheader("💡 Мой ответ:")
            st.success(response.text)
            
            with st.expander("🔗 Источники информации"):
                st.write(context)
        except Exception as e:
            st.error(f"Ошибка: {e}")

# --- ФИШКА ОТ СЕБЯ (ИНТЕРЕСНЫЙ ФАКТ) ---
st.markdown("---")
if not query:
    try:
        # Генерируем случайный факт при загрузке
        fact_prompt = "Расскажи один очень короткий и удивительный научный факт на русском языке."
        random_fact = model.generate_content(fact_prompt).text
        st.info(f"<b>💡 Знаете ли вы?</b><br>{random_fact}", icon="🎓")
    except:
        pass
