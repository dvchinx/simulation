import numpy as np
from config import (
    GRID_WIDTH, GRID_HEIGHT,
    INITIAL_ENERGY, PREDATOR_INITIAL_ENERGY,
    N_GENES, GENOME_MIN, GENOME_MAX,
    GENE_REPRO_ENERGY, GENE_MUTATION_RATE,
    TEMP_REPRO_PENALTY,
)

_DIRECTIONS = np.array([[-1, 0], [1, 0], [0, -1], [0, 1]], dtype=np.int32)


def apply(state):
    species  = state["species"]
    energy   = state["energy"]
    age      = state["age"]
    infected = state["infected"]
    genome   = state["genome"]
    terrain  = state.get("terrain")

    new_species  = species.copy()
    new_energy   = energy.copy()
    new_age      = age.copy()
    new_infected = infected.copy()
    new_genome   = genome.copy()

    # Umbral de reproducción base por genoma + penalización por temperatura extrema
    repro_thresh = genome[:, :, GENE_REPRO_ENERGY].astype(np.float32)
    if "local_temperature" in state:
        repro_thresh = repro_thresh + np.abs(state["local_temperature"]) * TEMP_REPRO_PENALTY

    for sp_id, init_energy in [(1, INITIAL_ENERGY), (2, PREDATOR_INITIAL_ENERGY), (3, INITIAL_ENERGY)]:
        parents = np.argwhere(
            (new_species == sp_id) & (new_energy.astype(np.float32) >= repro_thresh)
        )
        if len(parents) == 0:
            continue

        n       = len(parents)
        targets = parents + _DIRECTIONS[np.random.randint(0, 4, n)]
        targets[:, 0] = np.clip(targets[:, 0], 0, GRID_HEIGHT - 1)
        targets[:, 1] = np.clip(targets[:, 1], 0, GRID_WIDTH - 1)

        can_birth = new_species[targets[:, 0], targets[:, 1]] == 0
        # Fase 5: no reproducirse en roca
        if terrain is not None:
            can_birth &= terrain[targets[:, 0], targets[:, 1]] != 2

        target_ids = targets[:, 0] * GRID_WIDTH + targets[:, 1]
        _, first_occ = np.unique(target_ids, return_index=True)
        no_conflict  = np.zeros(n, dtype=bool)
        no_conflict[first_occ] = True

        birthing = can_birth & no_conflict

        new_species[targets[birthing, 0], targets[birthing, 1]] = sp_id
        new_energy [targets[birthing, 0], targets[birthing, 1]] = init_energy
        new_age    [targets[birthing, 0], targets[birthing, 1]] = 0
        new_energy [parents[birthing, 0], parents[birthing, 1]] = init_energy

        parent_g  = genome[parents[birthing, 0], parents[birthing, 1]]
        mut_rates = parent_g[:, GENE_MUTATION_RATE:GENE_MUTATION_RATE + 1]
        noise     = (np.random.randn(len(parent_g), N_GENES) * mut_rates).astype(np.float32)
        child_g   = np.clip(parent_g + noise, GENOME_MIN, GENOME_MAX)
        new_genome[targets[birthing, 0], targets[birthing, 1]] = child_g

        if sp_id in (1, 3):
            parent_inf = infected[parents[birthing, 0], parents[birthing, 1]]
            new_infected[targets[birthing, 0], targets[birthing, 1]] = parent_inf

    return {**state, "species": new_species, "energy": new_energy, "age": new_age, "infected": new_infected, "genome": new_genome}
