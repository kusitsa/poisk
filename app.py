import streamlit as st
import httpx
import google.generativeai as genai

# Настройка страницы
st.set_page_config(page_title="Free AI Search", page_icon="🚀")

# Проверка ключей в Secrets
try:
    SERPER_KEY = st.secrets["SERPER_API_KEY"]
    GEMINI_KEY = st.secrets["GEMINI_API_KEY"] # Теперь используем этот ключ
except Exception:
    st.error("Настройте ключи в Secrets: SERPER_API_KEY и GEMINI_API_KEY")
    st.stop()

# Настройка Google Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash') # Быстрая и бесплатная модель

def search_internet(query):
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': SERPER_KEY, 'Content-Type': 'application/json'}
    payload = {"q": query, "hl": "ru", "gl": "ru"}
    with httpx.Client() as sync_client:
        response = sync_client.post(url, headers=headers, json=payload, timeout=15)
        results = response.json()
    snippets = [f"Сайт: {r.get('title')}\nТекст: {r.get('snippet')}" for r in results.get("organic", [])[:5]]
    return "\n\n".join(snippets)

st.title("🚀 Бесплатный AI Поиск")

query = st.text_input("", placeholder="Введите ваш вопрос...")

if st.button("Найти ответ"):
    if query:
        with st.spinner("Ищу в интернете..."):
            try:
                context = search_internet(query)
                
                # Запрос к Gemini
                prompt = f"Ты помощник. Ответь кратко на вопрос: {query}, используя эти данные: {context}"
                response = model.generate_content(prompt)
                
                st.subheader("💡 Ответ:")
                st.info(response.text)
                
                with st.expander("🔗 Источники"):
                    st.text(context)
            except Exception as e:
                st.error(f"Ошибка: {e}")
