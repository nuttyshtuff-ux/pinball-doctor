# --- IMPROVED SEARCH (v1.1.9) ---
def get_raw_search_data(query, mfg, sys, is_modern_stern=False):
    # Try the specific game first
    queries = [f"{query} pinball troubleshooting", f"{mfg} {sys} pinball repair"]
    
    results = []
    for q in queries:
        try:
            url = f"https://www.googleapis.com/customsearch/v1?key={st.secrets['GOOGLE_API_KEY']}&cx={st.secrets['SEARCH_ENGINE_ID']}&q={q}"
            res = requests.get(url, timeout=5).json()
            if "items" in res:
                results.append("\n".join([f"SOURCE: {i['title']}\nURL: {i['link']}\nCONTENT: {i['snippet']}\n---" for i in res['items'][:3]]))
        except: continue
    
    return "\n".join(results) if results else "No specific community data found."

# --- IMPROVED WIKI (Handles common path errors) ---
def get_wiki_context(system, mfg, is_em):
    # Map common naming variations to PinWiki paths
    paths = [system.replace(" ", "_")]
    if "WPC" in system.upper(): paths.append("Williams_WPC")
    if "System 11" in system: paths.append("Williams_System_11")
    if "Bally" in mfg and not is_em: paths.append("Bally_6803")
    
    for path in paths:
        try:
            r = requests.get(f"https://pinwiki.com/wiki/index.php/{path}", timeout=5)
            if r.status_code == 200:
                content = BeautifulSoup(r.text, 'html.parser').find(id="mw-content-text")
                if content: return content.get_text()[:2000]
        except: continue
    return "Wiki content unavailable for this specific system."
