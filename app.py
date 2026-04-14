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
        allowed = ["pinside.com", "pinwiki.com", "arcade-museum.com"]
        if not any(d in url for d in allowed):
            return ""
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return ""
        soup = BeautifulSoup(r.text, "html.parser")
        if "pinside.com" in url:
            posts = soup.find_all("div", class_="forum-post-content")
            if not posts:
                return ""
            return "\n".join([p.get_text(strip=True)[:600] for p in posts[:5]])
        return soup.get_text()[:2000]
    except Exception:
        return ""

def get_wiki_context(system: str, is_em: bool):
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
        "SAM": "Stern_SAM",
        "SPIKE": "Stern_SPIKE"
    }

    sys_upper = (system or "").upper()
    path = (system or "General").replace(" ", "_")

    for key, mapped in wiki_map.items():
        if key in sys_upper:
            path = mapped
            break

    if is_em:
        path = "EM_Repair"

    url = f"https://pinwiki.com/wiki/index.php/{path}"

    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return "Wiki unavailable.", url

        soup = BeautifulSoup(r.text, "html.parser")
        content = soup.find(id="mw-content-text")
        if not content:
            return "Wiki unavailable.", url

        return content.get_text()[:2500], url
    except Exception:
        return "Wiki unavailable.", url


def get_deep_search_data(query: str, mfg: str, sys: str):
    if not SEARCH_ENGINE_ID:
        return "Deep search disabled (missing SEARCH_ENGINE_ID)."

    try:
        q = f"{mfg} {sys} {query} pinball repair site:pinside.com"
        url = (
            "https://www.googleapis.com/customsearch/v1"
            f"?key={st.secrets['GOOGLE_API_KEY']}"
            f"&cx={SEARCH_ENGINE_ID}"
            f"&q={requests.utils.quote(q)}"
        )

        r = requests.get(url, timeout=5)
        data = r.json()

        if "items" not in data:
            return "No deep search results."

        out = []
        for item in data["items"][:3]:
            link = item.get("link", "")
            title = item.get("title", "Untitled")
            content = scrape_thread_content(link)
            out.append(f"SOURCE: {title}\nURL: {link}\n{content}\n---")

        return "\n".join(out)
    except Exception:
        return "No deep search results."


def identify_machine(prompt: str):
    model = genai.GenerativeModel(
        MODEL_NAME,
        generation_config={"response_mime_type": "application/json"}
    )

    ask = (
        "Identify the pinball machine from this text.\n"
        "Return ONLY JSON:\n"
        "{"
        "\"mfg\":\"\","
        "\"system\":\"\","
        "\"is_em\":false,"
        "\"game\":\"\""
        "}\n\n"
        f"Text: \"{prompt}\""
    )

    try:
        res = model.generate_content(ask)
        return json.loads(res.text)
    except Exception:
        return {"mfg": "Unknown", "system": "General", "is_em": False, "game": prompt}


# ---------------------------------------------------------
# 3. UI + AUTH
# ---------------------------------------------------------

st.title("🩺 Doctor Pinball")

if not st.session_state.authenticated:
    pw = st.text_input("Tech Password", type="password")
    if st.button("Login"):
        if pw == st.secrets.get("TECH_PASSWORD"):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

with st.sidebar:
    st.header("Repair Bench")
    up_files = st.file_uploader(
        "Upload Manuals/Photos",
        type=["png", "jpg", "jpeg", "pdf"],
        accept_multiple_files=True
    )
    if st.button("🆕 New Repair Case"):
        st.session_state.messages = []
        st.session_state.specs = None
        st.rerun()

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# ---------------------------------------------------------
# 4. CHAT LOGIC
# ---------------------------------------------------------

prompt = st.chat_input("Describe the issue (include Mfg + Game + System if known)")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("CONSULTING DOCUMENTATION..."):
            model = genai.GenerativeModel(MODEL_NAME)

            if not st.session_state.specs:
                st.session_state.specs = identify_machine(prompt)

            spec = st.session_state.specs

            wiki_text, wiki_url = get_wiki_context(
                spec.get("system", "General"),
                spec.get("is_em", False)
            )

            deep_data = get_deep_search_data(
                prompt,
                spec.get("mfg", ""),
                spec.get("system", "")
            )
            ctx = f"""
You are a Senior Pinball Specialist.

Machine: {spec.get('mfg')} {spec.get('game')} ({spec.get('system')})

STRICT CITATION RULE:
- You MUST credit Pinside/Wiki sources found in the data.
- Provide clickable links: [Title](URL).

CONTEXT:
Wiki (PinWiki): {wiki_text}
(Source: {wiki_url})

Community (Pinside / others):
{deep_data}
"""
