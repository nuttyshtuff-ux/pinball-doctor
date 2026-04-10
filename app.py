import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv

# 1. SETUP - Keeping your exact working configuration
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=API_KEY)

# 2. THE SCRAPER (PinWiki & Pinside)
def get_repair_context(system, is_em, model_name, issue):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    context = ""
    
    # Target PinWiki
    wiki_path = "EM_Repair" if is_em else system.replace(" ", "_")
    try:
        wiki_res = requests.get(f"https://pinwiki.com/wiki/index.php/{wiki_path}", timeout=5)
        if wiki_res.status_code == 200:
            context += BeautifulSoup(wiki_res.text, 'html.parser').find(id="mw-content-text").get_text()[:3000]
    except: pass

    # Target Pinside
    search_q = f"{model_name} {issue}".replace(" ", "+")
    try:
        pinside_res = requests.get(f"https://pinside.com/pinball/forum/search?s={search_q}", headers=headers, timeout=5)
        if pinside_res.status_code == 200:
            soup = BeautifulSoup(pinside_res.text, 'html.parser')
            threads = soup.find_all('div', class_='search-result-content')
            context += "\n\nCommunity Insights:\n" + "\n".join([t.get_text(strip=True) for t in threads[:2]])
    except: pass
    
    return context

# 3. UI SETUP
st.set_page_config(page_title="Pinball Doctor", page_icon="🩺")
st.title("🩺 Pinball Doctor")

with st.sidebar:
    st.header("Machine Specs")
    
    # EM Checkbox
    is_em = st.checkbox("Electromechanical (EM) Game")
    
    # Dynamic System Selection
    if is_em:
        system = st.selectbox("Manufacturer", ["Gottlieb", "Williams", "Bally", "Chicago Coin", "United"])
    else:
        system = st.selectbox("System Architecture", [
            "Stern SPIKE 2", "Stern SPIKE 1", "Stern SAM", "Stern Whitestar", 
            "Stern MPU-200", "Williams WPC", "Williams System 11", 
            "Bally 6803", "Data East", "Gottlieb System 1", "Gottlieb System 80"
        ])

    # Empty Machine Box (No prepopulation)
    model_name = st.text_input("Machine Name", value="")

# Prepopulated Issue Box
issue = st.text_area("Diagnosis Request", value="Describe the issue")

if st.button("Run Diagnostic"):
    if not model_name or issue == "Describe the issue":
        st.warning("Please enter a Machine Name and describe the symptoms.")
    else:
        with st.spinner("Consulting the archives..."):
            kb_data = get_repair_context(system, is_em, model_name, issue)
            
            prompt = f"""
            Role: Expert Pinball Technician
            Machine: {model_name} ({system})
            Issue: {issue}
            Context: {kb_data}
            
            Provide a diagnosis, repair steps, and parts list.
            """
            
            try:
                # REVERTED: Using your original model strings to ensure no 404s
                model = genai.GenerativeModel('gemini-1.5-flash') 
                response = model.generate_content(prompt)
                st.success(f"Diagnosis for {model_name} Ready")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"API Error: {e}")
