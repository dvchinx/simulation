import numpy as np
from config import (
    GRID_HEIGHT, GRID_WIDTH,
    FLOCK_RADIUS, FLOCK_COHESION_WEIGHT,
    FLOCK_SEPARATION_RADIUS, FLOCK_SEPARATION_WEIGHT,
)

# N, S, W, E — mismo orden que random_walk._DIRECTIONS
_DIRS = np.array([[-1, 0], [1, 0], [0, -1], [0, 1]], dtype=np.int32)


def _scores_for_species(density):
    """
    Devuelve array (H, W, 4) de puntuaciones de cardumen para organismos de la especie dada.
    Positivo = atracción (cohesión), negativo = repulsión (separación).
    """
    scores = np.zeros((GRID_HEIGHT, GRID_WIDTH, 4), dtype=np.float32)

    for d_idx, (dy, dx) in enumerate(_DIRS):
        # Cohesión: suma ponderada de congéneres en la dirección d a distancias 1..FLOCK_RADIUS
        cohesion = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=np.float32)
        for r in range(1, FLOCK_RADIUS + 1):
            # np.roll(-dy*r, axis=0) trae a (y,x) el valor que estaba en (y+dy*r, x)
            shifted = np.roll(
                np.roll(density, -dy * r, axis=0),
                -dx * r, axis=1,
            )
            cohesion += shifted / r

        # Separación: presencia de congéneres dentro de FLOCK_SEPARATION_RADIUS
        separation = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=np.float32)
        for r in range(1, FLOCK_SEPARATION_RADIUS + 1):
            shifted = np.roll(
                np.roll(density, -dy * r, axis=0),
                -dx * r, axis=1,
            )
            separation += shifted

        scores[:, :, d_idx] = (
            FLOCK_COHESION_WEIGHT   * cohesion
            - FLOCK_SEPARATION_WEIGHT * separation
        )

    return scores


def apply(state):
    species = state["species"]

    flock_a    = _scores_for_species((species == 1).astype(np.float32))
    flock_b    = _scores_for_species((species == 3).astype(np.float32))
    flock_pred = _scores_for_species((species == 2).astype(np.float32))
    flock_omni = _scores_for_species((species == 4).astype(np.float32))

    return {**state,
            "flock_a": flock_a, "flock_b": flock_b,
            "flock_pred": flock_pred, "flock_omni": flock_omni}
