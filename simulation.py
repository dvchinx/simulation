import numpy as np
from config import (
    GRID_WIDTH, GRID_HEIGHT, SPECIES,
    INITIAL_POPULATION, HERBIVORE_B_POPULATION, PREDATOR_POPULATION, OMNI_POPULATION,
    INITIAL_FOOD_DENSITY, INFECTION_START_COUNT, N_GENES,
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
from rules import omnivore as omnivore_rule
from rules import migration as migration_rule
from rules.common import dominant_layer

_SHAPE = (GRID_HEIGHT, GRID_WIDTH)

# Orden de aplicación de las reglas en cada tick
RULES = (
    temperature_rule,    # actualiza local_temperature por estación
    disturbances_rule,   # fuego/inundación periódicos
    food_rule,           # comer + regen con bioma/temp/nutriente
    diffusion_rule,      # difusión del gradiente de nutriente
    pheromone_rule,
    territory_rule,
    flocking,
    predation,
    omnivore_rule,
    infection_rule,
    random_walk,
    aging,
    reproduction,
    migration_rule,      # grupo fundador si una especie lleva tiempo extinta
)

_INITIAL_POPULATIONS = {
    1: INITIAL_POPULATION,
    3: HERBIVORE_B_POPULATION,
    2: PREDATOR_POPULATION,
    4: OMNI_POPULATION,
}


def _biome_border(biome):
    """Celdas en el límite entre dos biomas (estático: se calcula una vez).
    Solo se marca el lado inferior/derecho para que el contorno mida 1 celda."""
    border = np.zeros(biome.shape, dtype=bool)
    border[1:]    |= biome[1:]    != biome[:-1]
    border[:, 1:] |= biome[:, 1:] != biome[:, :-1]
    return border


def create_state():
    # Fase 5: generar terreno y biomas antes de colocar organismos
    terrain_grid, biome_grid = terrain_rule.generate()
    walkable = terrain_grid.ravel() != terrain_rule.TERRAIN_ROCK

    layers = {
        "species":  np.zeros(_SHAPE, dtype=np.uint8),
        "energy":   np.zeros(_SHAPE, dtype=np.uint8),
        "age":      np.zeros(_SHAPE, dtype=np.uint8),
        "infected": np.zeros(_SHAPE, dtype=np.uint8),
        "gender":   np.zeros(_SHAPE, dtype=np.uint8),
        "genome":   np.zeros((*_SHAPE, N_GENES), dtype=np.float32),
    }

    # Organismos en celdas libres y no-roca; edades iniciales escalonadas para
    # que la cohorte fundadora no muera de vejez en el mismo tick
    for sp_id, count in _INITIAL_POPULATIONS.items():
        available = np.flatnonzero((layers["species"].ravel() == 0) & walkable)
        chosen = np.random.choice(available, min(count, len(available)), replace=False)
        ages = np.random.randint(0, SPECIES[sp_id]["max_age"] // 2, len(chosen))
        migration_rule.spawn(layers, chosen, sp_id, age=ages)

    # pasto inicial — solo en celdas vacías y no-roca
    food_candidates = np.flatnonzero((layers["species"].ravel() == 0) & walkable)
    n_food = int(len(food_candidates) * INITIAL_FOOD_DENSITY)
    food = np.zeros(GRID_HEIGHT * GRID_WIDTH, dtype=np.uint8)
    food[np.random.choice(food_candidates, n_food, replace=False)] = 1

    # infección inicial en algunos herbívoros
    herb_idx = np.flatnonzero(np.isin(layers["species"], (1, 3)))
    if len(herb_idx) >= INFECTION_START_COUNT:
        seeds = np.random.choice(herb_idx, INFECTION_START_COUNT, replace=False)
        layers["infected"].ravel()[seeds] = 1

    return {
        **layers,
        "food":       food.reshape(_SHAPE),
        # Fase 4
        "pheromone":  np.zeros((*_SHAPE, 3), dtype=np.float32),
        "territory":  np.zeros((*_SHAPE, 3), dtype=np.float32),
        "flock_a":    np.zeros((*_SHAPE, 4), dtype=np.float32),
        "flock_b":    np.zeros((*_SHAPE, 4), dtype=np.float32),
        "flock_pred": np.zeros((*_SHAPE, 4), dtype=np.float32),
        "flock_omni": np.zeros((*_SHAPE, 4), dtype=np.float32),
        # Fase 5
        "terrain":      terrain_grid,
        "biome":        biome_grid,
        "biome_border": _biome_border(biome_grid),
        "nutrient":     np.zeros(_SHAPE, dtype=np.float32),
        "fire":         np.zeros(_SHAPE, dtype=np.float32),
        "flood":        np.zeros(_SHAPE, dtype=np.float32),
        "tick_count":         0,
        "global_temperature": 0.0,
        "local_temperature":  np.zeros(_SHAPE, dtype=np.float32),
        "extinct_since":      {},
        "events":             [],
    }


def tick(state):
    state = {**state, "tick_count": state.get("tick_count", 0) + 1, "events": []}
    for rule in RULES:
        state = rule.apply(state)
    return state


def build_render(state):
    """Un byte por celda con el código visual de mayor prioridad (ver
    SPECIES_COLORS en config.py). Orden, de menor a mayor: terreno → territorio
    → feromona → pasto → organismos; en celdas vacías, bordes de bioma →
    inundación → fuego."""
    species = state["species"]
    render  = species.copy()
    empty   = species == 0

    # overlay de infectados: 1→5, 3→6, 4→7
    infected = state["infected"] > 0
    render[infected & (species == 1)] = 5
    render[infected & (species == 3)] = 6
    render[infected & (species == 4)] = 7

    # pasto en celdas sin organismo
    render[empty & (state["food"] > 0)] = 10

    # feromonas y, debajo, territorio: código base + capa dominante
    for key, threshold, base in (("pheromone", PHEROMONE_RENDER_THRESHOLD, 11),
                                 ("territory", TERRITORY_RENDER_THRESHOLD, 20)):
        if key in state:
            strength, which = dominant_layer(state[key])
            visible = (render == 0) & (strength >= threshold)
            render[visible] = base + which[visible]

    # Fase 5: terreno visible en celdas sin nada encima (1→30, 2→31, 3→32)
    if "terrain" in state:
        t = state["terrain"]
        bare = (render == 0) & (t > 0)
        render[bare] = 29 + t[bare]

    # Fase 5: contornos de bioma y perturbaciones — prioridad sobre el fondo en celdas vacías
    if "biome_border" in state:
        render[empty & state["biome_border"]] = 50
    if "flood" in state:
        render[empty & (state["flood"] >= DISTURBANCE_THRESHOLD)] = 41
    if "fire" in state:
        render[empty & (state["fire"] >= DISTURBANCE_THRESHOLD)] = 40

    return render
