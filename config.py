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
HERBIVORE_B_POPULATION = 150
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
FOOD_REGEN_RATE = 0.02             # más rápido → presas se recuperan antes

# --- Infección ---
INFECTION_START_COUNT = 20
INFECTION_ENERGY_DRAIN = 3         # menos agresiva → huéspedes viven más y contagian más
INFECTION_SPREAD_PROB = 0.20       # más contagiosa
INFECTION_CLEAR_PROB = 0.01        # recuperación más lenta → endémica

SPECIES_COLORS = {
    0:  [20,  20,  20 ],  # vacío
    1:  [0,   200, 100],  # herbívoro A (verde)
    2:  [220, 60,  60 ],  # depredador (rojo)
    3:  [60,  140, 220],  # herbívoro B (azul)
    5:  [200, 200, 0  ],  # herbívoro A infectado (amarillo)
    6:  [200, 120, 0  ],  # herbívoro B infectado (naranja)
    10: [30,  80,  30 ],  # pasto
}
