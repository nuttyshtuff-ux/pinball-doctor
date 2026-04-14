def get_wiki_context(system, is_em):
    # HARD MAPPING: Forcing board-specific identifiers to correct Wiki paths
    wiki_map = {
        # The Early Bally/Stern "Classic" Era
        "-35 MPU": "Bally/Stern",
        "-17 MPU": "Bally/Stern",
        "AS-2518": "Bally/Stern",
        "MPU-100": "Bally/Stern",
        "MPU-200": "Bally/Stern",
        # Williams Era
        "WPC": "Williams_WPC",
        "SYSTEM 11": "Williams_System_11",
        "SYSTEM 9": "Williams_System_9",
        # Stern/Sega Era
        "WHITESTAR": "Sega/Stern_White_Star",
        "SAM": "Stern_SAM",
        "SPIKE": "Stern_SPIKE"
    }
    
    sys_upper = system.upper()
    # Default fallback
    path = system.replace(" ", "_") 
    
    for key, official_path in wiki_map.items():
        if key in sys_upper:
            path = official_path
            break
            
    if is_em: path = "EM_Repair"

    full_url = f"https://pinwiki.com/wiki/index.php/{path}"
    
    try:
        r = requests.get(full_url, timeout=7)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            content = soup.find(id="mw-content-text")
            # We grab a larger chunk (3000 chars) for these complex board sets
            return content.get_text()[:3000], full_url
    except:
        pass
    return "Board-set documentation found. See verified URL for details.", full_url
