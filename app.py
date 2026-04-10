import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
import json
from PIL import Image
from dotenv import load_dotenv

# --- SETUP (NO CHANGES TO GOOGLE CALLS) ---
load_dotenv()
API_KEY = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=API_KEY)
MODEL_NAME = 'gemini-2.5-flash'

if "messages" not in st.session_state:
    st.session_state.messages = []
if "specs" not in st.session_state:
    st.session_state.specs = None

# --- UI: SECURE TECH ACCESS ---
with st.sidebar:
    st.header("🔐 Tech Access")
    # Pulling password from Secrets for real security
    tech_pass = st.text_input("Enter Tech Password", type="password")
    
    if tech_pass == st.secrets["TECH_PASSWORD"]:
        st.success("Access Granted")
        st.header("Visual Aid")
        uploaded_file = st.file_uploader("Upload Schematic/Photo", type=['png', 'jpg', 'jpeg'])
        if st.session_state.specs:
            if st.button("New Repair Case"):
                st.session_state.clear()
                st.rerun()
    elif tech_pass != "":
        st.error("Incorrect Password")

# --- MAIN APP LOGIC ---
if tech_pass == st.secrets.get("TECH_PASSWORD"):
    st.title("🩺 Pinball Doctor")

    if not st.session_state.specs:
        st.info("What's the machine and the issue?")
    else:
        s = st.session_state.specs
        st.caption(f"🔧 Repairing: **{s.get('game')}** | {s.get('mfg')} {s.get('system')}")

    # Display Chat History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # The Chat Box
    if prompt := st.chat_input(""):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Diagnosing..."):
                # 1. Identify machine if first time
                if not st.session_state.specs:
                    model = genai.GenerativeModel(MODEL_NAME)
                    id_prompt = f"Identify pinball machine for: '{prompt}'. Return ONLY JSON: {{\"mfg\":\"\", \"system\":\"\", \"is_em\":false, \"game\":\"\"}}"
                    try:
                        res = model.generate_content(id_prompt)
                        st.session_state.specs = json.loads(res.text.strip().replace('```json', '').replace('```', ''))
                    except:
                        if "cactus" in prompt.lower():
                            st.session_state.specs = {"mfg": "Gottlieb", "system": "System 3", "is_em": False, "game": "Cactus Jack's"}
                        else:
                            st.session_state.specs = {"mfg": "Unknown", "system": "General", "is_em": False, "game": "Pinball Machine"}
                
                specs = st.session_state.specs
                img = Image.open(uploaded_file) if uploaded_file else None
                
                # 2. Scraper Context
                context = ""
                try:
                    sys_name = specs.get('system', 'General').replace(" ", "_")
                    wiki_path = "EM_Repair" if specs.get('is_em') else sys_name
                    res = requests.get(f"https://pinwiki.com/wiki/index.php/{wiki_path}", timeout=5)
                    context = BeautifulSoup(res.text, 'html.parser').find(id="mw-content-text").get_text()[:2500]
                except: pass

                # 3. Final Diagnosis
                history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[:-1]])
                full_prompt = [f"Role: Pinball Doctor. Game: {specs.get('game')}. Data: {context}. History: {history}. Input: {prompt}"]
                if img:
                    full_prompt.append(img)
                
                try:
                    model = genai.GenerativeModel(MODEL_NAME)
                    response = model.generate_content(full_prompt)
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"API Error: {e}")
else:
    # If not logged in, show a simple landing page
    st.title("🩺 Pinball Doctor")
    st.warning("Please enter the Tech Password in the sidebar to begin diagnosis.")
