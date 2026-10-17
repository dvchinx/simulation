import numpy as np
from config import NUTRIENT_DEPOSIT, NUTRIENT_DIFFUSION, NUTRIENT_DECAY
from rules.common import neighbor_sum, TERRAIN_ROCK


def apply(state):
    food     = state["food"]
    nutrient = state.get("nutrient", np.zeros(food.shape, dtype=np.float32))
    terrain  = state.get("terrain")

    # Ecuación de difusión estable: D <= 0.25 garantiza estabilidad numérica
    spread = neighbor_sum(nutrient)

    new_nutrient = nutrient * (1.0 - 4.0 * NUTRIENT_DIFFUSION) + spread * NUTRIENT_DIFFUSION
    new_nutrient *= NUTRIENT_DECAY
    new_nutrient += food.astype(np.float32) * NUTRIENT_DEPOSIT

    if terrain is not None:
        new_nutrient[terrain == TERRAIN_ROCK] = 0.0  # sin nutriente en roca

    return {**state, "nutrient": np.clip(new_nutrient, 0.0, 1.0)}
