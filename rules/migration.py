"""Migración (efecto rescate): cuando una especie lleva MIGRATION_DELAY ticks
extinta, un grupo fundador llega a una zona aleatoria del mapa."""
import numpy as np
from config import (
    GRID_HEIGHT, GRID_WIDTH, SPECIES, N_GENES,
    GENOME_MIN, GENOME_MAX, GENOME_INIT_NOISE,
    MIGRATION_DELAY, MIGRATION_GROUP, MIGRATION_RADIUS,
)
from rules.common import TERRAIN_ROCK, copy_layers

_YS, _XS = np.ogrid[:GRID_HEIGHT, :GRID_WIDTH]


def spawn(layers, flat_idx, sp_id, age=None):
    """Coloca organismos nuevos de la especie sp_id en los índices planos dados:
    energía inicial, género aleatorio y genoma por defecto con variación."""
    n = len(flat_idx)
    if n == 0:
        return
    spec = SPECIES[sp_id]
    rows, cols = np.unravel_index(flat_idx, (GRID_HEIGHT, GRID_WIDTH))
    noise = np.random.randn(n, N_GENES).astype(np.float32) * GENOME_INIT_NOISE
    layers["species"] [rows, cols] = sp_id
    layers["energy"]  [rows, cols] = spec["initial_energy"]
    layers["age"]     [rows, cols] = 0 if age is None else age
    layers["infected"][rows, cols] = 0
    layers["gender"]  [rows, cols] = np.random.randint(1, 3, n, dtype=np.uint8)
    layers["genome"]  [rows, cols] = np.clip(spec["genome"] + noise, GENOME_MIN, GENOME_MAX)


def apply(state):
    tick = state.get("tick_count", 0)
    counts = np.bincount(state["species"].ravel(), minlength=len(SPECIES) + 1)
    extinct_since = dict(state.get("extinct_since", {}))

    arriving = []
    for sp_id in SPECIES:
        if counts[sp_id] > 0:
            extinct_since.pop(sp_id, None)
        elif sp_id not in extinct_since:
            extinct_since[sp_id] = tick
        elif tick - extinct_since[sp_id] >= MIGRATION_DELAY:
            arriving.append(sp_id)
            extinct_since.pop(sp_id)

    if not arriving:
        return {**state, "extinct_since": extinct_since}

    layers = copy_layers(state)
    terrain = state.get("terrain")
    free = layers["species"] == 0
    if terrain is not None:
        free &= terrain != TERRAIN_ROCK

    events = list(state.get("events", []))
    for sp_id in arriving:
        cy, cx = np.argwhere(free)[np.random.randint(np.count_nonzero(free))]
        zone = free & (((_YS - cy) ** 2 + (_XS - cx) ** 2) <= MIGRATION_RADIUS ** 2)
        candidates = np.flatnonzero(zone)
        chosen = np.random.choice(candidates, min(MIGRATION_GROUP[sp_id], len(candidates)), replace=False)
        spawn(layers, chosen, sp_id)
        free.ravel()[chosen] = False
        events.append({"tick": tick, "kind": "migration", "species": sp_id,
                       "count": int(len(chosen)), "row": int(cy), "col": int(cx)})

    return {**state, **layers, "extinct_since": extinct_since, "events": events}
