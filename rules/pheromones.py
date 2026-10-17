import numpy as np
from config import (
    GRID_HEIGHT, GRID_WIDTH,
    PHEROMONE_DEPOSIT, PHEROMONE_DECAY, PHEROMONE_DIFFUSION,
)
from rules.common import neighbor_sum

# species → capa de feromona: 0=herb_a, 1=pred, 2=herb_b
_SP_LAYER = {1: 0, 2: 1, 3: 2}


def apply(state):
    species = state["species"]
    ph = state["pheromone"].copy()

    # Depósito: cada organismo añade concentración en su celda actual
    for sp, layer in _SP_LAYER.items():
        ph[:, :, layer] += (species == sp).astype(np.float32) * PHEROMONE_DEPOSIT

    # Difusión: stencil de 5 puntos (centro + 4 vecinos cardinales), las 3 capas a la vez
    # coeficiente central = 1 - 4*d para conservar masa antes del decaimiento
    ph = (1.0 - 4.0 * PHEROMONE_DIFFUSION) * ph + PHEROMONE_DIFFUSION * neighbor_sum(ph)

    # Decaimiento exponencial y clamp
    ph *= PHEROMONE_DECAY
    np.clip(ph, 0.0, 1.0, out=ph)

    return {**state, "pheromone": ph}
