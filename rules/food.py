import numpy as np
from config import FOOD_ENERGY_GAIN, FOOD_REGEN_RATE


def apply(state):
    species = state["species"]
    energy = state["energy"].copy()
    food = state["food"].copy()

    # ambos herbívoros comen pasto en su celda
    eating = ((species == 1) | (species == 3)) & (food > 0)
    energy[eating] = np.minimum(
        energy[eating].astype(np.int16) + FOOD_ENERGY_GAIN, 255
    ).astype(np.uint8)
    food[eating] = 0

    # regenerar pasto en celdas vacías
    regen_candidates = (species == 0) & (food == 0)
    food[regen_candidates & (np.random.random(food.shape) < FOOD_REGEN_RATE)] = 1

    return {**state, "energy": energy, "food": food}
