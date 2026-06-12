import numpy as np
from config import GRID_WIDTH, GRID_HEIGHT, MOVE_ENERGY_COST

_DIRECTIONS = np.array([[-1, 0], [1, 0], [0, -1], [0, 1]], dtype=np.int32)


def apply(state):
    species = state["species"]
    energy = state["energy"]
    infected = state["infected"]

    # solo mueven los herbívoros; los depredadores se mueven en predation.py
    positions = np.argwhere((species == 1) | (species == 3))
    if len(positions) == 0:
        return state

    n = len(positions)
    species_ids = species[positions[:, 0], positions[:, 1]]

    targets = positions + _DIRECTIONS[np.random.randint(0, 4, n)]
    targets[:, 0] = np.clip(targets[:, 0], 0, GRID_HEIGHT - 1)
    targets[:, 1] = np.clip(targets[:, 1], 0, GRID_WIDTH - 1)

    can_move = species[targets[:, 0], targets[:, 1]] == 0

    target_ids = targets[:, 0] * GRID_WIDTH + targets[:, 1]
    _, first_occ = np.unique(target_ids, return_index=True)
    no_conflict = np.zeros(n, dtype=bool)
    no_conflict[first_occ] = True

    moving = can_move & no_conflict

    new_species = species.copy()
    new_energy = energy.copy()
    new_infected = infected.copy()

    new_species[positions[moving, 0], positions[moving, 1]] = 0
    new_species[targets[moving, 0], targets[moving, 1]] = species_ids[moving]

    new_energy[targets[moving, 0], targets[moving, 1]] = energy[positions[moving, 0], positions[moving, 1]]
    new_energy[positions[moving, 0], positions[moving, 1]] = 0

    # la infección se traslada con la célula
    new_infected[targets[moving, 0], targets[moving, 1]] = infected[positions[moving, 0], positions[moving, 1]]
    new_infected[positions[moving, 0], positions[moving, 1]] = 0

    # costo metabólico para todos los herbívoros vivos
    alive = (new_species == 1) | (new_species == 3)
    new_energy[alive] = np.maximum(
        new_energy[alive].astype(np.int16) - MOVE_ENERGY_COST, 0
    ).astype(np.uint8)

    # muerte por inanición
    starved = alive & (new_energy == 0)
    new_species[starved] = 0
    new_infected[starved] = 0

    return {**state, "species": new_species, "energy": new_energy, "infected": new_infected}
