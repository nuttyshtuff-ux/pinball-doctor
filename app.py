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
    try:
        if not any(domain in url for domain in ["pinside.com", "pinwiki.com", "arcade-museum.com"]):
            return ""
        headers = {'User-Agent': 'DoctorPinballDiagnosticBot/1.2 (Educational Use)'}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            if "pinside.com" in url:
                posts = soup.find_all('div', class_='forum-post-content')
                return "\n".join([p.get_text()[:600] for p in posts[:8]]) 
            return soup.get_text()[:2000]
    except:
        pass
    return ""

def get_wiki_context(system, is_em):
    wiki_map = {
        "-35 MPU": "Bally/Stern", "-17 MPU": "Bally/Stern", "AS-2518": "Bally/Stern",
        "MPU-100": "Bally/Stern", "MPU-200": "Bally/Stern", "WPC": "Williams_WPC",
        "SYSTEM 11": "Williams_System_11", "SYSTEM 3": "Gottlieb_System_3",
        "WHITESTAR": "Sega/Stern_White_Star", "SAM": "Stern_SAM", "SPIKE": "Stern_SPIKE"
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
    return "Wiki entry unavailable.", full_url

def get_deep_search_data(query, mfg, sys):
    search_terms = f"{mfg} {sys} {query} pinball repair board troubleshooting site:pinside.com"
    try:
        url = f"https://www.googleapis.com/customsearch/v1?key={st.secrets['GOOGLE_API_KEY']}&cx={st.secrets['SEARCH_ENGINE_ID']}&q={search_terms}"
        res = requests.get(url, timeout=5).json()
        if "items" in res:
            results = []
            for i in res['items'][:3]:
                content = scrape_thread_content(i['link'])
                results.append(f"SOURCE: {i['title']}\nURL: {i['link']}\nDEEP DATA: {content}\n---")
            return "\n".join(results)
    except:
        pass
    return "No verified deep search data found."

# --- 3. UI RENDERING (Guaranteed to run) ---
st.title("🩺 Doctor Pinball")

if not st.session_state.authenticated:
    pw = st.text_input("Tech Password", type="password")
    if st.button("Login"):
        if pw == st.secrets["TECH_PASSWORD"]:
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

with st.sidebar:
    st.header("Repair Bench")
    up_files = st.file_uploader("Upload Manuals/Photos", type=['png', 'jpg', 'jpeg', 'pdf'], accept_multiple_files=True)
    if st.button("🆕 New Repair Case"):
        st.session_state.messages, st.session_state.specs = [], None
        st.rerun()

# Display Messages
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. CHAT LOGIC ---
if prompt := st.chat_input("Enter Mfg + Game (e.g. Bally -35 MPU)"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("CONSULTING DOCUMENTATION..."):
            model = genai.GenerativeModel(MODEL_NAME)
            
            # SAFE IDENTIFICATION
            if not st.session_state.specs:
                id_p = f"Identify: '{prompt}'. Return JSON ONLY: {{\"mfg\":\"\", \"system\":\"\", \"is_em\":false, \"game\":\"\"}}"
                try:
                    res = model.generate_content(id_p)
                    # Use a very aggressive clean to prevent JSON decoding errors
                    clean_res = res.text.strip().split('{')[-1].split('}')[0]
                    clean_res = "{" + clean_res + "}"
                    st.session_state.specs = json.loads(clean_res)
                except:
                    st.session_state.specs = {"mfg":"Unknown", "system":"General", "is_em":False, "game":prompt}

            spec = st.session_state.specs
            
            # SAFE DATA GATHERING
            wiki_text, wiki_url = get_wiki_context(spec.get('system', 'General'), spec.get('is_em', False))
            deep_data = get_deep_search_data(prompt, spec.get('mfg', ''), spec.get('system', ''))
            
            ctx = f"""
            You are a Senior Pinball Specialist. 
            Machine: {spec.get('mfg')} {spec.get('game')} ({spec.get('system')})
            
            STRICT CITATION RULE:
            - You MUST credit Pinside/Wiki sources found in the data.
            - Provide clickable links: [Title](URL).
            
            CONTEXT:
            Wiki: {wiki_text} (Source: {wiki_url})
            Community: {deep_data}
            """
            
            inputs = [ctx, prompt]
            if up_files:
                for up in up_files:
                    if up.type == "application/pdf":
                        inputs.append({"mime_type": "application/pdf", "data": up.getvalue()})
                    else:
                        inputs.append(Image.open(up))
            
            try:
                ans = model.generate_content(inputs).text
                st.markdown(ans)
                st.session_state.messages.append({"role": "assistant", "content": ans})
            except Exception as e:
                st.error(f"Diagnostic Error: {str(e)}")
