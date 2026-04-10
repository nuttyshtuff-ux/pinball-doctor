import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = 'gemini-3-flash-preview' # 2026 stable alias

genai.configure(api_key=API_KEY)

# --- SCRAPER 1: PINWIKI ---
def get_pinwiki_data(system):
    formatted = system.replace(" ", "_")
    url = f"https://pinwiki.com/wiki/index.php/{formatted}"
    try:
        res = requests.get(url, timeout=5)
        return BeautifulSoup(res.text, 'html.parser').find(id="mw-content-text").get_text()[:4000]
    except:
        return ""

# --- SCRAPER 2: PINSIDE (New!) ---
def get_pinside_data(query):
    """Searches Pinside forum topics for the specific issue."""
    # Pinside requires a 'User-Agent' header to look like a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    search_url = f"https://pinside.com/pinball/forum/search?s={query.replace(' ', '+')}"
    
    try:
        res = requests.get(search_url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # Extract snippets from the search result titles and descriptions
            threads = soup.find_all('div', class_='search-result-content')
            context = "Recent Pinside Discussions:\n"
            for t in threads[:3]: # Grab the top 3 relevant threads
                context += f"- {t.get_text(separator=' ', strip=True)}\n"
            return context
        return "Pinside search unavailable."
    except:
        return "Could not reach Pinside."

# --- UI ---
st.set_page_config(page_title="Pinball Doctor", page_icon="🩺")
st.title("🩺 Pinball Doctor v3.0")

with st.sidebar:
    st.header("Settings")
    system = st.selectbox("System", ["Williams WPC", "Stern SPIKE 2", "Bally 6803", "EM Repair"])
    model_name = st.text_input("Machine Name", "The Addams Family")

issue = st.text_area("What's the problem?", "The Thing hand is stuck.")

if st.button("Diagnose"):
    with st.spinner("Searching PinWiki and Pinside..."):
        # 1. Gather Context
        wiki = get_pinwiki_data(system)
        pinside = get_pinside_data(f"{model_name} {issue}")
        
        # 2. Build Prompt
        full_prompt = f"""
        You are Pinball Doctor. 
        KNOWLEDGE BASE 1 (PinWiki): {wiki}
        KNOWLEDGE BASE 2 (Pinside): {pinside}
        
        ISSUE: {model_name} - {issue}
        
        Based on the technical data and community discussions above, provide a 
        repair guide including parts and common 'Pinside' community fixes.
        """
        
        # 3. Call AI
        try:
            model = genai.GenerativeModel(MODEL_NAME)
            response = model.generate_content(full_prompt)
            st.markdown(response.text)
        except Exception as e:
            st.error(f"Error: {e}")
