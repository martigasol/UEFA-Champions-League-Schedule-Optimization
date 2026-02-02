import pandas as pd
import numpy as np
import math
import unicodedata
from pathlib import Path

# ── Fitxers ────────────────────────────────────────────────────────────────────
matches_path = Path("champions-league-2025-UTC.xlsx")
stadiums_path = Path("DADES CHAMPIONS.xlsx")

# ── Funcions per calcular distància ─────────────────────────────────────────────
def haversine_km(lat1, lon1, lat2, lon2):
    """Calcula la distància haversine en km entre dues coordenades geogràfiques"""
    rlat1, rlon1, rlat2, rlon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = math.sin(dlat/2)**2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    R = 6371.0088  # km
    return R * c

# ── Llegeix els fitxers ────────────────────────────────────────────────────────
matches = pd.read_excel(matches_path)
stadiums = pd.read_excel(stadiums_path)

# ── Normalització de noms ───────────────────────────────────────────────────────
def normalize_name(s):
    """Normalitza noms d'equips per evitar problemes amb accents o variacions"""
    if pd.isna(s):
        return None
    s = str(s).strip().casefold()
    s = "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))  # treu accents
    s = " ".join(s.split())
    return s

# ── Assignació de columnes de partits i estadis───────────────────────────────────────────
home_col = 'Home Team' 
away_col = 'Away Team'

team_col = 'Equip'  
lat_col = 'Latitud (°N)' 
lon_col = 'Longitud (°E)'  

# ── Neteja les dades d'estadis ─────────────────────────────────────────────────
stadiums_clean = stadiums[[team_col, lat_col, lon_col]].copy()
stadiums_clean.columns = ['team', 'lat', 'lon']
stadiums_clean['team_norm'] = stadiums_clean['team'].map(normalize_name)

# ── Convertir les coordenades de mil·lèsimes a graus decimals ─────────────────
stadiums_clean['lat'] = stadiums_clean['lat'] / 1000000  # Converteix latitud
stadiums_clean['lon'] = stadiums_clean['lon'] / 1000000  # Converteix longitud

# ── Crear diccionari d'estadis amb coordenades ────────────────────────────────
stadiums_dict = {row['team_norm']: (row['lat'], row['lon']) for _, row in stadiums_clean.iterrows()}

# ── Neteja les dades de partits ────────────────────────────────────────────────
matches_clean = matches[[home_col, away_col]].copy()
matches_clean.columns = ['home', 'away']
matches_clean['home_norm'] = matches_clean['home'].map(normalize_name)
matches_clean['away_norm'] = matches_clean['away'].map(normalize_name)

# ── Funció per calcular distància per partit ───────────────────────────────────
def match_distance(row):
    """Calcula la distància entre l'estadi de l'equip visitant i l'equip local"""
    home_team = row['home_norm']
    away_team = row['away_norm']
    
    if home_team is None or away_team is None:
        return np.nan
    
    # Obtenim les coordenades dels estadis
    home_coords = stadiums_dict.get(home_team)
    away_coords = stadiums_dict.get(away_team)
    
    if home_coords is None or away_coords is None: 
        return np.nan
    
    # Calcula la distància
    return haversine_km(away_coords[0], away_coords[1], home_coords[0], home_coords[1])

# ── Calcula la distància per a cada partit ─────────────────────────────────────
matches_clean['away_travel_km'] = matches_clean.apply(match_distance, axis=1)

# ── Recalcular la distància total per cada equip visitant ───────────────────────
agg = matches_clean.groupby('away_norm').agg(
    total_travel_km=('away_travel_km', 'sum'),
    n_matches=('away_travel_km', 'count')
).reset_index()

agg['total_travel_km'] = agg['total_travel_km'].round(2)
agg_sorted = agg.sort_values('total_travel_km', ascending=False).reset_index(drop=True)
print(agg_sorted)

# ── Calcular la suma total de totes les distàncies ──────────────────────────────
total_distancia_total = agg_sorted['total_travel_km'].sum()
print(f"La suma total de totes les distàncies recorregudes pels equips com a visitants és: {total_distancia_total} km")

