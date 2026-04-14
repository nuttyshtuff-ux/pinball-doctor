import streamlit as st
import google.generativeai as genai
import requests
import json
from bs4 import BeautifulSoup

# --- 1. CORE SETUP ---
st.set_page_config(page_title="Doctor Pinball", page_icon="🩺")

# --- API CONFIG ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Missing GOOGLE_API_KEY in secrets.")
    st.stop()

MODEL_NAME = "gemini-2.5-flash"
SEARCH_ENGINE_ID = st.secrets.get("SEARCH_ENGINE_ID", None)

# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "specs" not in st.session_state:
    st.session_state.specs = None
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


# --- 2. DEEP TOOLS ---

def scrape_thread_content(url: str) -> str:
    """Scrape limited content from allowed pinball forums/wiki pages."""
    try:
        allowed_domains = ["pinside.com", "pinwiki.com", "arcade-museum.com"]
        if not any(domain in url for domain in allowed_domains):
            return ""

        headers = {"User-Agent": "DoctorPinballDiagnosticBot/1.2 (Educational Use)"}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code != 200:
            return ""

        soup = BeautifulSoup(r.text, "html.parser")

        # Pinside forum posts
        if "pinside.com" in url:
            posts = soup.find_all("div", class_="forum-post-content")
            if not posts:
                return ""
            return "\n".join([p.get_text(strip=True)[:600] for p in posts[:8]])

        # Fallback: generic text
        return soup.get_text()[:2000]
    except Exception:
        return ""


def get_wiki_context(system: str, is_em: bool):
    """Fetch relevant PinWiki content based on system and EM flag."""
    wiki_map = {
        "-35 MPU": "Bally/Stern",
        "-17 MPU": "Bally/Stern",
        "AS-2518": "Bally/Stern",
        "MPU-100": "Bally/Stern",
        "MPU-200": "Bally/Stern",
        "WPC": "Williams_WPC",
        "SYSTEM 11": "Williams_System_11",
        "SYSTEM 3": "Gottlieb_System_3",
        "WHITESTAR": "Sega/Stern_White_Star",
