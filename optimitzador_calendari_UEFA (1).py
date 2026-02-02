"""
Optimitzador de Calendari de la UEFA Champions League

Aquest programa llegeix dades d'equips des d'un fitxer Excel i optimitza
el calendari de partits per minimitzar la distància total recorreguda,
respectant les restriccions del format de la competició.
"""

import pandas as pd
import pulp
from math import radians, sin, cos, sqrt, atan2


# ============================================================================
# LECTURA DE DADES
# ============================================================================

def llegir_dades_excel(ruta_arxiu):
    """
    Llegeix les dades dels equips des d'un fitxer Excel.
    
    Args:
        ruta_arxiu: Ruta al fitxer Excel amb les dades dels equips
        
    Returns:
        Diccionari amb índex d'equip com a clau i informació de l'equip com a valor
    """
    df = pd.read_excel(ruta_arxiu)
    
    # Mapatge de codi numèric a codi de país
    paisos_map = {
        1: 'ESP', 2: 'GER', 3: 'ENG', 4: 'FRA', 5: 'ITA', 6: 'POR',
        7: 'BEL', 8: 'NED', 9: 'GRE', 10: 'CZE', 11: 'NOR', 12: 'DEN',
        13: 'TUR', 14: 'AZE', 15: 'CYP', 16: 'KAZ'
    }
    
    equips = {}
    for idx, fila in df.iterrows():
        pais_num = int(fila['País'])
        
        # Conversió de coordenades (dividir per 1,000,000)
        lat = fila['Latitud (°N)'] / 1000000.0
        lon = fila['Longitud (°E)'] / 1000000.0
        
        equips[idx] = {
            'nom': fila['Equip'],
            'estadi': fila['Estadi'],
            'lat': lat,
            'lon': lon,
            'pais': paisos_map[pais_num],
            'pot': int(fila['Pot'])
        }
    
    return equips


# ============================================================================
# CÀLCUL DE DISTÀNCIES
# ============================================================================

def calcular_distancia_haversine(lat1, lon1, lat2, lon2):
    """
    Calcula la distància entre dos punts geogràfics utilitzant la fórmula de Haversine.
    
    Args:
        lat1, lon1: Latitud i longitud del primer punt (en graus decimals)
        lat2, lon2: Latitud i longitud del segon punt (en graus decimals)
        
    Returns:
        Distància en quilòmetres
    """
    R = 6371.0  # Radi de la Terra en km
    
    # Conversió a radians
    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)
    
    # Diferències
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    
    # Fórmula de Haversine
    a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    return R * c


def crear_matriu_distancies(equips):
    """
    Crea una matriu N×N amb les distàncies entre tots els equips.
    
    Args:
        equips: Diccionari amb la informació dels equips
        
    Returns:
        Matriu (llista de llistes) amb les distàncies en km
    """
    N = len(equips)
    distancies = [[0.0] * N for _ in range(N)]
    
    for i in range(N):
        for j in range(N):
            if i != j:
                lat1, lon1 = equips[i]['lat'], equips[i]['lon']
                lat2, lon2 = equips[j]['lat'], equips[j]['lon']
                distancies[i][j] = calcular_distancia_haversine(lat1, lon1, lat2, lon2)
    
    return distancies


# ============================================================================
# OPTIMITZACIÓ
# ============================================================================

