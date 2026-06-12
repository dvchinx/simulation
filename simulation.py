import numpy as np
from config import (
    GRID_WIDTH, GRID_HEIGHT,
    INITIAL_POPULATION, INITIAL_ENERGY,
    HERBIVORE_B_POPULATION, HERBIVORE_B_INITIAL_ENERGY,
    PREDATOR_POPULATION, PREDATOR_INITIAL_ENERGY,
    INITIAL_FOOD_DENSITY, INFECTION_START_COUNT,
)
from rules import random_walk, food as food_rule, aging, reproduction
from rules import predation, infection as infection_rule


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

    return {"species": species, "energy": energy, "age": age, "food": food, "infected": infected}


def tick(state):
    state = food_rule.apply(state)
    state = predation.apply(state)
    state = infection_rule.apply(state)
    state = random_walk.apply(state)
    state = aging.apply(state)
    state = reproduction.apply(state)
    return state


def build_render(state):
    render = state["species"].copy()
    infected = state["infected"]

    # overlay de infectados encima de su especie
    render[(state["species"] == 1) & (infected > 0)] = 5
    render[(state["species"] == 3) & (infected > 0)] = 6

    # pasto visible solo en celdas sin organismo
    render[(state["food"] > 0) & (state["species"] == 0)] = 10

    return render
