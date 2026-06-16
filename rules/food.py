import numpy as np
from config import (
    FOOD_ENERGY_GAIN, FOOD_REGEN_RATE, GENE_FOOD_EFFICIENCY,
    BIOME_REGEN_MULT, TEMP_REGEN_FACTOR,
    NUTRIENT_REGEN_BOOST,
)


def apply(state):
    species = state["species"]
    energy  = state["energy"].copy()
    food    = state["food"].copy()
    genome  = state["genome"]

    # Herbívoros comen pasto
    eating = ((species == 1) | (species == 3)) & (food > 0)
    if np.any(eating):
        efficiency = genome[eating, GENE_FOOD_EFFICIENCY]
        new_e = np.minimum(
            energy[eating].astype(np.float32) + FOOD_ENERGY_GAIN * efficiency,
            255.0,
        ).astype(np.uint8)
        energy[eating] = new_e
    food[eating] = 0

    # Regeneración con modificadores de bioma, temperatura y nutriente
    regen_rate = np.full(food.shape, FOOD_REGEN_RATE, dtype=np.float32)

    if "biome" in state:
        regen_rate *= BIOME_REGEN_MULT[state["biome"]]

    if "local_temperature" in state:
        temp_factor = np.maximum(0.05, 1.0 - np.abs(state["local_temperature"]) * TEMP_REGEN_FACTOR)
        regen_rate *= temp_factor

    if "nutrient" in state:
        regen_rate += NUTRIENT_REGEN_BOOST * state["nutrient"]

    regen_rate = np.clip(regen_rate, 0.0, 0.95)

    regen_candidates = (species == 0) & (food == 0)
    if "terrain" in state:
        regen_candidates &= state["terrain"] != 2  # sin pasto en roca

    food[regen_candidates & (np.random.random(food.shape) < regen_rate)] = 1

    return {**state, "energy": energy, "food": food}
