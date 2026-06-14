import numpy as np
from config import TERRITORY_DEPOSIT, TERRITORY_DECAY

# species → capa territorial: 0=herb_a, 1=pred, 2=herb_b
_SP_LAYER = {1: 0, 2: 1, 3: 2}


def apply(state):
    species = state["species"]
    ter = state["territory"].copy()

    # Depósito: cada organismo reafirma su reclamación en la celda que ocupa
    for sp, layer in _SP_LAYER.items():
        ter[:, :, layer] += (species == sp).astype(np.float32) * TERRITORY_DEPOSIT

    # Decaimiento muy lento — el territorio persiste mucho más que las feromonas
    ter *= TERRITORY_DECAY
    np.clip(ter, 0.0, 1.0, out=ter)

    return {**state, "territory": ter}
