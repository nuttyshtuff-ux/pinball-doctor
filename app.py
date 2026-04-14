import streamlit as st
import google.generativeai as genai
import requests, json, os
from bs4 import BeautifulSoup
from PIL import Image

# --- 1. CORE SETUP ---
st.set_page_config(page_title="Doctor Pinball", page_icon="🩺")

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Missing GOOGLE_API_KEY in secrets.")
    st.stop()

MODEL_NAME = 'gemini-2.5-flash' 

if "messages" not in st.session_state: st.session_state.messages = []
if "specs" not in st.session_state: st.session_state.specs = None
if "authenticated" not in st.session_state: st.session_state.authenticated = False

# --- 2. THE DEEP TOOLS ---

def scrape_thread_content(url):
    """Targets tech content without bulk crawling."""
    try:
        if not any(domain in url for domain in ["pinside.com", "pinwiki.com", "arcade-museum.com"]):
            return ""
        
        headers = {'User-Agent': 'DoctorPinballDiagnosticBot/1.2 (Educational Use)'}
        r = requests.get(url, headers=headers, timeout=8)
        
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            if "pinside.com" in url:
                # Target the actual user-contributed fix areas
                posts = soup.find_all('div', class_='forum-post-content')
                return "\n".join([p.get_text()[:600] for p in posts[:8]]) 
            return soup.get_text()[:2500]
    except:
        pass
    return ""

def get_wiki_context(system, is_em):
    wiki_map = {
        "WPC": "Williams_WPC", "SYSTEM 11": "Williams_System_11", "SYSTEM 3": "Gottlieb_System_3",
        "SYSTEM 80": "Gottlieb_System_80", "SYSTEM 1": "Gottlieb_System_1", "WHITESTAR": "Sega/Stern_White_Star",
        "SAM": "Stern_SAM", "SPIKE": "Stern_SPIKE", "6803": "Bally_6803", "DATA EAST": "Data_East/Sega",
        "AS-2518": "Bally/Stern", "BALLY SS": "Bally/Stern", "MPU-100": "Bally/Stern", "MPU-200": "Bally/Stern"
    }
    sys_upper = system.upper()
    path = system.replace(" ", "_")
    for key, official_path in wiki_map.items():
        if key in sys_upper:
            path = official_path
            break
    if is_em: path = "EM_Repair"

    full_url = f"https://pinwiki.com/wiki/index.php/{path}"
    try:
        r = requests.get(full_url, timeout=5)
        if r.status_code == 200:
            content = BeautifulSoup(r.text, 'html.parser').find(id="mw-content-text")
            return content.get_text()[:2500], full_url
    except:
        pass
    return "Wiki content unavailable.", "https://pinwiki.com"

def get_deep_search_data(query, mfg, sys):
    tech_boost = f"{mfg} {sys} {query} pinball repair board troubleshooting site:pinside.com OR site:pinwiki.com"
    try:
        url = f"https://www.googleapis.com/customsearch/v1?key={st.secrets['GOOGLE_API_KEY']}&cx={st.secrets['SEARCH_ENGINE_ID']}&q={tech_boost}"
        res = requests.get(url, timeout=5).json()
        if "items" in res:
            deep_results = []
            for i in res['items'][:3]: # Only deep-read the top 3 matches
                content = scrape_thread_content(i['link'])
                deep_results.append(f"SOURCE: {i['title']}\nURL: {i['link']}\nDEEP TEXT: {content}\n---")
            return "\n".join(deep_results)
    except:
        pass
    return "No deep search data available."

# --- 3. UI & CHAT LOGIC ---
st.title("🩺 Doctor Pinball")

if not st.session_state.authenticated:
    pw = st.text_input("Tech Password", type="password")
    if st.button("Login"):
        if pw == st.secrets["TECH_PASSWORD"]:
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# (Sidebar and display logic remains same as v1.1.12...)
with st.sidebar:
    st.header("Repair Bench")
    up_files = st.file_uploader("Upload Docs", type=['png', 'jpg', 'jpeg', 'pdf'], accept_multiple_files=True)
    if st.button("🆕 New Case"):
        st.session_state.messages, st.session_state.specs = [], None
        st.rerun()

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("Enter Mfg + Game"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("DEEP-READING THREADS..."):
            model = genai.GenerativeModel(MODEL_NAME)
            
            # Identification
            if not st.session_state.specs:
                id_p = f"Identify: '{prompt}'. JSON ONLY: {{\"mfg\":\"\", \"system\":\"\", \"is_em\":false, \"game\":\"\"}}"
                res = model.generate_content(id_p)
                st.session_state.specs = json.loads(res.text.strip().replace('```json', '').replace('```', ''))

            spec = st.session_state.specs
            
            # Deep Data Gathering
            wiki_text, wiki_url = get_wiki_context(spec['system'], spec['is_em'])
            deep_data = get_deep_search_data(prompt, spec['mfg'], spec['system'])
            
            ctx = f"""
            You are a Senior Pinball Specialist. 
            Machine: {spec['mfg']} {spec['game']} ({spec['system']})
            
            STRICT CITATION RULE:
            - You MUST credit Pinside threads/users found in DEEP DATA.
            - Provide clickable links: [Title](URL).
            
            DATA:
            Wiki: {wiki_text} (Source: {wiki_url})
            Deep Search: {deep_data}
            """
            
            # Input assembly and model call...
            inputs = [ctx, prompt]
            if up_files:
                for up in up_files:
                    inputs.append(Image.open(up) if up.type != "application/pdf" else {"mime_type": "application/pdf", "data": up.getvalue()})
            
            ans = model.generate_content(inputs).text
            st.markdown(ans)
            st.session_state.messages.append({"role": "assistant", "content": ans})
