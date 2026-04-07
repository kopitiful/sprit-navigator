import streamlit as st
import requests
import urllib3
import pandas as pd
import time

# SSL-Warnungen unterdrücken
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- KONFIGURATION (HARDCODED) ---
# Hier deinen Key eintragen
API_KEY = "079fb998-1862-4c70-ba74-3ecc70e41d0a" 

# --- ROBUSTE ORTSSUCHE ---
@st.cache_data(ttl=600) # Speichert Ergebnisse für 10 Minuten
def get_coords(city):
    """Ortssuche mit Timeout-Schutz und Fake-Browser-Header."""
    if not city:
        return None
        
    url = f"https://nominatim.openstreetmap.org/search?q={city},Germany&format=json&limit=1"
    
    # Ein sehr spezifischer User-Agent verhindert, dass du als Bot abgelehnt wirst
    headers = {
        'User-Agent': 'SpritNavigator_Privat_v3',
        'Accept-Language': 'de'
    }
    
    try:
        # Wir setzen den Timeout auf 5 Sekunden. Wenn OSM nicht antwortet, bricht es ab.
        response = requests.get(url, headers=headers, verify=False, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data:
                return (float(data[0]['lat']), float(data[0]['lon']))
        return None
    except Exception as e:
        # Falls die API hängt, geben wir im Terminal eine Info aus
        print(f"DEBUG: Nominatim Fehler -> {e}")
        return None

@st.cache_data(ttl=600)
def get_route(s_coords, e_coords):
    url = f"http://router.project-osrm.org/route/v1/driving/{s_coords[1]},{s_coords[0]};{e_coords[1]},{e_coords[0]}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, verify=False, timeout=10)
        data = r.json()
        if data['code'] == 'Ok':
            return data['routes'][0]['geometry']['coordinates'], data['routes'][0]['distance']
    except: return None, None

def find_stations(waypoints, fuel_type, user_radius):
    all_stations = []
    seen_ids = set()
    
    # Suche alle 8 Punkte für maximale Dichte
    search_indices = list(range(0, len(waypoints), 8))
    if (len(waypoints)-1) not in search_indices:
        search_indices.append(len(waypoints)-1)
        
    for i in search_indices:
        lng, lat = waypoints[i]
        search_radius = float(user_radius)
        url = f"https://creativecommons.tankerkoenig.de/json/list.php?lat={lat}&lng={lng}&rad={search_radius}&type=all&apikey={API_KEY}"
        try:
            res = requests.get(url, verify=False, timeout=5).json()
            if res.get("ok"):
                for s in res["stations"]:
                    if s["id"] not in seen_ids:
                        price = s.get(fuel_type)
                        if price and price > 0:
                            # Profit Logik: Wir vergleichen mit einem "teuren" Preis an der Autobahn (ca. +15 Cent)
                            detour_km = s.get('dist', 0) * 2
                            # Kosten pro km: ca. 0,35€ (Sprit + Verschleiß)
                            profit = (0.15 * 50) - (detour_km * 0.35) 
                            
                            all_stations.append({
                                "Preis": f"{price:.3f} €",
                                "raw_price": price,
                                "Marke": s.get('brand') or "Freie",
                                "Adresse": f"{s.get('street')} {s.get('houseNumber', '')}",
                                "Ort": s.get('place'),
                                "Umweg": f"{detour_km:.1f} km",
                                "Profit": f"{profit:.2f} €",
                                "lat": s.get('lat'),
                                "lon": s.get('lng')
                            })
                            seen_ids.add(s["id"])
        except: continue
    return all_stations

# --- UI ---
st.set_page_config(page_title="Sprit-Navigator Pro", layout="wide")
st.title("⛽ Sprit-Navigator: Profit-Rechner")

with st.sidebar:
    st.header("Einstellungen")
    start_city = st.text_input("Start", "Barver")
    end_city = st.text_input("Ziel", "Bad Bentheim")
    fuel = st.selectbox("Kraftstoff", ["e5", "e10", "diesel"])
    radius = st.slider("Radius (km)", 1, 15, 5)
    btn = st.button("Route & Profit berechnen")

if btn:
    with st.spinner("Prüfe Orte..."):
        s_coords = get_coords(start_city)
        time.sleep(0.5) # Kurze Pause gegen API-Sperre
        e_coords = get_coords(end_city)
        
        if not s_coords or not e_coords:
            st.error("❌ Einer der Orte wurde nicht gefunden (oder die API blockiert).")
            st.info("Tipp: Warte kurz oder ändere den Start/Ziel Namen minimal (z.B. 'Berlin Mitte' statt 'Berlin').")
        else:
            coords, dist = get_route(s_coords, e_coords)
            if coords:
                stations = find_stations(coords, fuel, radius)
                if stations:
                    df = pd.DataFrame(stations).sort_values("raw_price")
                    
                    c1, c2 = st.columns([1, 1])
                    with c1:
                        st.subheader("🗺️ Karte")
                        st.map(df[["lat", "lon"]], size=20, color="#FF0000")
                    with c2:
                        st.subheader("💰 Profit-Tabelle")
                        st.table(df[["Preis", "Marke", "Umweg", "Profit"]].head(10))
                else:
                    st.warning("Keine Tankstellen gefunden.")