def optimitzar_lliga_champions(equips, dists):
    """
    Optimitza el calendari de la Champions League per minimitzar les distàncies totals.
    
    Restriccions aplicades:
    - Cada equip juga 8 partits (4 local, 4 visitant)
    - Màxim 1 partit entre cada parella d'equips
    - No es poden enfrontar equips del mateix país
    - Màxim 2 partits contra equips d'un mateix país estranger
    - 1 partit local i 1 visitant contra cada pot
    
    Args:
        equips: Diccionari amb la informació dels equips
        dists: Matriu de distàncies entre equips
        
    Returns:
        Tupla (model, variables) amb el model resolt i les variables de decisió
    """
    # Paràmetres del problema
    TOTAL_PARTITS = 8
    MAX_RIVAL_MATEIX_PAIS = 2
    PARTITS_PER_POT = 1
    
    # Crear model d'optimització
    model = pulp.LpProblem("UEFA_Champions_League_Optimization", pulp.LpMinimize)
    
    N = len(equips)
    
    # Precalcular agrupacions per a restriccions
    equips_per_pot = {1: [], 2: [], 3: [], 4: []}
    equips_per_pais = {}
    
    for i in range(N):
        pot = equips[i]['pot']
        pais = equips[i]['pais']
        
        equips_per_pot[pot].append(i)
        equips_per_pais.setdefault(pais, []).append(i)
    
    # Variables de decisió: x[(i,j)] = 1 si l'equip i visita l'equip j
    x = pulp.LpVariable.dicts("partit", 
                             [(i, j) for i in range(N) for j in range(N)],
                             cat='Binary')
    
    # Funció objectiu: minimitzar distància total
    model += pulp.lpSum(dists[i][j] * x[(i, j)] for i in range(N) for j in range(N))
    
    # --- RESTRICCIONS ---
    
    # 1. Cada equip juga 4 partits com a local i 4 com a visitant
    for i in range(N):
        model += pulp.lpSum(x[(i, j)] for j in range(N)) == TOTAL_PARTITS // 2
        model += pulp.lpSum(x[(j, i)] for j in range(N)) == TOTAL_PARTITS // 2
    
    # 2. Màxim 1 partit entre cada parella d'equips
    for i in range(N):
        for j in range(N):
            if i != j:
                model += x[(i, j)] + x[(j, i)] <= 1
    
    # 3. No partits entre equips del mateix país
    for i in range(N):
        for j in range(N):
            if i != j and equips[i]['pais'] == equips[j]['pais']:
                model += x[(i, j)] == 0
    
    # 4. Màxim 2 partits contra equips del mateix país estranger
    for i in range(N):
        pais_i = equips[i]['pais']
        for pais_j, equips_pais_j in equips_per_pais.items():
            if pais_j != pais_i:
                equips_del_pais = [j for j in equips_pais_j if j != i]
                model += (pulp.lpSum(x[(i, j)] for j in equips_del_pais) + 
                         pulp.lpSum(x[(j, i)] for j in equips_del_pais)) <= MAX_RIVAL_MATEIX_PAIS
    
    # 5. 1 partit local i 1 visitant contra cada pot
    for i in range(N):
        for pot_objectiu in [1, 2, 3, 4]:
            equips_del_pot = [j for j in equips_per_pot[pot_objectiu] if j != i]
            model += pulp.lpSum(x[(i, j)] for j in equips_del_pot) == PARTITS_PER_POT
            model += pulp.lpSum(x[(j, i)] for j in equips_del_pot) == PARTITS_PER_POT
    
    # Resoldre el model (màxim 5 minuts)
    model.solve(pulp.PULP_CBC_CMD(timeLimit=300, msg=0))
    
    if model.status == pulp.LpStatusOptimal:
        print(f"Distància total mínima: {pulp.value(model.objective):.2f} km")
    
    return model, x


# ============================================================================
# PROCESSAMENT DE RESULTATS
# ============================================================================

def convertir_variables_a_matriu(x, N=36):
    """
    Converteix les variables de PuLP en una matriu N×N.
    
    Args:
        x: Variables de decisió de PuLP
        N: Nombre d'equips
        
    Returns:
        Matriu N×N amb 1 si hi ha partit, 0 altrament
    """
    matriu = [[0 for _ in range(N)] for _ in range(N)]
    
    for i in range(N):
        for j in range(N):
            matriu[i][j] = int(pulp.value(x[(i, j)]))
    
    return matriu


def mostrar_rivals_taula(matriu, equips):
    """
    Mostra els rivals de cada equip en format de taula.
    
    Args:
        matriu: Matriu de partits
        equips: Diccionari amb la informació dels equips
    """
    N = len(equips)
    
    print("Equip\tCom a visitant\tCom a local")
    print("-" * 120)
    
    for i in range(N):
        # Rivals quan l'equip i és visitant
        rivals_visitant = [equips[j]['nom'] for j in range(N) if matriu[i][j] == 1]
        
        # Rivals quan l'equip i és local
        rivals_local = [equips[j]['nom'] for j in range(N) if matriu[j][i] == 1]
        
        print(f"{equips[i]['nom']}\t{', '.join(rivals_visitant)}\t{', '.join(rivals_local)}")
    
    print("-" * 120)


# ============================================================================
# PROGRAMA PRINCIPAL
# ============================================================================

def main():
    """Executa el procés complet d'optimització."""
    # Llegir dades
    equips = llegir_dades_excel('DADES CHAMPIONS.xlsx')
    
    # Calcular distàncies
    dists = crear_matriu_distancies(equips)
    
    # Optimitzar
    model, variables = optimitzar_lliga_champions(equips, dists)
    
    # Convertir resultats a matriu
    matriu = convertir_variables_a_matriu(variables, len(equips))
    
    # Mostrar resultats
    mostrar_rivals_taula(matriu, equips)


if __name__ == "__main__":
    main()