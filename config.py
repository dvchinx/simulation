import numpy as np

GRID_WIDTH = 200
GRID_HEIGHT = 200
FPS = 4                            # ticks por segundo por defecto (SIM_FPS lo sobrescribe)

# --- Herbívoro A (presa verde) ---
INITIAL_POPULATION = 450
INITIAL_ENERGY = 30
MOVE_ENERGY_COST = 2
MAX_ENERGY = 255                   # tope de energía de los herbívoros
FOOD_ENERGY_GAIN = 20
MAX_AGE = 150

# --- Herbívoro B (competidor azul) ---
HERBIVORE_B_POPULATION = 450
HERBIVORE_B_INITIAL_ENERGY = 30
# Nicho distinto al herbívoro A: mejor eficiencia de pasto en biomas duros (ártico/desierto),
# peor en templado/tropical — evita exclusión competitiva total entre ambos herbívoros.
# [templado, ártico, desierto, tropical]
HERBIVORE_B_BIOME_MULT = np.array([0.6, 1.8, 1.8, 0.6], dtype=np.float32)

# --- Depredador (rojo) ---
PREDATOR_POPULATION = 60           # mayor inicial para soportar reproducción sexual
PREDATOR_INITIAL_ENERGY = 50
PREDATOR_MOVE_COST = 2             # igual al herbívoro — sobrevive mejor en escasez
PREDATOR_MAX_ENERGY = 200          # holgura sobre el umbral reproductivo (+ penalización por temperatura)
PREDATOR_ENERGY_FROM_PREY = 40     # menor ganancia por presa: evita que el depredador arrase a los herbívoros
PREDATOR_MAX_AGE = 120             # más tiempo para sobrevivir períodos de escasez

# --- Omnívoro (morado) ---
OMNI_POPULATION       = 80
OMNI_INITIAL_ENERGY   = 40
OMNI_MOVE_COST        = 2
OMNI_MAX_ENERGY       = 140
OMNI_ENERGY_FROM_PREY = 30    # menor que el depredador
OMNI_FOOD_EFFICIENCY  = 0.25  # menor eficiencia de pasto: evita que domine sobre las demás especies
OMNI_MAX_AGE          = 130

# --- Pasto ---
INITIAL_FOOD_DENSITY = 0.4
FOOD_REGEN_RATE = 0.03             # más rápido → presas se recuperan antes

# --- Infección ---
INFECTION_START_COUNT = 20
INFECTION_ENERGY_DRAIN = 3         # menos agresiva → huéspedes viven más y contagian más
INFECTION_SPREAD_PROB = 0.20       # más contagiosa
INFECTION_CLEAR_PROB = 0.01        # recuperación más lenta → endémica

# --- Reproducción ---
MATE_SEARCH_RADIUS = 3   # radio (celdas) para detectar pareja, no solo adyacencia directa
# Las especies escasas (depredador, omnívoro) rastrean pareja desde más lejos;
# sin esto casi nunca coinciden dos individuos fértiles (efecto Allee) y se extinguen.
MATE_SEARCH_RADIUS_BY_SPECIES = {1: MATE_SEARCH_RADIUS, 2: 8, 3: MATE_SEARCH_RADIUS, 4: 12}

# --- Migración (efecto rescate) ---
# Si una especie lleva MIGRATION_DELAY ticks extinta, llega un grupo fundador
# desde fuera del mapa. Mantiene viva la demo y reproduce dinámicas de metapoblación.
MIGRATION_DELAY  = 120
MIGRATION_GROUP  = {1: 80, 2: 16, 3: 80, 4: 16}
MIGRATION_RADIUS = 8

# --- Genoma (Fase 3) ---
N_GENES = 5
GENE_SPEED           = 0  # probabilidad de moverse por tick [0.1, 1.0]
GENE_REPRO_ENERGY    = 1  # energía mínima para reproducirse [40, 220]
GENE_FOOD_EFFICIENCY = 2  # multiplicador en energía obtenida de alimento [0.2, 3.0]
GENE_VISION          = 3  # rango de visión en celdas [1, 12]
GENE_MUTATION_RATE   = 4  # desviación estándar del ruido de mutación [0.001, 0.4]

