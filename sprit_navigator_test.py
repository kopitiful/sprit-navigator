import streamlit as st
import requests
import urllib3
import pandas as pd
import os
from pathlib import Path

# Load from .env if it exists
env_file = Path(".env")
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value.strip('"').strip("'")

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATION ---
API_KEY = None

# Try Streamlit secrets (Streamlit Cloud)
try:
    API_KEY = st.secrets["TANKERKOENIG_API_KEY"]
except KeyError:
    pass

# Try environment variable (local development)
if not API_KEY:
    API_KEY = os.getenv("TANKERKOENIG_API_KEY")

# If still no API key, show error
if not API_KEY:
    st.error("❌ API-Key nicht gefunden!")
    st.info("""
    **Lokale Entwicklung:**
    Erstelle eine `.env` Datei:
    ```
    TANKERKOENIG_API_KEY="dein-api-key"
    ```
    
    **Streamlit Cloud:**
    1. Gehe zu App Settings
    2. Klick "Secrets"
    3. Füge hinzu: `TANKERKOENIG_API_KEY = "dein-api-key"`
    
    **API Key bekommen:** https://creativecommons.tankerkoenig.de/
    """)
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
                
                # Distance to station (in km, from API)
                distance_to_station = station.get('dist', 0)  # in km
                
                all_stations.append({
                    "Preis": f"{price:.3f} €",
                    "Marke": brand,
                    "Adresse": address,
                    "Ort": station.get('place', 'N/A'),
                    "Distanz": f"{distance_to_station:.1f} km",
                    "Status": "✅" if station.get("isOpen") else "❌",
                    "raw_price": price,
                    "distance_to_station": distance_to_station,
                })
                seen_ids.add(station["id"])
        
        except Exception as e:
            continue
    
    return all_stations


# --- STREAMLIT UI ---
st.set_page_config(page_title="Sprit-Navigator Pro", page_icon="⛽", layout="wide")
st.title("⛽ Sprit-Navigator Pro")
st.markdown("Finde die günstigsten Tankstellen entlang deiner Fahrtstrecke.")

# Sidebar
with st.sidebar:
    st.header("⚙️ Einstellungen")

# Input form
col1, col2 = st.columns(2)
with col1:
    start_city = st.text_input("🚀 Startpunkt", value="Barver", placeholder="z.B. Barver")
with col2:
    end_city = st.text_input("🎯 Zielort", value="Bad Bentheim", placeholder="z.B. Bad Bentheim")

col1, col2 = st.columns(2)
with col1:
    via_city = st.text_input("📍 Via (optional)", value="", placeholder="z.B. Osnabrück (optional)")
with col2:
    fuel_type = st.selectbox("⛽ Kraftstoff", ["e5", "e10", "diesel"])

col1, col2 = st.columns(2)
with col1:
    radius = st.slider("🔍 Such-Radius (km)", 1, 15, 5)
with col2:
    pass  # Layout balance

# Main action button
if st.button("🔍 Günstigste Tankstellen finden", use_container_width=True):
    st.session_state.search_done = True
    st.session_state.start_city = start_city
    st.session_state.end_city = end_city
    st.session_state.via_city = via_city
    st.session_state.fuel_type = fuel_type
    st.session_state.radius = radius

