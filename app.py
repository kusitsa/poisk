import streamlit as st
import httpx
from openai import OpenAI

# 1. Настройка страницы (дизайн)
st.set_page_config(
    page_title="AI Search Engine", 
    page_icon="🚀", 
    layout="centered"
)

# Красивое оформление через CSS
st.markdown("""
    <style>
    .stTextInput > div > div > input {
        border-radius: 25px;
        padding: 15px 25px;
        border: 2px solid #007bff;
    }
    .stButton > button {
        border-radius: 20px;
        width: 100%;
        background-color: #007bff;
        color: white;
        font-weight: bold;
    }
    .answer-box {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 15px;
        border-left: 5px solid #007bff;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        color: #333;
        line-height: 1.6;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. Проверка ключей в Secrets (настройках сервера)
try:
    SERPER_KEY = st.secrets["SERPER_API_KEY"]
    OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
except Exception:
    st.error("⚠️ Ошибка: Ключи API не найдены в Secrets вашего приложения!")
    st.info("Пожалуйста, добавьте SERPER_API_KEY и OPENAI_API_KEY в настройках Streamlit Cloud.")
    st.stop()

# Инициализация клиента OpenAI
client = OpenAI(api_key=OPENAI_KEY)

# 3. Функция поиска в Google (через Serper)
def search_internet(query):
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': SERPER_KEY, 'Content-Type': 'application/json'}
    payload = {"q": query, "hl": "ru", "gl": "ru"}
    
    with httpx.Client() as sync_client:
        response = sync_client.post(url, headers=headers, json=payload, timeout=15)
        results = response.json()
        
    snippets = []
    # Собираем данные из первых 5 результатов
    for r in results.get("organic", [])[:5]:
        snippets.append(f"Заголовок: {r.get('title')}\nОписание: {r.get('snippet')}\nСсылка: {r.get('link')}")
    return "\n\n".join(snippets)

# 4. Функция генерации ответа через GPT-4o-mini
def get_ai_answer(query, context):
    prompt = f"""
    Ты — умный ИИ-помощник. Твоя задача — ответить на вопрос пользователя максимально точно, основываясь на данных из интернета.
    
    ВОПРОС: {query}
    
    ДАННЫЕ ИЗ ПОИСКА:
    {context}
    
    Твой ответ должен быть коротким, структурированным и на русском языке.
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return response.choices[0].message.content

# 5. Интерфейс приложения
st.title("🚀 Мой персональный AI-поиск")
st.write("Я проанализирую интернет и выдам вам краткую выжимку.")

query = st.text_input("", placeholder="Введите ваш вопрос (например: какая погода в Москве или что такое квантовый компьютер?)")

if st.button("Найти ответ"):
    if query:
        with st.spinner("🔍 Ищу информацию в сети..."):
            try:
                # Шаг 1: Поиск в Google
                search_results = search_internet(query)
                
                # Шаг 2: Анализ через ИИ
                answer = get_ai_answer(query, search_results)
                
                # Шаг 3: Вывод результата
                st.markdown("### 💡 Ответ:")
                st.markdown(f"<div class='answer-box'>{answer}</div>", unsafe_allow_html=True)
                
                # Шаг 4: Источники
                with st.expander("🔗 Посмотреть источники"):
                    st.text(search_results)
                    
            except Exception as e:
                st.error(f"Произошла техническая ошибка: {e}")
    else:
        st.warning("Сначала введите ваш вопрос!")
