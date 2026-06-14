import numpy as np

GRID_WIDTH = 200
GRID_HEIGHT = 200
FPS = 1

# --- Herbívoro A (presa verde) ---
INITIAL_POPULATION = 300
INITIAL_ENERGY = 30
MOVE_ENERGY_COST = 2
MAX_ENERGY = 100
FOOD_ENERGY_GAIN = 20
MAX_AGE = 150

# --- Herbívoro B (competidor azul) ---
HERBIVORE_B_POPULATION = 300
HERBIVORE_B_INITIAL_ENERGY = 30

# --- Depredador (rojo) ---
PREDATOR_POPULATION = 25           # menos presión inicial
PREDATOR_INITIAL_ENERGY = 50
PREDATOR_MOVE_COST = 2             # igual al herbívoro — sobrevive mejor en escasez
PREDATOR_MAX_ENERGY = 120
PREDATOR_REPRODUCE_ENERGY = 115    # requiere 2 cazas seguidas, no 1
PREDATOR_ENERGY_FROM_PREY = 60
PREDATOR_MAX_AGE = 120             # más tiempo para sobrevivir períodos de escasez
PREDATOR_VISION_RANGE = 4          # radio menor → refugio espacial para las presas

# --- Pasto ---
INITIAL_FOOD_DENSITY = 0.4
FOOD_REGEN_RATE = 0.03             # más rápido → presas se recuperan antes

# --- Infección ---
INFECTION_START_COUNT = 20
INFECTION_ENERGY_DRAIN = 3         # menos agresiva → huéspedes viven más y contagian más
INFECTION_SPREAD_PROB = 0.20       # más contagiosa
INFECTION_CLEAR_PROB = 0.01        # recuperación más lenta → endémica

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
GENOME_INIT_NOISE   = np.array([0.08,  12.0, 0.10, 0.5, 0.015], dtype=np.float32)

SPECIES_COLORS = {
    0:  [20,  20,  20 ],  # vacío
    1:  [0,   200, 100],  # herbívoro A (verde)
    2:  [220, 60,  60 ],  # depredador (rojo)
    3:  [60,  140, 220],  # herbívoro B (azul)
    5:  [200, 200, 0  ],  # herbívoro A infectado (amarillo)
    6:  [200, 120, 0  ],  # herbívoro B infectado (naranja)
    10: [30,  80,  30 ],  # pasto
    # --- Fase 4: feromonas (rastros en celdas vacías) ---
    11: [0,   85,  42 ],  # feromona herbívoro A (verde tenue)
    12: [105, 25,  25 ],  # feromona depredador (rojo tenue)
    13: [25,  58,  115],  # feromona herbívoro B (azul tenue)
    # --- Fase 4: territorio (marca persistente debajo de feromonas) ---
    20: [0,   48,  24 ],  # territorio herbívoro A (verde muy tenue)
    21: [58,  14,  14 ],  # territorio depredador (rojo muy tenue)
    22: [14,  32,  68 ],  # territorio herbívoro B (azul muy tenue)
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
