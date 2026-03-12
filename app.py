import streamlit as st
import requests
import uuid
import pytz
from datetime import datetime

# 1. Настройка страницы
st.set_page_config(page_title="КУСИЦА — Поиск", page_icon="🔍", layout="wide")

# 2. Дизайн Яндекс-портала (CSS)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #fff; color: #000; }
    
    .logo { font-size: 38px; font-weight: 900; letter-spacing: -2px; color: #000; margin-bottom: 5px; }
    
    .informer-box { display: flex; flex-wrap: wrap; gap: 8px; font-size: 11px; margin-bottom: 20px; }
    .informer-item { background: #f2f2f4; padding: 4px 12px; border-radius: 15px; display: flex; align-items: center; gap: 4px; color: #555; }
    .currency-red { border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; padding: 2px 8px; border-radius: 10px; }

    /* Поисковая строка */
    .stTextInput > div > div > input {
        font-size: 18px !important; padding: 22px 25px !important;
        border-radius: 30px !important; border: 2px solid #ffdb4d !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    }
    .stButton > button {
        height: 60px; width: 100%; border-radius: 30px;
        background-color: #ffdb4d; color: black; border: none; font-size: 26px; font-weight: bold;
    }

    /* Блок Алисы */
    .alice-card { 
        background: #fdfdff; padding: 25px; border-radius: 20px; 
        box-shadow: 0 10px 40px rgba(0,0,0,0.05); border-left: 6px solid #8e44ad; margin: 20px 0;
        line-height: 1.6; font-size: 17px;
    }

    /* Поисковая выдача (Ссылки) */
    .result-item { margin-bottom: 25px; border-bottom: 1px solid #f0f0f0; padding-bottom: 15px; }
    .result-title { font-size: 20px; color: #1a0dab; text-decoration: none; font-weight: 500; }
    .result-title:hover { text-decoration: underline; }
    .result-url { color: #006621; font-size: 13px; display: block; margin-top: 2px; }
    .result-snippet { color: #444; font-size: 14px; margin-top: 5px; line-height: 1.5; }

    /* Новости */
    .news-block { background: #fafafa; padding: 15px; border-radius: 15px; border: 1px solid #eee; margin-top: 10px; }
    .news-link { color: #000; text-decoration: none; font-weight: 500; display: block; margin-bottom: 8px; font-size: 15px; }
    .news-link:hover { color: #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

# 3. Работа с данными
if 'search_data' not in st.session_state: st.session_state.search_data = None
if 'links_visible' not in st.session_state: st.session_state.links_visible = 3

@st.cache_data(ttl=600)
def get_header():
    try:
        tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(tz)
        w_m = requests.get("https://wttr.in/Moscow?format=%t", timeout=2).text.strip()
        w_s = requests.get("https://wttr.in/Saint-Petersburg?format=%t", timeout=2).text.strip()
        curr = requests.get("https://open.er-api.com/v6/latest/USD", timeout=2).json()
        usd = round(curr['rates']['RUB'], 1)
        eur = round(usd / (curr['rates']['EUR'] / curr['rates']['USD']), 1)
        return now.strftime("%d.%m"), now.strftime("%H:%M"), w_m, w_s, usd, eur
    except: return "??", "??", "?", "?", "??", "??"

@st.cache_data(ttl=1800)
def get_news_from_web(api_key):
    try:
        r = requests.post("https://google.serper.dev/news", headers={'X-API-KEY': api_key}, 
                         json={"q": "новости сегодня Россия", "gl": "ru", "hl": "ru"}, timeout=10).json()
        return r.get('news', [])[:5]
    except: return []

def call_ai(msgs):
    try:
        auth = st.secrets["GIGACHAT_CREDENTIALS"]
        # Токен
        tk_res = requests.post("https://ngw.devices.sberbank.ru:9443/api/v2/oauth", 
                             headers={'Authorization': f'Basic {auth}', 'RqUID': str(uuid.uuid4()), 'Content-Type': 'application/x-www-form-urlencoded'},
                             data={'scope': 'GIGACHAT_API_PERS'}, verify=False, timeout=10).json()
        token = tk_res['access_token']
        # Чат
        chat_res = requests.post("https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                               headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
                               json={"model": "GigaChat", "messages": msgs, "temperature": 0.8}, verify=False, timeout=25).json()
        return chat_res['choices'][0]['message']['content']
    except Exception as e:
        return f"Кусица столкнулась с ошибкой: {e}"

# --- ШАПКА ---
d, tm, wm, ws, usd_r, eur_r = get_header()
col_logo, col_info = st.columns([1, 4])
with col_logo: st.markdown('<div class="logo">КУСИЦА</div>', unsafe_allow_html=True)
with col_info:
    st.markdown(f"""
    <div class="informer-box">
        <div class="informer-item">📅 {d}</div><div class="informer-item">🕒 {tm} МСК</div>
        <div class="informer-item">🌡️ МСК {wm}</div><div class="informer-item">🌡️ СПБ {ws}</div>
        <div class="currency-red">USD {usd_r}₽</div><div class="currency-red">EUR {eur_r}₽</div>
    </div>
    """, unsafe_allow_html=True)

# --- ПОИСК ---
col_q, col_b = st.columns([7, 1])
with col_q: q = st.text_input("", placeholder="Напишите ваш вопрос...", key="search_bar", label_visibility="collapsed")
with col_b: btn = st.button("➔")

if (btn or q) and q:
    if st.session_state.get('last_q') != q:
        with st.spinner(" "):
            try:
                s_key = st.secrets["SERPER_API_KEY"]
                # Поиск
                s_res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': s_key}, json={"q": q, "hl": "ru"}).json()
                i_res = requests.post("https://google.serper.dev/images", headers={'X-API-KEY': s_key}, json={"q": q}).json()
                
                links = s_res.get('organic', [])
                if not links: st.warning("Ничего не найдено в интернете."); st.stop()
                
                context = "\n".join([f"Источник {i+1} ({l['title']}): {l['snippet']}" for i, l in enumerate(links[:5])])
                
                # Запрос к ИИ (Убираем лень)
                prompt = [
                    {"role": "system", "content": "Ты — Кусица, эрудированный и очень подробный ассистент. Твоя задача — давать развернутые, глубокие ответы на русском языке, используя факты из интернета. Не давай коротких отписок, пиши много и по делу."},
                    {"role": "user", "content": f"Запрос: {q}\n\nДанные поиска:\n{context}"}
                ]
                
                answer = call_ai(prompt)
                st.session_state.search_data = {"ans": answer, "links": links, "imgs": i_res.get('images', []), "q": q}
                st.session_state.last_q = q
                st.session_state.links_visible = 3
            except Exception as e: st.error(f"Ошибка поиска: {e}")

# --- ВЫВОД РЕЗУЛЬТАТОВ ---
if st.session_state.search_data:
    t1, t2 = st.tabs(["🔍 Поиск и Ответ", "🖼️ Картинки"])
    
    with t1:
        res = st.session_state.search_data
        # 1. Ответ Алисы
        st.markdown(f'<div class="alice-card"><b>✨ Ответ Ассистента:</b><br><br>{res["ans"]}</div>', unsafe_allow_html=True)
        
        # 2. Уточнение
        u_q = st.text_input("Уточнить детали у Кусицы...", key="follow_up")
        if u_q:
            with st.spinner(" "):
                u_ans = call_ai([{"role":"system","content":f"Ты Кусица. Контекст: {res['q']}"}, {"role":"assistant","content":res['ans']}, {"role":"user","content":u_q}])
                st.info(f"**Дополнение:** {u_ans}")

        # 3. ССЫЛКИ (Исправленный вывод)
        st.write("---")
        st.subheader("🌐 Результаты поиска")
        for l in res['links'][:st.session_state.links_visible]:
            st.markdown(f"""
            <div class="result-item">
                <a class="result-title" href="{l['link']}" target="_blank">{l['title']}</a>
                <span class="result-url">{l['link'][:80]}...</span>
                <div class="result-snippet">{l.get('snippet', '')}</div>
            </div>
            """, unsafe_allow_html=True)
        
        if st.session_state.links_visible < len(res['links']):
            if st.button("Показать еще ссылки"):
                st.session_state.links_visible += 5
                st.rerun()

    with t2:
        imgs = st.session_state.search_data['imgs']
        if not imgs: st.write("Картинки не найдены")
        else:
            cols = st.columns(2)
            for i, img in enumerate(imgs[:10]):
                with cols[i % 2]:
                    st.image(img['imageUrl'], use_container_width=True)
                    st.caption(f"[{img.get('source', 'Сайт')}]({img['link']})")

else:
    # ГЛАВНАЯ (НОВОСТИ)
    st.write("---")
    st.subheader("Главное за день")
    news = get_news_from_web(st.secrets.get("SERPER_API_KEY", ""))
    if news:
        st.markdown('<div class="news-block">', unsafe_allow_html=True)
        for n in news:
            st.markdown(f'<a class="news-link" href="{n["link"]}" target="_blank">📰 {n["title"]}</a>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<br><hr><center style='color:#999; font-size:11px;'>КУСИЦА • 2024</center>", unsafe_allow_html=True)
