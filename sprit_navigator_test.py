import streamlit as st
import requests
import urllib3
import pandas as pd
import os
from pathlib import Path
from geopy.geocoders import Nominatim

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
def get_distance_osrm(station_lat, station_lng, route_lat, route_lng):
    """Get distance between station and route point using OSRM."""
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{station_lng},{station_lat};{route_lng},{route_lat}"
        r = requests.get(url, verify=False, timeout=5)
        data = r.json()
        if data.get('code') == 'Ok' and data.get('routes'):
            return data['routes'][0].get('distance', 0) / 1000  # Convert to km
    except:
        pass
    return 0


@st.cache_data(ttl=600)
def get_coords(city):
    """Get coordinates for a German city via Geopy (fallback to Google)."""
    if not city or not city.strip():
        return None
    
    try:
        # Try with geopy (uses multiple APIs including OSM, cached)
        from geopy.geocoders import GoogleV3, Nominatim as GeopifyNominatim
        
        # Use geopy with no rate limit as it's cached
        geolocator = GeopifyNominatim(user_agent="spritsparer_2026")
        location = geolocator.geocode(f"{city}, Germany")
        
        if location:
            return float(location.latitude), float(location.longitude)
    except:
        pass
    
    # Fallback: Manual coordinates for common German cities
    common_cities = {
        # Großstädte
        "berlin": (52.5200, 13.4050),
        "münchen": (48.1351, 11.5820),
        "hamburg": (53.5511, 9.9937),
        "köln": (50.9375, 6.9603),
        "frankfurt": (50.1109, 8.6821),
        "stuttgart": (48.7758, 9.1829),
        "düsseldorf": (51.2277, 6.7735),
        "dortmund": (51.5136, 7.4653),
        "essen": (51.4556, 7.0116),
        "leipzig": (51.3397, 12.3731),
        "dresden": (51.0504, 13.7373),
        "hannover": (52.3759, 9.7320),
        "nürnberg": (49.4521, 11.0767),
        "duisburg": (51.4344, 6.7073),
        "bochum": (51.4818, 7.2254),
        "wuppertal": (51.2629, 7.1577),
        "bielefeld": (52.0116, 8.5355),
        "bonn": (50.7353, 7.0992),
        "münster": (51.9625, 7.6251),
        "karlsruhe": (49.0069, 8.4037),
        "mannheim": (49.4891, 8.4673),
        "augsburg": (48.3705, 10.8945),
        "wiesbaden": (50.0829, 8.2430),
        "gelsenkirchen": (51.4556, 7.0916),
        "mönchengladbach": (51.1642, 6.4115),
        "braunschweig": (52.2688, 10.5267),
        "chemnitz": (50.8365, 12.9168),
        "kiel": (54.3233, 10.1348),
        "aachen": (50.7753, 6.0838),
        "osnabrück": (52.2799, 8.0532),
        "rostock": (54.0887, 12.0960),
        "erfurt": (50.9856, 11.0296),
        "mainz": (50.0012, 8.2765),
        "ludwigshafen": (49.4778, 8.4427),
        "würzburg": (49.7927, 9.9516),
        "freiburg": (48.0021, 7.8524),
        "ulm": (48.3985, 9.9947),
        "heilbronn": (49.1383, 9.2200),
        "bamberg": (49.8905, 10.8867),
        "bayreuth": (49.9479, 11.5791),
        # Mittlere Städte
        "diepholz": (52.6089, 8.3986),
        "barver": (52.2500, 8.6667),
        "bad bentheim": (52.3003, 7.0997),
        "steinfeld": (52.3500, 8.1500),
        "bremen": (53.0795, 8.8017),
        "oldenburg": (53.1437, 8.2226),
        "vechta": (52.5664, 8.2878),
        "wildeshausen": (52.7564, 8.4239),
        "hagen": (51.3552, 7.4688),
        "solingen": (51.1787, 7.0866),
        "remscheid": (51.1849, 7.1986),
        "castrop-rauxel": (51.5167, 7.3167),
        "bottrop": (51.5236, 7.1139),
        "oberhausen": (51.4629, 6.8518),
        "recklinghausen": (51.6158, 7.2050),
        "neukirchen-vluyn": (51.4428, 6.7436),
        "moers": (51.4514, 6.6275),
        "krefeld": (51.3389, 6.5596),
        "viersen": (51.2544, 6.3883),
        "wilnsdorf": (50.9967, 8.1500),
        "siegen": (50.8773, 8.0289),
        "herborn": (50.7419, 8.3244),
        "dillenburg": (50.7331, 8.2806),
        "haiger": (50.7453, 8.4122),
        "lahn": (50.7053, 8.3306),
        "gießen": (50.5836, 8.6751),
        "wetzlar": (50.5641, 8.5035),
        "marburg": (50.8050, 8.7744),
        "bad marienberg": (50.4378, 8.1289),
        "limburg": (50.3861, 8.0693),
        "weilburg": (50.4753, 8.2578),
        "bad homburg": (50.2288, 8.6183),
        "bad nauheim": (50.3675, 8.7583),
        "friedberg": (50.3333, 8.7500),
        "bad orb": (50.1247, 9.2975),
        "hanau": (50.1214, 8.9153),
        "offenbach": (50.1047, 8.7764),
        "darmstadt": (49.8728, 8.6512),
        "groß-umstadt": (49.8867, 8.9344),
        "erbach": (49.7028, 8.9653),
        "michelstadt": (49.7053, 8.9736),
        "höchst": (50.1778, 8.7500),
        "aschaffenburg": (49.9750, 9.1476),
        "bad kissingen": (50.1981, 9.9853),
        "bad neustadt": (50.3253, 9.8914),
        "schmalkalden": (50.7186, 10.4639),
        "hildburghausen": (50.4128, 10.7261),
        "sonneberg": (50.3631, 10.9950),
        "coburg": (50.2625, 10.9626),
        "lichtenfels": (50.1408, 11.0958),
        "kulmbach": (50.1036, 11.4414),
        "bad staffelstein": (50.0753, 11.2631),
        "rothenburg ob tauber": (49.3809, 10.1767),
        "crailsheim": (49.1389, 10.0778),
        "schwäbisch hall": (49.1075, 9.7389),
        "künzelsau": (49.2583, 9.6667),
        "öhringen": (49.1917, 9.4889),
        "weinsberg": (49.1806, 9.4306),
        "neckarsulm": (49.1892, 9.2214),
        "lauffen": (49.0519, 9.1764),
        "heilbronn": (49.1383, 9.2200),
        "mosbach": (49.3606, 9.1639),
        "buchen": (49.5119, 9.2581),
        "wertheim": (49.7567, 9.5403),
        "tauberbischofsheim": (49.6447, 9.6425),
        "bad mergentheim": (49.4931, 9.7661),
        "weikersheim": (49.3156, 9.8169),
        "creglingen": (49.4019, 10.0081),
    }
    
    city_lower = city.lower().strip()
    if city_lower in common_cities:
        return common_cities[city_lower]
    
    st.error(f"❌ Stadt '{city}' konnte nicht gefunden werden. Bitte eine größere Stadt eingeben.")
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
                
                # Distance from API (in km)
                distance_to_station = station.get('dist', 0)
                
                all_stations.append({
                    "Preis": f"{price:.3f} €",
                    "Marke": brand,
                    "Adresse": address,
                    "Ort": station.get('place', 'N/A'),
                    "Distanz": f"{distance_to_station:.1f} km",
                    "Status": "✅" if station.get("isOpen") else "❌",
                    "raw_price": price,
                    "distance_to_station": distance_to_station,
                    "lat": float(station.get('lat', 0)),
                    "lng": float(station.get('lng', 0)),
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
        time.sleep(5)  # 5 Sekunden Pause gegen Rate-Limit
        e_coords = get_coords(end_city)
        via_coords = None
        if via_city:
            time.sleep(5)  # Nochmal Pause
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
        # Calculate real distance using OSRM for this station to first route point
        if 'coords' in locals() and coords:
            real_distance = get_distance_osrm(row['lat'], row['lng'], coords[0][1], coords[0][0])
            distance_text = f"📍 {real_distance:.1f} km" if real_distance > 0 else f"📍 {row['Distanz']}"
        else:
            distance_text = f"📍 {row['Distanz']}"
        
        col1, col2, col3, col4, col5 = st.columns([1, 1.5, 1.5, 1.5, 0.8])
        
        with col1:
            st.metric("Preis", row['Preis'], label_visibility="collapsed")
        with col2:
            st.write(f"**{row['Marke']}**")
        with col3:
            st.write(distance_text)
        with col4:
            st.write(f"{row['Ort']}")
        with col5:
            # Google Maps Link - with real Google Maps icon
            maps_url = f"https://www.google.com/maps/search/{row['Adresse']}+{row['Ort']}"
            st.link_button("📍", maps_url, help="In Google Maps öffnen")
        
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
