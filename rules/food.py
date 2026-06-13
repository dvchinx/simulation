import numpy as np
from config import FOOD_ENERGY_GAIN, FOOD_REGEN_RATE, GENE_FOOD_EFFICIENCY


def apply(state):
    species = state["species"]
    energy = state["energy"].copy()
    food = state["food"].copy()
    genome = state["genome"]

    eating = ((species == 1) | (species == 3)) & (food > 0)
    if np.any(eating):
        efficiency = genome[eating, GENE_FOOD_EFFICIENCY]
        new_e = np.minimum(
            energy[eating].astype(np.float32) + FOOD_ENERGY_GAIN * efficiency,
            255.0,
        ).astype(np.uint8)
        energy[eating] = new_e
    food[eating] = 0

    regen_candidates = (species == 0) & (food == 0)
    food[regen_candidates & (np.random.random(food.shape) < FOOD_REGEN_RATE)] = 1

    return {**state, "energy": energy, "food": food}
