import streamlit as st
import google.generativeai as genai
import requests
import json
from bs4 import BeautifulSoup

# ---------------------------------------------------------
# 1. CORE SETUP
# ---------------------------------------------------------

st.set_page_config(page_title="Doctor Pinball", page_icon="🩺")

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Missing GOOGLE_API_KEY in secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

MODEL_NAME = "gemini-2.5-flash"
SEARCH_ENGINE_ID = st.secrets.get("SEARCH_ENGINE_ID")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "specs" not in st.session_state:
    st.session_state.specs = None
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# ---------------------------------------------------------
# 2. SCRAPING + DATA HELPERS
# ---------------------------------------------------------

def scrape_thread_content(url: str) -> str:
    try:
        allowed
