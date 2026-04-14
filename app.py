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

MODEL_NAME =