GENOME_MIN = np.array([0.1,  40.0, 0.2,  1.0, 0.001], dtype=np.float32)
GENOME_MAX = np.array([1.0, 220.0, 3.0, 12.0, 0.400], dtype=np.float32)

# (speed, repro_energy, food_efficiency, vision, mutation_rate)
GENOME_HERBIVORE    = np.array([0.9, 100.0, 1.0, 2.0, 0.05], dtype=np.float32)
GENOME_PREDATOR     = np.array([1.0, 115.0, 1.0, 4.0, 0.05], dtype=np.float32)
GENOME_OMNIVORE     = np.array([0.8,  90.0, 0.6, 3.0, 0.05], dtype=np.float32)
GENOME_INIT_NOISE   = np.array([0.08,  12.0, 0.10, 0.5, 0.015], dtype=np.float32)
GENE_NAMES = ["Velocidad", "Reprod.", "Eficiencia", "Visión", "Mutación"]

# --- Registro de especies: fuente única para simulación, servidor y cliente ---
SPECIES = {
    1: {"key": "herb_a",   "name": "Herbívoro A", "initial_energy": INITIAL_ENERGY,
        "max_energy": MAX_ENERGY,          "max_age": MAX_AGE,          "genome": GENOME_HERBIVORE},
    2: {"key": "predator", "name": "Depredador",  "initial_energy": PREDATOR_INITIAL_ENERGY,
        "max_energy": PREDATOR_MAX_ENERGY, "max_age": PREDATOR_MAX_AGE, "genome": GENOME_PREDATOR},
    3: {"key": "herb_b",   "name": "Herbívoro B", "initial_energy": HERBIVORE_B_INITIAL_ENERGY,
        "max_energy": MAX_ENERGY,          "max_age": MAX_AGE,          "genome": GENOME_HERBIVORE},
    4: {"key": "omnivore", "name": "Omnívoro",    "initial_energy": OMNI_INITIAL_ENERGY,
        "max_energy": OMNI_MAX_ENERGY,     "max_age": OMNI_MAX_AGE,     "genome": GENOME_OMNIVORE},
}

SPECIES_COLORS = {
    0:  [20,  20,  20 ],  # vacío
    1:  [0,   200, 100],  # herbívoro A (verde)
    2:  [220, 60,  60 ],  # depredador (rojo)
    3:  [60,  140, 220],  # herbívoro B (azul)
    4:  [160, 60,  200],  # omnívoro (morado)
    5:  [200, 200, 0  ],  # herbívoro A infectado (amarillo)
    6:  [200, 120, 0  ],  # herbívoro B infectado (naranja)
    7:  [120, 40,  160],  # omnívoro infectado (morado oscuro)
    10: [30,  80,  30 ],  # pasto
    # --- Fase 4: feromonas (rastros en celdas vacías) ---
    11: [0,   85,  42 ],  # feromona herbívoro A (verde tenue)
    12: [105, 25,  25 ],  # feromona depredador (rojo tenue)
    13: [25,  58,  115],  # feromona herbívoro B (azul tenue)
    # --- Fase 4: territorio (marca persistente debajo de feromonas) ---
    20: [0,   48,  24 ],  # territorio herbívoro A (verde muy tenue)
    21: [58,  14,  14 ],  # territorio depredador (rojo muy tenue)
    22: [14,  32,  68 ],  # territorio herbívoro B (azul muy tenue)
    # --- Fase 5: terreno ---
    30: [20,  60,  140],  # agua
    31: [70,  70,  70 ],  # roca
    32: [35,  55,  35 ],  # pantano
    # --- Fase 5: perturbaciones ---
    40: [220, 80,  10 ],  # fuego
    41: [30,  60,  180],  # inundación
    # --- Fase 5: contorno y heatmap de bioma ---
    50: [100, 90,  85 ],  # contorno de bioma
    60: [80,  160, 100],  # bioma templado
    61: [60,  80,  180],  # bioma ártico
    62: [180, 130, 40 ],  # bioma desierto
    63: [30,  180, 80 ],  # bioma tropical
}

