import numpy as np
from config import (
    GRID_HEIGHT, GRID_WIDTH,
    FIRE_PERIOD, FIRE_RADIUS, FIRE_DECAY,
    FLOOD_PERIOD, FLOOD_WIDTH, FLOOD_DECAY,
)
from rules.common import TERRAIN_ROCK, copy_layers, kill

_YS, _XS = np.ogrid[:GRID_HEIGHT, :GRID_WIDTH]


def apply(state):
    tick    = state.get("tick_count", 0)
    fire    = state.get("fire",  np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=np.float32))
    flood   = state.get("flood", np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=np.float32))
    terrain = state.get("terrain")

    fire  = fire  * FIRE_DECAY
    flood = flood * FLOOD_DECAY

    fire_now  = tick > 0 and tick % FIRE_PERIOD == 0
    flood_now = tick > 0 and tick % FLOOD_PERIOD == 0
    if not (fire_now or flood_now):
        return {**state, "fire": fire, "flood": flood}

    layers = copy_layers(state)
    food   = state["food"].copy()
    events = list(state.get("events", []))

    # --- Fuego ---
    if fire_now:
        if terrain is not None:
            candidates = np.argwhere(terrain != TERRAIN_ROCK)
        else:
            candidates = np.argwhere(np.ones((GRID_HEIGHT, GRID_WIDTH), dtype=bool))
        cy, cx = candidates[np.random.randint(len(candidates))]
        mask = ((_YS - cy) ** 2 + (_XS - cx) ** 2) <= FIRE_RADIUS ** 2
        kill(layers, mask)
        food[mask] = 0
        fire[mask] = 1.0
        events.append({"tick": tick, "kind": "fire", "row": int(cy), "col": int(cx)})

    # --- Inundación ---
    if flood_now:
        cy   = np.random.randint(GRID_HEIGHT)
        y_lo = max(0, cy - FLOOD_WIDTH)
        y_hi = min(GRID_HEIGHT, cy + FLOOD_WIDTH)
        mask = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=bool)
        mask[y_lo:y_hi, :] = True
        kill(layers, mask)
        food[mask]  = 0
        flood[mask] = 1.0
        events.append({"tick": tick, "kind": "flood", "row": int(cy), "col": GRID_WIDTH // 2})

    return {**state, **layers, "food": food, "fire": fire, "flood": flood, "events": events}
