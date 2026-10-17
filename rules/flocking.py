import numpy as np
from config import (
    GRID_HEIGHT, GRID_WIDTH,
    FLOCK_RADIUS, FLOCK_COHESION_WEIGHT,
    FLOCK_SEPARATION_RADIUS, FLOCK_SEPARATION_WEIGHT,
)
from rules.common import DIRECTIONS

# (clave de estado, id de especie) — todas se calculan en un único array apilado
_FLOCKS = (("flock_a", 1), ("flock_pred", 2), ("flock_b", 3), ("flock_omni", 4))
_PAD = max(FLOCK_RADIUS, FLOCK_SEPARATION_RADIUS)

# Peso por distancia r en la dirección d: cohesión 1/r (r <= FLOCK_RADIUS)
# menos separación (r <= FLOCK_SEPARATION_RADIUS)
_RADIUS_WEIGHTS = [
    (r,
     (FLOCK_COHESION_WEIGHT / r if r <= FLOCK_RADIUS else 0.0)
     - (FLOCK_SEPARATION_WEIGHT if r <= FLOCK_SEPARATION_RADIUS else 0.0))
    for r in range(1, _PAD + 1)
]


def apply(state):
    """
    Campos (H, W, 4) de puntuación direccional de cardumen por especie.
    Positivo = atracción (cohesión), negativo = repulsión (separación).
    Los bordes no hacen wrap: fuera del grid no hay congéneres.
    """
    species = state["species"]
    density = np.stack([species == sp for _, sp in _FLOCKS]).astype(np.float32)
    padded  = np.pad(density, ((0, 0), (_PAD, _PAD), (_PAD, _PAD)))

    scores = np.zeros((len(_FLOCKS), GRID_HEIGHT, GRID_WIDTH, 4), dtype=np.float32)
    for d_idx, (dy, dx) in enumerate(DIRECTIONS):
        acc = scores[..., d_idx]
        for r, weight in _RADIUS_WEIGHTS:
            # trae a (y, x) la densidad que está en (y + dy·r, x + dx·r)
            y0 = _PAD + dy * r
            x0 = _PAD + dx * r
            acc += weight * padded[:, y0:y0 + GRID_HEIGHT, x0:x0 + GRID_WIDTH]

    return {**state, **{key: scores[i] for i, (key, _) in enumerate(_FLOCKS)}}
