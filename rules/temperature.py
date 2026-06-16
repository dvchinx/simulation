import numpy as np
from config import (
    GRID_HEIGHT, GRID_WIDTH,
    SEASON_PERIOD, SEASON_AMPLITUDE,
    BIOME_TEMP_OFFSET,
)


def apply(state):
    tick = state.get("tick_count", 0)
    global_temp = float(np.sin(2.0 * np.pi * tick / SEASON_PERIOD) * SEASON_AMPLITUDE)

    if "biome" in state:
        local_temp = np.clip(
            global_temp + BIOME_TEMP_OFFSET[state["biome"]],
            -1.0, 1.0,
        ).astype(np.float32)
    else:
        local_temp = np.full((GRID_HEIGHT, GRID_WIDTH), global_temp, dtype=np.float32)

    return {**state, "global_temperature": global_temp, "local_temperature": local_temp}
