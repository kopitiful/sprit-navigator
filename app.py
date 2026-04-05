import streamlit as st
import requests
import time
import urllib3
import pandas as pd

# Warnungen und SSL-Fix
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- KONFIGURATION ---
import streamlit as st

API_KEY = st.secrets["TANKERKOENIG_API_KEY"]

# --- FUNKTIONEN ---
def get_coords(city):
    url = f"https://nominatim.openstreetmap.org/search?q={city},Germany&format=json&limit=1"
    headers = {'User-Agent': 'SpritApp_Streamlit'}
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=5)
        data = r.json()
        if data: return float(data[0]['lat']), float(data[0]['lon'])
    except: return None

def get_route(s_coords, e_coords):
    url = f"http://router.project-osrm.org/route/v1/driving/{s_coords[1]},{s_coords[0]};{e_coords[1]},{e_coords[0]}?overview=full&geometries=geojson"
    r = requests.get(url, verify=False)
    data = r.json()
    return data['routes'][0]['geometry']['coordinates'], data['routes'][0]['distance']
try:
                    r = requests.get(url, verify=False, timeout=5)
                    res = r.json()
                    if res.get("ok"):
                        # ... (dein bisheriger Code zum Hinzufügen der Stationen)
                    else:
                        # HIER: Fehlermeldung der API anzeigen
                        st.error(f"API Fehler: {res.get('message')}")
                except Exception as e:
                    st.error(f"Verbindungsfehler: {e}")

# --- STREAMLIT UI ---
st.set_page_config(page_title="Sprit-Navigator", page_icon="⛽")
st.title("⛽ Sprit-Navigator Pro")
st.markdown("Finde die günstigsten Preise entlang deiner Route.")

# Sidebar für Einstellungen
with st.sidebar:
    st.header("Einstellungen")
    fuel_type = st.selectbox("Kraftstoff", ["e5", "e10", "diesel"])
    radius = st.slider("Such-Radius (km)", 1, 15, 5)
    st.info("Hinweis: VPN am Mac muss für die Abfrage aktiv sein!")

# Eingabefelder
col1, col2 = st.columns(2)
with col1:
    start_city = st.text_input("Start", value="Barver")
with col2:
    end_city = st.text_input("Ziel", value="Bad Bentheim")

if st.button("Route berechnen & Preise suchen"):
    with st.spinner("Berechne Route und scanne Preise..."):
        s_loc = get_coords(start_city)
        e_loc = get_coords(end_city)
        
        if s_loc and e_loc:
            coords, dist = get_route(s_loc, e_loc)
            dist_km = dist / 1000
            st.success(f"Route gefunden: {dist_km:.1f} km")
            
            # Wegpunkte
            step_size = max(1, len(coords) // max(1, int(dist_km / 15)))
            waypoints = coords[::step_size]
            
            all_stations = []
            seen_ids = set()

            for lng, lat in waypoints:
                url = f"https://creativecommons.tankerkoenig.de/json/list.php?lat={lat}&lng={lng}&rad={radius}&type=all&apikey={API_KEY}"
                try:
                    res = requests.get(url, verify=False).json()
                    if res.get("ok"):
                        for s in res["stations"]:
                            if s["id"] not in seen_ids:
                                p = s.get(fuel_type)
                                if p and p > 0:
                                    all_stations.append({
                                        "Preis": f"{p:.3f} €",
                                        "Marke": s.get('brand') or "Freie Tankstelle",
                                        "Adresse": f"{s.get('street')} {s.get('houseNumber', '')}",
                                        "Ort": s.get('place'),
                                        "Status": "✅" if s.get("isOpen") else "❌",
                                        "raw_price": p
                                    })
                                    seen_ids.add(s["id"])
                except: pass
            
            if all_stations:
                df = pd.DataFrame(all_stations).sort_values("raw_price")
                st.table(df[["Preis", "Marke", "Adresse", "Ort", "Status"]].head(15))
            else:
                st.warning("Keine Tankstellen gefunden.")
        else:
            st.error("Orte nicht gefunden.")
