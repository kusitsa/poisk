import streamlit as st
import requests
import uuid
import pytz
from datetime import datetime

# 1. Настройка страницы
st.set_page_config(page_title="КУСИЦА — Поиск", page_icon="🔍", layout="wide")

# 2. Стиль Яндекс-портала
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #fff; color: #000; }
    
    .logo { font-size: 38px; font-weight: 900; letter-spacing: -2px; color: #000; margin-bottom: 5px; }
    
    .informer-box { display: flex; flex-wrap: wrap; gap: 8px; font-size: 11px; margin-bottom: 20px; }
    .informer-item { background: #f2f2f4; padding: 4px 12px; border-radius: 15px; display: flex; align-items: center; gap: 4px; color: #555; }
    .currency-pill { border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; }

    .stTextInput > div > div > input {
        font-size: 18px !important; padding: 22px 25px !important;
        border-radius: 30px !important; border: 2px solid #ffdb4d !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    }
    .stButton > button {
        height: 60px; width: 100%; border-radius: 30px;
        background-color: #ffdb4d; color: black; border: none; font-size: 26px; font-weight: bold;
    }

    /* Блок Ассистента (Умный ответ) */
    .alice-card { 
        background: #fdfdff; padding: 30px; border-radius: 24px; 
        box-shadow: 0 10px 40px rgba(0,0,0,0.05); border-left: 6px solid #8e44ad; margin-top: 15px; 
        line-height: 1.6; font-size: 18px;
    }
    .alice-label { color: #8e44ad; font-weight: bold; font-size: 13px; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px; }

    /* Поисковая выдача */
    .search-result { margin-bottom: 25px; max-width: 800px; }
    .search-title { font-size: 20px; color: #1a0dab; text-decoration: none; font-weight: 500; }
    .search-title:hover { text-decoration: underline; }
    .search-url { color: #006621; font-size: 13px; display: block; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .search-desc { color: #444; font-size: 15px; margin-top: 5px; line-height: 1.5; }

    /* Новости на главной */
    .news-block { background: #fafafa; padding: 20px; border-radius: 20px; border: 1px solid #f0f0f0; }
    .news-item { padding: 10px 0; border-bottom: 1px solid #eee; }
    .news-item:last-child { border-bottom: none; }
    .news-link { color: #000; text-decoration: none; font-weight: 500; font-size: 16px; }
    .news-link:hover { color: #ff4b4b; }
    .news-meta { font-size: 12px; color: #888; margin-top: 4px; }
    </style>
    """, unsafe_allow_html=True)

# 3. Управление состоянием (Session State)
if 'res' not in st.session_state: st.session_state.res = None
if 'link_limit' not in st.session_state: st.session_state.link_limit = 3
if 'img_limit' not in st.session_state: st.session_state.img_limit = 4
if 'view_img_idx' not in st.session_state: st.session_state.view_img_idx = None

# 4. Функции данных
@st.cache_data(ttl=600)
def get_header_data():
    try:
        tz_m = pytz.timezone('Europe/Moscow')
        now_m = datetime.now(tz_m)
        w_m = requests.get("https://wttr.in/Moscow?format=%t", timeout=3).text.strip()
        w_s = requests.get("https://wttr.in/Saint-Petersburg?format=%t", timeout=3).text.strip()
        curr = requests.get("https://open.er-api.com/v6/latest/USD", timeout=3).json()
        usd = round(curr['rates']['RUB'], 1)
        eur = round(usd / (curr['rates']['EUR'] / curr['rates']['USD']), 1)
        return now_m.strftime("%d.%m"), now_m.strftime("%H:%M"), datetime.now(pytz.timezone('Asia/Almaty')).strftime("%H:%M"), w_m, w_s, usd, eur
    except: return "??", "??", "??", "?", "?", "??", "??"

@st.cache_data(ttl=1800)
def fetch_news(api_key):
    try:
        url = "https://google.serper.dev/news"
        headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
        r = requests.post(url, headers=headers, json={"q": "главные новости России сегодня", "gl": "ru", "hl": "ru"}, timeout=10).json()
        return r.get('news', [])[:6]
    except: return []

def get_smart_answer(messages):
    try:
        auth = st.secrets["GIGACHAT_CREDENTIALS"]
        # Получение токена
        tk_res = requests.post("https://ngw.devices.sberbank.ru:9443/api/v2/oauth", 
                               headers={'Authorization': f'Basic {auth}', 'RqUID': str(uuid.uuid4()), 'Content-Type': 'application/x-www-form-urlencoded'},
                               data={'scope': 'GIGACHAT_API_PERS'}, verify=False, timeout=10)
        token = tk_res.json()['access_token']
        # Запрос к нейросети
        chat_res = requests.post("https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                               headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
                               json={"model": "GigaChat", "messages": messages, "temperature": 0.8}, verify=False, timeout=25)
        data = chat_res.json()
        if 'choices' in data:
            return data['choices'][0]['message']['content']
        return f"Кусица призадумалась... (Ошибка: {data.get('message', 'пустой ответ')})"
    except Exception as e:
        return f"Ошибка связи с Кусицей: {str(e)}"

# --- ШАПКА ---
d_msk, t_msk, t_kz, w_msk, w_spb, usd_r, eur_r = get_header_data()
col_logo, col_info = st.columns([1, 4])
with col_logo: st.markdown('<div class="logo">КУСИЦА</div>', unsafe_allow_html=True)
with col_info:
    st.markdown(f"""
    <div class="informer-box">
        <div class="informer-item">📅 {d_msk}</div><div class="informer-item">🕒 МСК {t_msk}</div>
        <div class="informer-item">🇰🇿 КЗ {t_kz}</div><div class="informer-item">🌡️ МСК {w_msk}</div>
        <div class="informer-item">🌡️ СПБ {w_spb}</div>
        <div class="informer-item currency-pill">USD {usd_r}₽</div><div class="informer-item currency-pill">EUR {eur_r}₽</div>
    </div>
    """, unsafe_allow_html=True)

# --- ПОИСК ---
col_input, col_go = st.columns([7, 1])
with col_input: 
    q = st.text_input("", placeholder="Спроси Кусицу о чем угодно...", key="search_bar", label_visibility="collapsed")
with col_go: 
    btn = st.button("➔")

if (btn or q) and q:
    if st.session_state.get('last_q') != q:
        with st.spinner(" "):
            try:
                s_key = st.secrets["SERPER_API_KEY"]
                sr = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': s_key}, json={"q": q, "hl": "ru"}).json()
                ir = requests.post("https://google.serper.dev/images", headers={'X-API-KEY': s_key}, json={"q": q}).json()
                
                links = sr.get('organic', [])
                context = "\n".join([f"Сайт {l.get('title')}: {l.get('snippet')}" for l in links[:5]])
                
                # НОВАЯ ИНСТРУКЦИЯ (Убираем "лень")
                prompt = [
                    {"role": "system", "content": "Ты — Кусица, невероятно умный и подробный ассистент. Твоя задача — давать развернутые, интересные и полезные ответы на русском языке, используя предоставленные данные из интернета. Не ленись, пиши подробно."},
                    {"role": "user", "content": f"Вопрос пользователя: {q}\n\nДанные из поиска:\n{context}"}
                ]
                
                ans = get_smart_answer(prompt)
                st.session_state.res = {"ans": ans, "links": links, "imgs": ir.get('images', []), "q": q, "ctx": context}
                st.session_state.last_q = q
                st.session_state.link_limit, st.session_state.img_limit = 3, 4
                st.session_state.view_img_idx = None
            except: st.error("Произошла ошибка при поиске. Проверьте ключи API.")

# --- ВЫВОД РЕЗУЛЬТАТОВ ---
if st.session_state.res:
    t1, t2 = st.tabs(["🔍 Ответ и Ссылки", "🖼️ Картинки"])
    
    with t1:
        res = st.session_state.res
        # Ответ ИИ
        st.markdown(f"""
        <div class="alice-card">
            <div class="alice-label">✨ Умный ответ Кусицы</div>
            {res['ans']}
        </div>
        """, unsafe_allow_html=True)
        
        # Уточнение
        st.write("")
        f_q = st.text_input("Уточнить детали у ассистента...", key="follow_up")
        if f_q:
            with st.spinner("Уточняю..."):
                f_ans = get_smart_answer([
                    {"role": "system", "content": f"Ты Кусица. Контекст: {res['ctx']}"},
                    {"role": "assistant", "content": res['ans']},
                    {"role": "user", "content": f_q}
                ])
                st.info(f"**Дополнение:** {f_ans}")

        st.markdown("### 🌐 Найденные сайты")
        for l in res['links'][:st.session_state.link_limit]:
            st.markdown(f"""
            <div class="search-result">
                <a class="search-title" href="{l['link']}" target="_blank">{l['title']}</a>
                <span class="search-url">{l['link'][:80]}...</span>
                <div class="search-desc">{l.get('snippet', '')}</div>
            </div>
            """, unsafe_allow_html=True)
        
        if st.session_state.link_limit < len(res['links']):
            if st.button("Показать еще результаты"):
                st.session_state.link_limit += 5
                st.rerun()

    with t2:
        imgs = st.session_state.res['imgs']
        if st.session_state.view_img_idx is not None:
            idx = st.session_state.view_img_idx
            if st.button("⬅️ Вернуться к галерее"):
                st.session_state.view_img_idx = None
                st.rerun()
            c1, c2, c3 = st.columns([1, 8, 1])
            with c1: 
                if idx > 0 and st.button("◀️"): st.session_state.view_img_idx -= 1; st.rerun()
            with c2:
                st.image(imgs[idx]['imageUrl'], use_container_width=True)
                st.subheader(imgs[idx].get('title', 'Без названия'))
                st.link_button(f"Источник: {imgs[idx].get('source', 'Сайт')}", imgs[idx]['link'])
            with c3:
                if idx < len(imgs)-1 and st.button("▶️"): st.session_state.view_img_idx += 1; st.rerun()
        else:
            if not imgs: st.write("Картинки не найдены")
            else:
                cols = st.columns(2)
                for i, img in enumerate(imgs[:st.session_state.img_limit]):
                    with cols[i % 2]:
                        st.image(img['imageUrl'])
                        if st.button(f"Увеличить #{i+1}", key=f"zoom_{i}"):
                            st.session_state.view_img_idx = i
                            st.rerun()
                if st.session_state.img_limit < len(imgs):
                    if st.button("Загрузить еще картинки"):
                        st.session_state.img_limit += 6
                        st.rerun()
else:
    # ГЛАВНАЯ (Новости)
    st.write("---")
    st.subheader("Главное сегодня в России")
    news_data = fetch_news(st.secrets.get("SERPER_API_KEY", ""))
    if news_data:
        st.markdown('<div class="news-block">', unsafe_allow_html=True)
        for n in news_data:
            st.markdown(f"""
            <div class="news-item">
                <a class="news-link" href="{n['link']}" target="_blank">{n['title']}</a>
                <div class="news-meta">{n.get('source', 'СМИ')} • {n.get('date', 'Сегодня')}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Загружаю свежие новости...")

st.markdown("<br><hr><center style='color:#aaa; font-size:12px;'>КУСИЦА ПОИСК • 2024</center>", unsafe_allow_html=True)
