import numpy as np
from config import (
    GRID_HEIGHT, GRID_WIDTH,
    FIRE_PERIOD, FIRE_RADIUS, FIRE_DECAY,
    FLOOD_PERIOD, FLOOD_WIDTH, FLOOD_DECAY,
)

_YS, _XS = np.ogrid[:GRID_HEIGHT, :GRID_WIDTH]


def apply(state):
    tick    = state.get("tick_count", 0)
    fire    = state.get("fire",  np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=np.float32))
    flood   = state.get("flood", np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=np.float32))
    terrain = state.get("terrain")

    species  = state["species"].copy()
    energy   = state["energy"].copy()
    genome   = state["genome"].copy()
    infected = state["infected"].copy()
    food     = state["food"].copy()

    fire  = fire  * FIRE_DECAY
    flood = flood * FLOOD_DECAY

    # --- Fuego ---
    if tick > 0 and tick % FIRE_PERIOD == 0:
        if terrain is not None:
            candidates = np.argwhere(terrain != 2)
        else:
            candidates = np.argwhere(np.ones((GRID_HEIGHT, GRID_WIDTH), dtype=bool))
        cy, cx = candidates[np.random.randint(len(candidates))]
        mask = ((_YS - cy) ** 2 + (_XS - cx) ** 2) <= FIRE_RADIUS ** 2
        species[mask]  = 0
        energy[mask]   = 0
        genome[mask]   = 0
        infected[mask] = 0
        food[mask]     = 0
        fire[mask]     = 1.0

    # --- Inundación ---
    if tick > 0 and tick % FLOOD_PERIOD == 0:
        cy   = np.random.randint(GRID_HEIGHT)
        y_lo = max(0, cy - FLOOD_WIDTH)
        y_hi = min(GRID_HEIGHT, cy + FLOOD_WIDTH)
        mask = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=bool)
        mask[y_lo:y_hi, :] = True
        species[mask]  = 0
        energy[mask]   = 0
        genome[mask]   = 0
        infected[mask] = 0
        food[mask]     = 0
        flood[mask]    = 1.0

    return {**state,
            "species":  species,  "energy":   energy,
            "genome":   genome,   "infected": infected,
            "food":     food,
            "fire":     fire,     "flood":    flood}