# --- Fase 4: Feromonas ---
PHEROMONE_DEPOSIT          = 0.30   # concentración añadida por organismo por tick
PHEROMONE_DECAY            = 0.85   # fracción que permanece tras cada tick
PHEROMONE_DIFFUSION        = 0.08   # fracción que se difunde a cada vecino cardinal
PHEROMONE_HERB_ATTRACTION  = 0.50   # peso en dir_scores para herbívoros (propio rastro)
PHEROMONE_PRED_ATTRACTION  = 0.70   # depredadores rastrean feromona combinada de presas
PHEROMONE_RENDER_THRESHOLD = 0.06   # umbral mínimo para pintar rastro en canvas

# --- Fase 4: Cardumen / Bandada (Flocking) ---
FLOCK_RADIUS            = 6    # radio de cohesión en celdas
FLOCK_COHESION_WEIGHT   = 0.25 # atracción hacia el centro de masa del cardumen
FLOCK_SEPARATION_RADIUS = 2    # radio de separación (evitar apiñamiento)
FLOCK_SEPARATION_WEIGHT = 0.60 # repulsión de congéneres demasiado cercanos

# --- Fase 4: Territorio ---
TERRITORY_DEPOSIT           = 0.06  # marca territorial depositada por tick
TERRITORY_DECAY             = 0.995 # decaimiento lento → territorio persistente
TERRITORY_ATTRACTION        = 0.15  # peso en dir_scores para moverse hacia propio territorio
TERRITORY_FEAR_WEIGHT       = 0.30  # herbívoros huyen del territorio del depredador
TERRITORY_RENDER_THRESHOLD  = 0.12  # umbral para pintar territorio en canvas

# --- Fase 5: Temperatura / Estaciones ---
SEASON_PERIOD        = 400     # ticks por ciclo completo (4 estaciones)
SEASON_AMPLITUDE     = 0.85    # temperatura pico (rango -0.85 a +0.85)
TEMP_SPEED_FACTOR    = 0.40    # penalización de velocidad en extremos
TEMP_REPRO_PENALTY   = 30.0    # energía extra requerida para reproducirse en extremos
TEMP_REGEN_FACTOR    = 0.65    # reducción de regen de pasto en extremos

# Offsets de temperatura por bioma: [templado, ártico, desierto, tropical]
BIOME_TEMP_OFFSET = np.array([0.0, -0.50,  0.50, 0.20], dtype=np.float32)
# Multiplicadores de regen de pasto por bioma
BIOME_REGEN_MULT  = np.array([1.0,  0.40,  0.30, 1.80], dtype=np.float32)

# --- Fase 5: Terreno ---
TERRAIN_SMOOTH_ITER = 25    # iteraciones de suavizado para patches de terreno
BIOME_SMOOTH_ITER   = 40    # mayor escala para patches de bioma
WATER_THRESHOLD     = 0.18  # valor de ruido por debajo del cual hay agua
ROCK_THRESHOLD      = 0.80  # valor de ruido por encima del cual hay roca
SWAMP_MIN           = 0.65  # rango de pantano
SWAMP_MAX           = 0.80
TERRAIN_WATER_COST  = 1.6   # multiplicador de costo metabólico en agua
TERRAIN_SWAMP_COST  = 1.3   # multiplicador de costo metabólico en pantano

# --- Fase 5: Difusión de nutrientes ---
NUTRIENT_DEPOSIT     = 0.40   # depósito de nutriente por celda de pasto por tick
NUTRIENT_DIFFUSION   = 0.05   # fracción difundida a vecinos cardinales (D <= 0.25)
NUTRIENT_DECAY       = 0.92   # fracción que permanece tras cada tick
NUTRIENT_REGEN_BOOST = 0.04   # probabilidad extra de regen donde hay nutriente alto
NUTRIENT_CHEMOTAXIS  = 0.12   # peso en dir_scores por gradiente de nutriente

# --- Fase 5: Perturbaciones ---
FIRE_PERIOD  = 500    # ticks entre eventos de fuego
FIRE_RADIUS  = 12     # radio del incendio en celdas
FIRE_DECAY   = 0.95   # decaimiento visual por tick
FLOOD_PERIOD = 750    # ticks entre inundaciones
FLOOD_WIDTH  = 10     # semiancho de la franja de inundación
FLOOD_DECAY  = 0.93   # decaimiento visual por tick
DISTURBANCE_THRESHOLD = 0.08  # umbral mínimo para pintar perturbación en canvas
