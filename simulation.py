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
    DISTURBANCE_THRESHOLD,
)
from rules import random_walk, food as food_rule, aging, reproduction
from rules import predation, infection as infection_rule
from rules import pheromones as pheromone_rule, flocking, territory as territory_rule
from rules import terrain as terrain_rule
from rules import temperature as temperature_rule
from rules import diffusion as diffusion_rule
from rules import disturbances as disturbances_rule


def create_state():
    total = GRID_WIDTH * GRID_HEIGHT

    # Fase 5: generar terreno y biomas antes de colocar organismos
    terrain_grid, biome_grid = terrain_rule.generate()
    terrain_flat = terrain_grid.flatten()
    non_rock = np.where(terrain_flat != terrain_rule.TERRAIN_ROCK)[0]

    flat = np.zeros(total, dtype=np.uint8)

    # herbívoros A — solo en celdas no-roca
    idx_a = np.random.choice(non_rock, min(INITIAL_POPULATION, len(non_rock)), replace=False)
    flat[idx_a] = 1

    # herbívoros B
    available = np.where((flat == 0) & (terrain_flat != terrain_rule.TERRAIN_ROCK))[0]
    idx_b = np.random.choice(available, min(HERBIVORE_B_POPULATION, len(available)), replace=False)
    flat[idx_b] = 3

    # depredadores
    available = np.where((flat == 0) & (terrain_flat != terrain_rule.TERRAIN_ROCK))[0]
    idx_p = np.random.choice(available, min(PREDATOR_POPULATION, len(available)), replace=False)
    flat[idx_p] = 2

    species = flat.reshape((GRID_HEIGHT, GRID_WIDTH))

    energy = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=np.uint8)
    energy[species == 1] = INITIAL_ENERGY
    energy[species == 2] = PREDATOR_INITIAL_ENERGY
    energy[species == 3] = HERBIVORE_B_INITIAL_ENERGY

    age = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=np.uint8)

    # pasto inicial — solo en celdas vacías y no-roca
    food_candidates = np.where((species.flatten() == 0) & (terrain_flat != terrain_rule.TERRAIN_ROCK))[0]
    n_food = int(len(food_candidates) * INITIAL_FOOD_DENSITY)
    chosen = np.random.choice(food_candidates, min(n_food, len(food_candidates)), replace=False)
    food_flat = np.zeros(total, dtype=np.uint8)
    food_flat[chosen] = 1
    food = food_flat.reshape((GRID_HEIGHT, GRID_WIDTH))

    # infección inicial en algunos herbívoros
    infected = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=np.uint8)
    herb_pos = np.argwhere((species == 1) | (species == 3))
    if len(herb_pos) >= INFECTION_START_COUNT:
        seeds = np.random.choice(len(herb_pos), INFECTION_START_COUNT, replace=False)
        for i in seeds:
            infected[herb_pos[i, 0], herb_pos[i, 1]] = 1

    # genoma con variación inicial
    genome = np.zeros((GRID_HEIGHT, GRID_WIDTH, N_GENES), dtype=np.float32)
    for sp_id, defaults in [(1, GENOME_HERBIVORE), (2, GENOME_PREDATOR), (3, GENOME_HERBIVORE)]:
        mask = species == sp_id
        n = int(np.sum(mask))
        if n > 0:
            noise = np.random.randn(n, N_GENES).astype(np.float32) * GENOME_INIT_NOISE
            genome[mask] = np.clip(defaults + noise, GENOME_MIN, GENOME_MAX)

    # Fase 4
    pheromone = np.zeros((GRID_HEIGHT, GRID_WIDTH, 3), dtype=np.float32)
    territory  = np.zeros((GRID_HEIGHT, GRID_WIDTH, 3), dtype=np.float32)
    flock_a    = np.zeros((GRID_HEIGHT, GRID_WIDTH, 4), dtype=np.float32)
    flock_b    = np.zeros((GRID_HEIGHT, GRID_WIDTH, 4), dtype=np.float32)

    # Fase 5
    nutrient = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=np.float32)
    fire     = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=np.float32)
    flood    = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=np.float32)

    return {
        "species":            species,
        "energy":             energy,
        "age":                age,
        "food":               food,
        "infected":           infected,
        "genome":             genome,
        "pheromone":          pheromone,
        "territory":          territory,
        "flock_a":            flock_a,
        "flock_b":            flock_b,
        # Fase 5
        "terrain":            terrain_grid,
        "biome":              biome_grid,
        "nutrient":           nutrient,
        "fire":               fire,
        "flood":              flood,
        "tick_count":         0,
        "global_temperature": 0.0,
        "local_temperature":  np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=np.float32),
    }


