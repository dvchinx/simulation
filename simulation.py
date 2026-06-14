import numpy as np
from config import (
    GRID_WIDTH, GRID_HEIGHT,
    INITIAL_POPULATION, INITIAL_ENERGY,
    HERBIVORE_B_POPULATION, HERBIVORE_B_INITIAL_ENERGY,
    PREDATOR_POPULATION, PREDATOR_INITIAL_ENERGY,
    INITIAL_FOOD_DENSITY, INFECTION_START_COUNT,
    N_GENES, GENOME_MIN, GENOME_MAX,
    GENOME_HERBIVORE, GENOME_PREDATOR, GENOME_INIT_NOISE,
    PHEROMONE_RENDER_THRESHOLD, TERRITORY_RENDER_THRESHOLD,
)
from rules import random_walk, food as food_rule, aging, reproduction
from rules import predation, infection as infection_rule
from rules import pheromones as pheromone_rule, flocking, territory as territory_rule


def create_state():
    total = GRID_WIDTH * GRID_HEIGHT
    flat = np.zeros(total, dtype=np.uint8)

    # herbívoros A
    idx_a = np.random.choice(total, INITIAL_POPULATION, replace=False)
    flat[idx_a] = 1

    # herbívoros B
    empty = np.where(flat == 0)[0]
    idx_b = np.random.choice(empty, min(HERBIVORE_B_POPULATION, len(empty)), replace=False)
    flat[idx_b] = 3

    # depredadores
    empty = np.where(flat == 0)[0]
    idx_p = np.random.choice(empty, min(PREDATOR_POPULATION, len(empty)), replace=False)
    flat[idx_p] = 2

    species = flat.reshape((GRID_HEIGHT, GRID_WIDTH))

    energy = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=np.uint8)
    energy[species == 1] = INITIAL_ENERGY
    energy[species == 2] = PREDATOR_INITIAL_ENERGY
    energy[species == 3] = HERBIVORE_B_INITIAL_ENERGY

    age = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=np.uint8)

    # pasto inicial en celdas vacías
    empty_idx = np.where((species == 0).flatten())[0]
    n_food = min(int(total * INITIAL_FOOD_DENSITY), len(empty_idx))
    chosen = np.random.choice(empty_idx, n_food, replace=False)
    food_flat = np.zeros(total, dtype=np.uint8)
    food_flat[chosen] = 1
    food = food_flat.reshape((GRID_HEIGHT, GRID_WIDTH))

    # infección inicial en unos pocos herbívoros
    infected = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=np.uint8)
    herb_pos = np.argwhere((species == 1) | (species == 3))
    if len(herb_pos) >= INFECTION_START_COUNT:
        seeds = np.random.choice(len(herb_pos), INFECTION_START_COUNT, replace=False)
        for i in seeds:
            infected[herb_pos[i, 0], herb_pos[i, 1]] = 1

    # genoma: variación inicial pequeña alrededor de los valores por defecto
    genome = np.zeros((GRID_HEIGHT, GRID_WIDTH, N_GENES), dtype=np.float32)
    for sp_id, defaults in [(1, GENOME_HERBIVORE), (2, GENOME_PREDATOR), (3, GENOME_HERBIVORE)]:
        mask = species == sp_id
        n = int(np.sum(mask))
        if n > 0:
            noise = np.random.randn(n, N_GENES).astype(np.float32) * GENOME_INIT_NOISE
            genome[mask] = np.clip(defaults + noise, GENOME_MIN, GENOME_MAX)

    # --- Fase 4: grillas nuevas ---
    # pheromone[y, x, layer]: concentración de feromona (0=herb_a, 1=pred, 2=herb_b)
    pheromone = np.zeros((GRID_HEIGHT, GRID_WIDTH, 3), dtype=np.float32)
    # territory[y, x, layer]: intensidad de reclamación territorial (mismos layers)
    territory = np.zeros((GRID_HEIGHT, GRID_WIDTH, 3), dtype=np.float32)
    # flock_a / flock_b: puntuaciones de cardumen por dirección (se calculan cada tick)
    flock_a = np.zeros((GRID_HEIGHT, GRID_WIDTH, 4), dtype=np.float32)
    flock_b = np.zeros((GRID_HEIGHT, GRID_WIDTH, 4), dtype=np.float32)

    return {
        "species":   species,
        "energy":    energy,
        "age":       age,
        "food":      food,
        "infected":  infected,
        "genome":    genome,
        "pheromone": pheromone,
        "territory": territory,
        "flock_a":   flock_a,
        "flock_b":   flock_b,
    }


def tick(state):
    state = food_rule.apply(state)
    state = pheromone_rule.apply(state)   # deposita, difunde y decae feromonas
    state = territory_rule.apply(state)   # deposita y decae territorio
    state = flocking.apply(state)         # precalcula puntuaciones de cardumen
    state = predation.apply(state)        # depredadores cazan (usan feromona de presas)
    state = infection_rule.apply(state)
    state = random_walk.apply(state)      # herbívoros se mueven (usan feromona + flock + territorio)
    state = aging.apply(state)
    state = reproduction.apply(state)
    return state


def build_render(state):
    render = state["species"].copy()
    infected = state["infected"]

    # overlay de infectados
    render[(state["species"] == 1) & (infected > 0)] = 5
    render[(state["species"] == 3) & (infected > 0)] = 6

    # pasto visible solo en celdas sin organismo
    render[(state["food"] > 0) & (state["species"] == 0)] = 10

    # --- Fase 4: feromonas en celdas vacías sin pasto ---
    if "pheromone" in state:
        ph = state["pheromone"]
        ph_max   = np.max(ph, axis=2)
        ph_which = np.argmax(ph, axis=2)  # 0=herb_a, 1=pred, 2=herb_b
        # Solo celdas vacías + sin pasto + concentración suficiente
        visible_ph = (render == 0) & (ph_max >= PHEROMONE_RENDER_THRESHOLD)
        render[visible_ph & (ph_which == 0)] = 11
        render[visible_ph & (ph_which == 1)] = 12
        render[visible_ph & (ph_which == 2)] = 13

    # --- Fase 4: territorio debajo de las feromonas (prioridad más baja) ---
    if "territory" in state:
        ter = state["territory"]
        ter_max   = np.max(ter, axis=2)
        ter_which = np.argmax(ter, axis=2)
        visible_ter = (render == 0) & (ter_max >= TERRITORY_RENDER_THRESHOLD)
        render[visible_ter & (ter_which == 0)] = 20
        render[visible_ter & (ter_which == 1)] = 21
        render[visible_ter & (ter_which == 2)] = 22

    return render