# Process search if button was clicked
if st.session_state.get("search_done"):
    start_city = st.session_state.start_city
    end_city = st.session_state.end_city
    via_city = st.session_state.via_city
    fuel_type = st.session_state.fuel_type
    radius = st.session_state.radius
    
    with st.spinner("📍 Orte lokalisieren..."):
        s_coords = get_coords(start_city)
        import time
        time.sleep(1)  # 1 Sekunde Pause gegen Rate-Limit
        e_coords = get_coords(end_city)
        via_coords = None
        if via_city:
            time.sleep(1)  # Nochmal Pause
            via_coords = get_coords(via_city)
    
    if not s_coords or not e_coords:
        st.error("❌ Einer oder beide Orte konnten nicht gefunden werden.")
        st.stop()
    
    if via_city and not via_coords:
        st.error(f"❌ Via-Ort '{via_city}' konnte nicht gefunden werden.")
        st.stop()
    
    with st.spinner("🛣️ Routen berechnen..."):
        if via_coords:
            # Calculate route: start -> via -> end
            coords1, dist1 = get_route(s_coords, via_coords)
            coords2, dist2 = get_route(via_coords, e_coords)
            
            if not coords1 or not coords2 or not dist1 or not dist2:
                st.error("❌ Routenberechnung mit Via-Punkt fehlgeschlagen.")
                st.stop()
            
            # Combine coordinates (remove last point of first route to avoid duplicate)
            coords = coords1[:-1] + coords2
            dist = dist1 + dist2
            
            route_info = f"**{start_city} → {via_city} → {end_city}**"
        else:
            # Direct route
            coords, dist = get_route(s_coords, e_coords)
            
            if not coords or not dist:
                st.error("❌ Routenberechnung fehlgeschlagen.")
                st.stop()
            
            route_info = f"**{start_city} → {end_city}**"
    
    dist_km = dist / 1000
    st.success(f"✅ Route: {route_info} — **{dist_km:.1f} km**")
    
    # Calculate waypoints (every ~15km)
    target_waypoints = max(3, int(dist_km / 15))  # mindestens 3 Wegpunkte
    step_size = max(1, len(coords) // target_waypoints)
    waypoints = coords[::step_size]
    
    # Ensure start and end points are included
    if coords[0] not in waypoints:
        waypoints.insert(0, coords[0])
    if coords[-1] not in waypoints:
        waypoints.append(coords[-1])
    
    # If via_coords exists, include the via point
    if via_city and 'coords1' in locals():
        # Add the via point (end of first route segment)
        via_point = coords1[-1]
        if via_point not in waypoints:
            # Find best position to insert
            insert_pos = len(waypoints) // 2
            waypoints.insert(insert_pos, via_point)
    
    st.info(f"🔍 Durchsuche {len(waypoints)} Wegpunkte auf der Route...")
    
    with st.spinner("⛽ Suche Tankstellen..."):
        if via_city and 'coords1' in locals() and 'coords2' in locals():
            # Search both route segments separately
            st.info("🔍 Suche auf Strecke 1: Start → Via...")
            waypoints1 = coords1[::max(1, len(coords1) // max(1, int(dist_km / 30)))]
            if coords1[-1] not in waypoints1:
                waypoints1.append(coords1[-1])
            all_stations_1 = find_stations(waypoints1, fuel_type, radius, API_KEY)
            
            st.info("🔍 Suche auf Strecke 2: Via → Ziel...")
            waypoints2 = coords2[::max(1, len(coords2) // max(1, int(dist_km / 30)))]
            if coords2[-1] not in waypoints2:
                waypoints2.append(coords2[-1])
            all_stations_2 = find_stations(waypoints2, fuel_type, radius, API_KEY)
            
            # Combine and deduplicate
            all_stations = all_stations_1
            seen_ids = {s.get('Adresse', '') for s in all_stations}
            
            for station in all_stations_2:
                if station.get('Adresse', '') not in seen_ids:
                    all_stations.append(station)
                    seen_ids.add(station.get('Adresse', ''))
        else:
            # Direct route search
            all_stations = find_stations(waypoints, fuel_type, radius, API_KEY)
    
    if all_stations:
        df = pd.DataFrame(all_stations)
        st.success(f"✅ **{len(all_stations)} Tankstellen** gefunden!")
        
        # Calculate baseline price (use 90th percentile = "Autobahn-ähnlich")
        baseline_price = df['raw_price'].quantile(0.90)
        
        # Calculate net profit and savings percentage for each station
        df['net_profit'] = df.apply(
            lambda row: (baseline_price - row['raw_price']) * 50 - (row['distance_to_station'] * 2 * 0.12),
            axis=1
        )
        
        # Calculate percentage savings
        df['savings_percent'] = (((baseline_price - df['raw_price']) / baseline_price) * 100).round(1)
        
        st.info(f"💰 **Autobahn-Referenzpreis:** €{baseline_price:.3f}/L (90. Perzentil aus der Liste)")
        
        # Store in session state for persistence
        st.session_state.df = df
        st.session_state.baseline_price = baseline_price
    else:
        st.warning(f"❌ Keine {fuel_type.upper()}-Tankstellen gefunden.")
        st.stop()

# Display sorting options and results (persistent across clicks)
if st.session_state.get("df") is not None:
    df = st.session_state.df
    baseline_price = st.session_state.baseline_price
    fuel_type = st.session_state.fuel_type
    
    # Sorting options - use session state to persist selection
    st.markdown("---")
    st.subheader("📊 Sortierung")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("💰 Bestes Angebot", use_container_width=True):
            st.session_state.sort_by = "best"
    with col2:
        if st.button("⛽ Günstigster Preis", use_container_width=True):
            st.session_state.sort_by = "price"
    with col3:
        if st.button("🚗 Kürzeste Distanz", use_container_width=True):
            st.session_state.sort_by = "distance"
    
    # Default sorting
    if "sort_by" not in st.session_state:
        st.session_state.sort_by = "best"
    
    # Apply sorting
    if st.session_state.sort_by == "best":
        df_sorted = df.sort_values("net_profit", ascending=False)
        st.caption("💡 Sortiert nach: Preis UND Distanz kombiniert (höchster Profit)")
    elif st.session_state.sort_by == "price":
        df_sorted = df.sort_values("raw_price", ascending=True)
        st.caption("💡 Sortiert nach: Reiner Spritpreis (ohne Distanz)")
    else:  # distance
        df_sorted = df.sort_values("distance_to_station", ascending=True)
        st.caption("💡 Sortiert nach: Distanz zur Route")
    
    # Display stations with Google Maps links (TOP 5 ONLY)
    st.subheader(f"📋 Top 5 {fuel_type.upper()}-Tankstellen")
    
    # Create dataframe for top 5
    display_df = df_sorted.head(5).reset_index(drop=True)
    
    # Display each station with Google Maps button
    for idx, (i, row) in enumerate(display_df.iterrows(), 1):
        col1, col2, col3, col4, col5 = st.columns([1, 1.5, 1.5, 1.5, 0.8])
        
        with col1:
            st.metric("Preis", row['Preis'], label_visibility="collapsed")
        with col2:
            st.write(f"**{row['Marke']}**")
        with col3:
            st.write(f"📍 {row['Distanz']}")  # Distanz zur Station
        with col4:
            st.write(f"{row['Ort']}")
        with col5:
            # Google Maps Link - Real Streamlit Button
            maps_url = f"https://www.google.com/maps/search/{row['Adresse']}+{row['Ort']}"
            st.link_button("🗺️", maps_url)
        
        st.write(f"*{row['Adresse']}*")
        st.write(f"{row['Status']}")
        st.divider()
    
    st.markdown("---")
    st.subheader("📈 Gewinn-Analyse (für 50L Tank)")
    st.caption(f"**Berechnung:** (€{baseline_price:.3f}/L - Stationspreis) × 50L - Detourkosten (€0,12/km hin+zurück)")
    
    # Show top 3 recommendations with profit and savings %
    col1, col2, col3 = st.columns(3)
    
    for idx, (i, row) in enumerate(df_sorted.head(3).iterrows()):
        with [col1, col2, col3][idx]:
            profit = row['net_profit']
            savings_pct = row['savings_percent']
            color = "🟢" if profit > 5 else "🟡" if profit > 0 else "🔴"
            st.metric(
                f"{color} #{idx+1}: {row['Marke']}",
                f"{row['Preis']}",
                f"{profit:+.2f}€ ({savings_pct:.1f}%)"
            )
            st.caption(f"📍 {row['Distanz']}\n{row['Ort']}\n{row['Status']}")
