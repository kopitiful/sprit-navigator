import streamlit as st
import requests
import urllib3
import pandas as pd

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATION ---
# Try to load from secrets first (production), fall back to env var or hardcoded (testing)
try:
    API_KEY = st.secrets["TANKERKOENIG_API_KEY"]
except KeyError:
    import os
    API_KEY = os.getenv("TANKERKOENIG_API_KEY")
    
    if not API_KEY:
        # ⚠️ TESTING ONLY - Remove before production!
        API_KEY = "079fb998-1862-4c70-ba74-3ecc70e41d0a"
        st.warning("⚠️ Using hardcoded API key (testing mode). This is NOT secure for production!")
    
    if not API_KEY:
        st.error("❌ API-Key not found!")
        st.info("Set via: `.streamlit/secrets.toml` or `TANKERKOENIG_API_KEY` environment variable")
        st.stop()


# --- FUNCTIONS ---
@st.cache_data(ttl=600)
def get_coords(city):
    """Get coordinates for a German city via Nominatim."""
    if not city or not city.strip():
        return None
    
    url = f"https://nominatim.openstreetmap.org/search?q={city},Germany&format=json&limit=1"
    headers = {'User-Agent': 'SpritNavigator_Streamlit_2026'}
    
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=5)
        r.raise_for_status()
        data = r.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except requests.Timeout:
        st.error(f"⏱️ Timeout bei Ortssuche für '{city}'")
    except Exception as e:
        st.error(f"❌ Fehler bei Ortssuche: {e}")
    
    return None


@st.cache_data(ttl=600)
def get_route(s_coords, e_coords):
    """Calculate driving route via OSRM."""
    if not s_coords or not e_coords:
        return None, None
    
    url = f"http://router.project-osrm.org/route/v1/driving/{s_coords[1]},{s_coords[0]};{e_coords[1]},{e_coords[0]}?overview=full&geometries=geojson"
    
    try:
        r = requests.get(url, verify=False, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        if data.get('code') == 'Ok' and data.get('routes'):
            route = data['routes'][0]
            coords = route.get('geometry', {}).get('coordinates', [])
            distance = route.get('distance')
            return coords, distance
    except Exception as e:
        st.error(f"❌ Routenberechnung fehlgeschlagen: {e}")
    
    return None, None


def find_stations(waypoints, fuel_type, radius, api_key):
    """Find gas stations along waypoints."""
    all_stations = []
    seen_ids = set()
    
    for lng, lat in waypoints:
        url = f"https://creativecommons.tankerkoenig.de/json/list.php?lat={lat}&lng={lng}&rad={radius}&type=all&apikey={api_key}"
        
        try:
            res = requests.get(url, verify=False, timeout=5).json()
            
            if not res.get("ok"):
                st.warning(f"API Fehler bei {lat},{lng}: {res.get('message', 'Unbekannter Fehler')}")
                continue
            
            for station in res.get("stations", []):
                if station["id"] in seen_ids:
                    continue
                
                price = station.get(fuel_type)
                if not price or price <= 0:
                    continue
                
                brand = station.get('brand')
                if not brand or str(brand).strip() in ["", "None", "null"]:
                    brand = "Freie Tankstelle"
                
                address = f"{station.get('street', '')} {station.get('houseNumber', '')}".strip()
                
                all_stations.append({
                    "Preis": f"{price:.3f} €",
                    "Marke": brand,
                    "Adresse": address,
                    "Ort": station.get('place', 'N/A'),
                    "Status": "✅ Offen" if station.get("isOpen") else "❌ Geschlossen",
                    "raw_price": price
                })
                seen_ids.add(station["id"])
        
        except Exception as e:
            st.warning(f"Fehler bei Station-Abfrage: {e}")
            continue
    
    return all_stations


# --- STREAMLIT UI ---
st.set_page_config(page_title="Sprit-Navigator Pro", page_icon="⛽", layout="wide")
st.title("⛽ Sprit-Navigator Pro")
st.markdown("Finde die günstigsten Tankstellen entlang deiner Fahrtstrecke.")

# Sidebar
with st.sidebar:
    st.header("⚙️ Einstellungen")
    st.info("ℹ️ Hinweis: VPN am Mac muss aktiv sein für API-Abfragen.")

# Input form
col1, col2 = st.columns(2)
with col1:
    start_city = st.text_input("🚀 Startpunkt", value="Barver", placeholder="z.B. Barver")
with col2:
    end_city = st.text_input("🎯 Zielort", value="Bad Bentheim", placeholder="z.B. Bad Bentheim")

col1, col2 = st.columns(2)
with col1:
    fuel_type = st.selectbox("⛽ Kraftstoff", ["e5", "e10", "diesel"])
with col2:
    radius = st.slider("🔍 Such-Radius (km)", 1, 15, 5)

# Main action button
if st.button("🔍 Günstigste Tankstellen finden", use_container_width=True):
    with st.spinner("📍 Orte lokalisieren..."):
        s_coords = get_coords(start_city)
        e_coords = get_coords(end_city)
    
    if not s_coords or not e_coords:
        st.error("❌ Einer oder beide Orte konnten nicht gefunden werden. Schreibweise prüfen!")
        st.stop()
    
    with st.spinner("🛣️ Route berechnen..."):
        coords, dist = get_route(s_coords, e_coords)
    
    if not coords or not dist:
        st.error("❌ Routenberechnung fehlgeschlagen.")
        st.stop()
    
    dist_km = dist / 1000
    st.success(f"✅ Route gefunden: **{dist_km:.1f} km**")
    
    # Calculate waypoints every ~15km
    step_size = max(1, len(coords) // max(1, int(dist_km / 15)))
    waypoints = coords[::step_size]
    if coords[-1] not in waypoints:
        waypoints.append(coords[-1])
    
    st.info(f"🔍 Durchsuche {len(waypoints)} Wegpunkte nach Tankstellen...")
    
    with st.spinner("⛽ Suche Tankstellen..."):
        all_stations = find_stations(waypoints, fuel_type, radius, API_KEY)
    
    if all_stations:
        df = pd.DataFrame(all_stations).sort_values("raw_price")
        
        st.success(f"✅ **{len(all_stations)} Tankstellen** gefunden!")
        
        # Display table
        st.subheader(f"💰 Top 15 günstigste {fuel_type.upper()}-Preise")
        display_cols = ["Preis", "Marke", "Adresse", "Ort", "Status"]
        st.table(df[display_cols].head(15))
        
        # Show cheapest
        cheapest = df.iloc[0]
        st.markdown(f"""
        ### 🏆 Günstigste Tankstelle
        **{cheapest['Marke']}** - {cheapest['Preis']}  
        {cheapest['Adresse']}, {cheapest['Ort']}  
        {cheapest['Status']}
        """)
    else:
        st.warning(f"❌ Keine {fuel_type.upper()}-Tankstellen im Radius von {radius}km gefunden.")
