import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=API_KEY)

# --- 2026 STABLE MODEL NAMES ---
# Google sunset the '1.5' names. Use these aliases to avoid 404s:
FLASH_MODEL = 'gemini-2.5-flash' 
PRO_MODEL = 'gemini-2.5-pro'

# --- SCRAPER ---
def get_repair_context(system, is_em, model_name, issue):
    headers = {'User-Agent': 'Mozilla/5.0'}
    context = ""
    wiki_path = "EM_Repair" if is_em else system.replace(" ", "_")
    try:
        res = requests.get(f"https://pinwiki.com/wiki/index.php/{wiki_path}", timeout=5)
        context += BeautifulSoup(res.text, 'html.parser').find(id="mw-content-text").get_text()[:3000]
    except: pass
    return context

# --- UI ---
st.set_page_config(page_title="Pinball Doctor", page_icon="🩺")
st.title("🩺 Pinball Doctor")

with st.sidebar:
    st.header("1. Connection Test")
    if st.button("Check API Connection"):
        try:
            # This lists models available to YOUR specific key
            models = [m.name for m in genai.list_models()]
            st.success("Connected!")
            st.write("Available Models:", models)
        except Exception as e:
            st.error(f"Connection Failed: {e}")

    st.header("2. Machine Specs")
    is_em = st.checkbox("Electromechanical (EM) Game")
    if is_em:
        system = st.selectbox("Manufacturer", ["Gottlieb", "Williams", "Bally", "Chicago Coin"])
    else:
        system = st.selectbox("System Architecture", ["Stern SPIKE 2", "Stern SAM", "Williams WPC", "Data East"])
    model_name = st.text_input("Machine Name", value="")

issue = st.text_area("Diagnosis Request", value="Describe the issue")

if st.button("Run Diagnostic"):
    if not model_name or issue == "Describe the issue":
        st.warning("Please fill out the fields.")
    else:
        with st.spinner("Analyzing..."):
            kb_data = get_repair_context(system, is_em, model_name, issue)
            prompt = f"Expert Pinball Repair: {model_name} ({system}). Issue: {issue}. Context: {kb_data}"
            
            try:
                # Using the 2.5-flash alias which replaced 1.5-flash
                model = genai.GenerativeModel(FLASH_MODEL)
                response = model.generate_content(prompt)
                st.markdown(response.text)
            except Exception as e:
                st.error(f"API Error: {e}")
                st.info("Try checking the 'Connection Test' in the sidebar to see which model names your key supports.")
