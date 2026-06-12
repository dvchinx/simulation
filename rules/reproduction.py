import numpy as np
from config import (
    GRID_WIDTH, GRID_HEIGHT,
    MAX_ENERGY, INITIAL_ENERGY,
    PREDATOR_REPRODUCE_ENERGY, PREDATOR_INITIAL_ENERGY,
)

_DIRECTIONS = np.array([[-1, 0], [1, 0], [0, -1], [0, 1]], dtype=np.int32)

# (species_id, energy_threshold, initial_energy_for_offspring)
_SPECIES_PARAMS = [
    (1, MAX_ENERGY,         INITIAL_ENERGY),
    (2, PREDATOR_REPRODUCE_ENERGY, PREDATOR_INITIAL_ENERGY),
    (3, MAX_ENERGY,         INITIAL_ENERGY),
]


def apply(state):
    species = state["species"]
    energy = state["energy"]
    age = state["age"]
    infected = state["infected"]

    new_species = species.copy()
    new_energy = energy.copy()
    new_age = age.copy()
    new_infected = infected.copy()

    for sp_id, threshold, init_energy in _SPECIES_PARAMS:
        parents = np.argwhere((new_species == sp_id) & (new_energy >= threshold))
        if len(parents) == 0:
            continue

        n = len(parents)
        targets = parents + _DIRECTIONS[np.random.randint(0, 4, n)]
        targets[:, 0] = np.clip(targets[:, 0], 0, GRID_HEIGHT - 1)
        targets[:, 1] = np.clip(targets[:, 1], 0, GRID_WIDTH - 1)

        can_birth = new_species[targets[:, 0], targets[:, 1]] == 0
        target_ids = targets[:, 0] * GRID_WIDTH + targets[:, 1]
        _, first_occ = np.unique(target_ids, return_index=True)
        no_conflict = np.zeros(n, dtype=bool)
        no_conflict[first_occ] = True

        birthing = can_birth & no_conflict

        new_species[targets[birthing, 0], targets[birthing, 1]] = sp_id
        new_energy[targets[birthing, 0], targets[birthing, 1]] = init_energy
        new_age[targets[birthing, 0], targets[birthing, 1]] = 0

        # el padre resetea energía al reproducirse
        new_energy[parents[birthing, 0], parents[birthing, 1]] = init_energy

        # los herbívoros infectados transmiten infección a su cría
        if sp_id in (1, 3):
            parent_infected = infected[parents[birthing, 0], parents[birthing, 1]]
            new_infected[targets[birthing, 0], targets[birthing, 1]] = parent_infected

    return {**state, "species": new_species, "energy": new_energy, "age": new_age, "infected": new_infected}
