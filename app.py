import streamlit as st
import requests
import uuid
import pytz
from datetime import datetime

# 1. Настройка страницы
st.set_page_config(page_title="КУСИЦА", page_icon="🔍", layout="wide")

# 2. Яндекс-портал CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #fff; color: #000; }
    
    .logo { font-size: 38px; font-weight: 900; letter-spacing: -2px; color: #000; margin-bottom: 5px; }
    
    .informer-box { display: flex; flex-wrap: wrap; gap: 8px; font-size: 11px; margin-bottom: 20px; }
    .informer-item { background: #f2f2f4; padding: 4px 10px; border-radius: 12px; display: flex; align-items: center; gap: 4px; color: #555; white-space: nowrap; }
    .currency-red { border: 1px solid #ff4b4b; background: #fff5f5; color: #ff4b4b; font-weight: bold; }

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
        background: #fff; padding: 25px; border-radius: 20px; 
        box-shadow: 0 10px 40px rgba(0,0,0,0.05); border-left: 6px solid #8e44ad; margin-top: 15px; 
    }
    .alice-label { color: #8e44ad; font-weight: bold; font-size: 13px; margin-bottom: 8px; text-transform: uppercase; }

    .search-result { margin-bottom: 20px; }
    .search-title { font-size: 19px; color: #1a0dab; text-decoration: none; font-weight: 500; }
    .search-url { color: #006621; font-size: 13px; display: block; margin-top: 2px; }
    .search-desc { color: #444; font-size: 14px; margin-top: 4px; line-height: 1.5; }

    .news-item { padding: 10px 0; border-bottom: 1px solid #f0f0f0; font-size: 15px; }
    .news-item a { color: #000; text-decoration: none; font-weight: 500; }

    /* Поле уточнения */
    .follow-up-box { margin-top: 15px; padding: 10px; background: #f9f9f9; border-radius: 15px; border: 1px dashed #ccc; }
    </style>
    """, unsafe_allow_html=True)

# 3. Инициализация памяти (Session State)
if 'res' not in st.session_state: st.session_state.res = None
if 'link_limit' not in st.session_state: st.session_state.link_limit = 3
if 'img_limit' not in st.session_state: st.session_state.img_limit = 4
if 'view_img_idx' not in st.session_state: st.session_state.view_img_idx = None
if 'follow_up_ans' not in st.session_state: st.session_state.follow_up_ans = None

# 4. Функции данных
@st.cache_data(ttl=600)
def get_top_data():
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
def get_real_news(key):
    try:
        r = requests.post("https://google.serper.dev/news", headers={'X-API-KEY': key}, json={"q": "главные новости", "gl": "ru", "hl": "ru"}).json()
        return r.get('news', [])[:5]
    except: return []

def get_ai_answer(msgs):
    try:
        auth = st.secrets["GIGACHAT_CREDENTIALS"]
        auth_res = requests.post("https://ngw.devices.sberbank.ru:9443/api/v2/oauth", 
                               headers={'Authorization': f'Basic {auth}', 'RqUID': str(uuid.uuid4()), 'Content-Type': 'application/x-www-form-urlencoded'},
                               data={'scope': 'GIGACHAT_API_PERS'}, verify=False, timeout=10)
        token = auth_res.json()['access_token']
        chat_res = requests.post("https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                               headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
                               json={"model": "GigaChat", "messages": msgs, "temperature": 0.7}, verify=False, timeout=20)
        data = chat_res.json()
        return data['choices'][0]['message']['content'] if 'choices' in data else f"Ошибка ИИ: {data.get('message', 'Нет ответа')}"
    except Exception as e:
        return f"Ошибка ассистента: {str(e)}"

# --- ШАПКА ---
d, tm, tk, wm, ws, usd_r, eur_r = get_top_data()
col_logo, col_info = st.columns([1, 4])
with col_logo: st.markdown('<div class="logo">КУСИЦА</div>', unsafe_allow_html=True)
with col_info:
    st.markdown(f"""
    <div class="informer-box">
        <div class="informer-item">📅 {d}</div><div class="informer-item">🕒 МСК {tm}</div>
        <div class="informer-item">🇰🇿 КЗ {tk}</div><div class="informer-item">🌡️ МСК {wm}</div>
        <div class="informer-item">🌡️ СПБ {ws}</div>
        <div class="informer-item currency-red">USD {usd_r}₽</div><div class="informer-item currency-red">EUR {eur_r}₽</div>
    </div>
    """, unsafe_allow_html=True)

# --- ПОИСК ---
col_q, col_b = st.columns([7, 1])
with col_q: q = st.text_input("", placeholder="Найдётся всё...", key="main_search_bar", label_visibility="collapsed")
with col_b: btn = st.button("➔")

if (btn or q) and q:
    if st.session_state.get('last_q') != q:
        with st.spinner(" "):
            try:
                s_key = st.secrets["SERPER_API_KEY"]
                sr = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': s_key}, json={"q": q, "hl": "ru"}).json()
                ir = requests.post("https://google.serper.dev/images", headers={'X-API-KEY': s_key}, json={"q": q}).json()
                links = sr.get('organic', [])
                ans = get_ai_answer([{"role":"system","content":"Ты Кусица. Отвечай кратко."}, {"role":"user","content":f"Запрос: {q}\nДанные: {links[:3]}"}])
                st.session_state.res = {"ans": ans, "links": links, "imgs": ir.get('images', []), "q": q}
                st.session_state.last_q = q
                st.session_state.follow_up_ans = None
                st.session_state.link_limit, st.session_state.img_limit = 3, 4
                st.session_state.view_img_idx = None
            except: st.error("Ошибка сети")

# --- ВЫВОД РЕЗУЛЬТАТОВ ---
if st.session_state.res:
    t1, t2 = st.tabs(["🔍 Поиск", "🖼️ Картинки"])
    
    with t1:
        res = st.session_state.res
        # Основной ответ
        st.markdown(f'<div class="alice-card"><div class="alice-label">✨ Ассистент Кусица</div>{res["ans"]}</div>', unsafe_allow_html=True)
        
        # Уточнение запроса
        st.write("")
        with st.container():
            f_q = st.text_input("Уточнить запрос у Кусицы...", key="follow_up_input")
            if f_q:
                with st.spinner(" "):
                    f_ans = get_ai_answer([
                        {"role":"system","content":f"Ты Кусица. Контекст поиска: {res['q']}"},
                        {"role":"assistant","content":res['ans']},
                        {"role":"user","content":f_q}
                    ])
                    st.session_state.follow_up_ans = f_ans
            
            if st.session_state.follow_up_ans:
                st.info(f"**Уточнение:** {st.session_state.follow_up_ans}")

        st.write("---")
        # Ссылки
        for l in res['links'][:st.session_state.link_limit]:
            st.markdown(f'<div class="search-result"><a class="search-title" href="{l["link"]}" target="_blank">{l["title"]}</a><span class="search-url">{l["link"][:70]}...</span><div class="search-desc">{l.get("snippet","")}</div></div>', unsafe_allow_html=True)
        
        if st.session_state.link_limit < len(res['links']):
            if st.button("Показать еще ссылки"):
                st.session_state.link_limit += 5
                st.rerun()

    with t2:
        imgs = st.session_state.res['imgs']
        if st.session_state.view_img_idx is not None:
            idx = st.session_state.view_img_idx
            if st.button("⬅️ Назад"):
                st.session_state.view_img_idx = None
                st.rerun()
            c1, c2, c3 = st.columns([1, 8, 1])
            with c1: 
                if idx > 0:
                    if st.button("◀️"): st.session_state.view_img_idx -= 1; st.rerun()
            with c2:
                st.image(imgs[idx]['imageUrl'], use_container_width=True)
                st.subheader(imgs[idx].get('title', ''))
                st.link_button(f"Источник: {imgs[idx].get('source', 'Сайт')}", imgs[idx]['link'])
            with c3:
                if idx < len(imgs)-1:
                    if st.button("▶️"): st.session_state.view_img_idx += 1; st.rerun()
        else:
            if not imgs: st.write("Картинки не найдены")
            else:
                cols = st.columns(2)
                for i, img in enumerate(imgs[:st.session_state.img_limit]):
                    with cols[i % 2]:
                        st.image(img['imageUrl'])
                        if st.button(f"Увеличить #{i+1}", key=f"btn_z_{i}"):
                            st.session_state.view_img_idx = i
                            st.rerun()
                if st.session_state.img_limit < len(imgs):
                    if st.button("Показать еще картинки"):
                        st.session_state.img_limit += 6
                        st.rerun()
else:
    # ГЛАВНАЯ
    st.write("---")
    st.subheader("Главное сегодня")
    news_key = st.secrets.get("SERPER_API_KEY")
    if news_key:
        for n in get_real_news(news_key):
            st.markdown(f'<div class="news-item"><a href="{n["link"]}" target="_blank">{n["title"]}</a><br><small>{n.get("source","")} • {n.get("date","")}</small></div>', unsafe_allow_html=True)

st.markdown("<br><hr><center style='color:#999; font-size:11px;'>КУСИЦА • 2024</center>", unsafe_allow_html=True)
