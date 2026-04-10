import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv

# 1. SETUP & CONFIG
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    st.error("Missing API Key! Please add GOOGLE_API_KEY to your .env file.")
    st.stop()

genai.configure(api_key=API_KEY)

# Use the latest 2026 model strings to avoid 404s
# 'gemini-3-flash-preview' is the current high-speed workhorse
MODEL_NAME = 'gemini-3-flash-preview' 

# 2. THE WEBSCRAPER (PinWiki Specialist)
def get_pinwiki_data(game_system):
    """
    Scrapes repair guides from PinWiki based on the game system (e.g., 'Williams WPC').
    """
    # Example URL structure for PinWiki repair guides
    search_query = game_system.replace(" ", "_")
    url = f"https://pinwiki.com/wiki/index.php/{search_query}_Repair_Selection"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Get the main text content, stripping out nav and scripts
            content = soup.find(id="mw-content-text")
            return content.get_text()[:5000]  # Return first 5k chars as context
        else:
            return "Could not find specific PinWiki guide for this system."
    except Exception as e:
        return f"Scraper error: {str(e)}"

# 3. STREAMLIT UI
st.set_page_config(page_title="Pinball Doctor", page_icon="🕹️")

st.title("🩺 Pinball Doctor")
st.markdown("### Expert Diagnosis & Repair Guide")

with st.sidebar:
    st.header("Machine Profile")
    system = st.selectbox("Game System", 
                          ["Williams WPC", "Bally 6803", "Data East", "Stern SPIKE", "Gottlieb System 1"])
    model_name = st.text_input("Specific Model (e.g., Addams Family)", "Addams Family")

st.info(f"Currently diagnosing: **{model_name}** ({system})")

issue = st.text_area("Describe the symptoms (e.g., 'Left flipper is weak and making a buzzing sound')", height=150)

if st.button("Start Diagnosis"):
    with st.spinner("Consulting repair manuals and forum data..."):
        # Step A: Scrape fresh data
        wiki_context = get_pinwiki_data(system)
        
        # Step B: Construct the prompt with RAG (Retrieval-Augmented Generation)
        prompt = f"""
        You are 'Pinball Doctor', an expert pinball technician. 
        Use the following technical context from PinWiki to help diagnose the user's issue.
        
        TECHNICAL CONTEXT:
        {wiki_context}
        
        USER ISSUE:
        Machine: {model_name} ({system})
        Symptom: {issue}
        
        PLEASE PROVIDE:
        1. Possible Cause (Diagnosis)
        2. Step-by-Step Repair Instructions
        3. Parts Needed (and common suppliers like Marco Specialties or Pinball Life)
        4. Safety Warnings (High voltage areas to avoid)
        """
        
        try:
            model = genai.GenerativeModel(MODEL_NAME)
            response = model.generate_content(prompt)
            
            st.success("Diagnosis Complete")
            st.markdown(response.text)
            
        except Exception as e:
            st.error(f"AI Error: {str(e)}")
            st.info("Tip: If you see a 404, check if 'gemini-3-flash-preview' is still the active alias in AI Studio.")