def tick(state):
    state = {**state, "tick_count": state.get("tick_count", 0) + 1}
    state = temperature_rule.apply(state)    # actualiza local_temperature por estación
    state = disturbances_rule.apply(state)   # fuego/inundación periódicos
    state = food_rule.apply(state)           # comer + regen con bioma/temp/nutriente
    state = diffusion_rule.apply(state)      # difusión del gradiente de nutriente
    state = pheromone_rule.apply(state)
    state = territory_rule.apply(state)
    state = flocking.apply(state)
    state = predation.apply(state)
    state = infection_rule.apply(state)
    state = random_walk.apply(state)
    state = aging.apply(state)
    state = reproduction.apply(state)
    return state


def build_render(state):
    species  = state["species"]
    infected = state["infected"]
    render   = species.copy()

    # overlay de infectados
    render[(species == 1) & (infected > 0)] = 5
    render[(species == 3) & (infected > 0)] = 6

    # pasto en celdas sin organismo
    render[(state["food"] > 0) & (species == 0)] = 10

    # feromonas en celdas vacías sin pasto
    if "pheromone" in state:
        ph = state["pheromone"]
        ph_max   = np.max(ph, axis=2)
        ph_which = np.argmax(ph, axis=2)
        visible_ph = (render == 0) & (ph_max >= PHEROMONE_RENDER_THRESHOLD)
        render[visible_ph & (ph_which == 0)] = 11
        render[visible_ph & (ph_which == 1)] = 12
        render[visible_ph & (ph_which == 2)] = 13

    # territorio debajo de las feromonas
    if "territory" in state:
        ter = state["territory"]
        ter_max   = np.max(ter, axis=2)
        ter_which = np.argmax(ter, axis=2)
        visible_ter = (render == 0) & (ter_max >= TERRITORY_RENDER_THRESHOLD)
        render[visible_ter & (ter_which == 0)] = 20
        render[visible_ter & (ter_which == 1)] = 21
        render[visible_ter & (ter_which == 2)] = 22

    # Fase 5: terreno visible en celdas sin nada encima
    if "terrain" in state:
        t = state["terrain"]
        empty = render == 0
        render[empty & (t == 1)] = 30  # agua
        render[empty & (t == 2)] = 31  # roca (siempre vacía)
        render[empty & (t == 3)] = 32  # pantano

    # Fase 5: contornos de bioma — visibles sobre fondo en celdas sin organismo
    if "biome" in state:
        biome  = state["biome"]
        border = (
            (np.roll(biome, -1, axis=1) != biome) |
            (np.roll(biome,  1, axis=1) != biome) |
            (np.roll(biome, -1, axis=0) != biome) |
            (np.roll(biome,  1, axis=0) != biome)
        )
        render[(species == 0) & border] = 50

    # Fase 5: perturbaciones — prioridad máxima sobre el fondo en celdas vacías
    if "flood" in state:
        render[(species == 0) & (state["flood"] >= DISTURBANCE_THRESHOLD)] = 41
    if "fire" in state:
        render[(species == 0) & (state["fire"]  >= DISTURBANCE_THRESHOLD)] = 40

    return render
