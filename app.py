import streamlit as st
import requests
import urllib3
import pandas as pd

# SSL-Warnungen unterdrücken (wichtig für Mac & Cloud)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- KONFIGURATION (Secrets) ---
# Der Key wird aus dem Streamlit Dashboard geladen
try:
    API_KEY = st.secrets["TANKERKOENIG_API_KEY"]
except:
    st.error("❌ API-Key nicht in den Secrets gefunden!")
    st.stop()

# --- FUNKTIONEN ---
def get_coords(city):
    """Ortssuche via Nominatim."""
    url = f"https://nominatim.openstreetmap.org/search?q={city},Germany&format=json&limit=1"
    headers = {'User-Agent': 'SpritNavigator_App_2026'}
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=10)
        data = r.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except:
        return None

def get_route(s_coords, e_coords):
    """Echte Route via OSRM berechnen."""
    url = f"http://router.project-osrm.org/route/v1/driving/{s_coords[1]},{s_coords[0]};{e_coords[1]},{e_coords[0]}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, verify=False, timeout=10)
        data = r.json()
        if data['code'] == 'Ok':
            return data['routes'][0]['geometry']['coordinates'], data['routes'][0]['distance']
    except:
        return None, None

# --- STREAMLIT UI ---
st.set_page_config(page_title="Sprit-Navigator Pro", page_icon="⛽")
st.title("⛽ Sprit-Navigator Pro")
st.markdown("Finde die günstigsten Preise direkt an deiner Fahrtstrecke.")

# Eingabemaske
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        start_city = st.text_input("Startpunkt", value="Barver")
    with col2:
        end_city = st.text_input("Zielort", value="Bad Bentheim")
    
    fuel_type = st.selectbox("Kraftstoff wählen", ["e5", "e10", "diesel"])
    radius = st.slider("Such-Radius abseits der Route (km)", 1, 15, 5)

if st.button("Günstigste Tankstellen finden"):
    with st.spinner("Route wird analysiert..."):
        s_loc = get_coords(start_city)
        e_loc = get_coords(end_city)
        
        if s_loc and e_loc:
            coords, dist = get_route(s_loc, e_loc)
            
            if coords:
                dist_km = dist / 1000
                st.info(f"🛣️ Route erkannt: {dist_km:.1f} km")
                
                # Wegpunkte alle ~15km setzen
                step_size = max(1, len(coords) // max(1, int(dist_km / 15)))
                waypoints = coords[::step_size]
                if coords[-1] not in waypoints:
                    waypoints.append(coords[-1])
                
                all_stations = []
                seen_ids = set()

                # Tankstellen abfragen
                for lng, lat in waypoints:
                    url = f"https://creativecommons.tankerkoenig.de/json/list.php?lat={lat}&lng={lng}&rad={radius}&type=all&apikey={API_KEY}"
                    try:
                        res = requests.get(url, verify=False, timeout=5).json()
                        if res.get("ok"):
                            for s in res["stations"]:
                                if s["id"] not in seen_ids:
                                    price = s.get(fuel_type)
                                    if price and price > 0:
                                        # Marke & Adresse aufbereiten
                                        brand = s.get('brand')
                                        if not brand or str(brand).strip() in ["", "None", "null"]:
                                            brand = "Freie Tankstelle"
                                        
                                        addr = f"{s.get('street')} {s.get('houseNumber', '')}".strip()
                                        
                                        all_stations.append({
                                            "Preis": f"{price:.3f} €",
                                            "Marke": brand,
                                            "Adresse": addr,
                                            "Ort": s.get('place'),
                                            "Status": "✅ Offen" if s.get("isOpen") else "❌ Zu",
                                            "raw_price": price
                                        })
                                        seen_ids.add(s["id"])
                    except:
                        continue
                
                if all_stations:
                    # Sortieren nach Preis
                    df = pd.DataFrame(all_stations).sort_values("raw_price")
                    st.success(f"Gefunden: {len(all_stations)} Tankstellen an der Strecke.")
                    # Tabelle anzeigen (ohne die Hilfsspalte raw_price)
                    st.table(df[["Preis", "Marke", "Adresse", "Ort", "Status"]].head(15))
                else:
                    st.warning("Keine Tankstellen im gewählten Radius gefunden.")
            else:
                st.error("Routenberechnung fehlgeschlagen.")
        else:
            st.error("Einer der Orte wurde nicht gefunden. Bitte Schreibweise prüfen.")
