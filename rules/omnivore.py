import numpy as np
from config import (
    GRID_WIDTH, GRID_HEIGHT,
    OMNI_MOVE_COST, OMNI_MAX_ENERGY, OMNI_ENERGY_FROM_PREY,
    GENE_VISION, GENE_FOOD_EFFICIENCY,
    TERRAIN_WATER_COST, TERRAIN_SWAMP_COST,
)

_DIRECTIONS = np.array([[-1, 0], [1, 0], [0, -1], [0, 1]], dtype=np.int32)
_TERRAIN_COST = np.array([1.0, TERRAIN_WATER_COST, 1.0, TERRAIN_SWAMP_COST], dtype=np.float32)


def apply(state):
    species = state["species"]
    energy  = state["energy"]
    genome  = state["genome"]
    food    = state["food"]
    terrain = state.get("terrain")
    gender  = state.get("gender")

    omnis = np.argwhere(species == 4)
    if len(omnis) == 0:
        return state

    n = len(omnis)
    prey = (species == 1) | (species == 3)

    omni_vision = np.round(genome[omnis[:, 0], omnis[:, 1], GENE_VISION]).astype(np.int32)
    max_vision  = int(omni_vision.max())
    dir_scores  = np.zeros((n, 4), dtype=np.float32)

    for d_idx in range(4):
        dy, dx = _DIRECTIONS[d_idx]
        for dist in range(1, max_vision + 1):
            look_y = np.clip(omnis[:, 0] + dy * dist, 0, GRID_HEIGHT - 1)
            look_x = np.clip(omnis[:, 1] + dx * dist, 0, GRID_WIDTH  - 1)
            within = omni_vision >= dist
            unset  = dir_scores[:, d_idx] == 0
            # presa atrae más que el pasto
            has_prey = unset & within & prey[look_y, look_x]
            dir_scores[has_prey, d_idx] = 1.2 / dist
            has_food = unset & ~has_prey & within & (food[look_y, look_x] > 0)
            dir_scores[has_food, d_idx] = 0.8 / dist

    # --- Cohesión de cardumen: atracción hacia otros omnívoros (favorece encontrar pareja) ---
    if "flock_omni" in state:
        fo = state["flock_omni"]
        for d_idx in range(4):
            dir_scores[:, d_idx] += fo[omnis[:, 0], omnis[:, 1], d_idx]

    dir_scores += np.random.uniform(0, 1e-4, dir_scores.shape)
    chosen = np.argmax(dir_scores, axis=1)

    targets = omnis + _DIRECTIONS[chosen]
    targets[:, 0] = np.clip(targets[:, 0], 0, GRID_HEIGHT - 1)
    targets[:, 1] = np.clip(targets[:, 1], 0, GRID_WIDTH  - 1)

    target_sp       = species[targets[:, 0], targets[:, 1]]
    is_prey_target  = (target_sp == 1) | (target_sp == 3)
    is_empty_target = target_sp == 0
    if terrain is not None:
        is_empty_target &= terrain[targets[:, 0], targets[:, 1]] != 2

    target_ids = targets[:, 0] * GRID_WIDTH + targets[:, 1]
    _, first_occ = np.unique(target_ids, return_index=True)
    no_conflict  = np.zeros(n, dtype=bool)
    no_conflict[first_occ] = True

    eating = is_prey_target  & no_conflict
    moving = is_empty_target & no_conflict

    new_species  = species.copy()
    new_energy   = energy.copy()
    new_infected = state["infected"].copy()
    new_genome   = genome.copy()
    new_gender   = gender.copy() if gender is not None else None

    if np.any(eating):
        efficiency = genome[omnis[eating, 0], omnis[eating, 1], GENE_FOOD_EFFICIENCY]
        energy_gained = np.minimum(
            energy[omnis[eating, 0], omnis[eating, 1]].astype(np.float32)
            + OMNI_ENERGY_FROM_PREY * efficiency,
            OMNI_MAX_ENERGY,
        ).astype(np.uint8)
        new_species [omnis[eating, 0], omnis[eating, 1]]    = 0
        new_species [targets[eating, 0], targets[eating, 1]] = 4
        new_energy  [targets[eating, 0], targets[eating, 1]] = energy_gained
        new_energy  [omnis[eating, 0], omnis[eating, 1]]    = 0
        new_infected[targets[eating, 0], targets[eating, 1]] = 0
        new_genome  [targets[eating, 0], targets[eating, 1]] = genome[omnis[eating, 0], omnis[eating, 1]]
        new_genome  [omnis[eating, 0], omnis[eating, 1]]    = 0
        if new_gender is not None:
            new_gender[targets[eating, 0], targets[eating, 1]] = gender[omnis[eating, 0], omnis[eating, 1]]
            new_gender[omnis[eating, 0], omnis[eating, 1]]    = 0

    if np.any(moving):
        new_species[omnis[moving, 0], omnis[moving, 1]]    = 0
        new_species[targets[moving, 0], targets[moving, 1]] = 4
        new_energy [targets[moving, 0], targets[moving, 1]] = energy[omnis[moving, 0], omnis[moving, 1]]
        new_energy [omnis[moving, 0], omnis[moving, 1]]    = 0
        new_genome [targets[moving, 0], targets[moving, 1]] = genome[omnis[moving, 0], omnis[moving, 1]]
        new_genome [omnis[moving, 0], omnis[moving, 1]]    = 0
        if new_gender is not None:
            new_gender[targets[moving, 0], targets[moving, 1]] = gender[omnis[moving, 0], omnis[moving, 1]]
            new_gender[omnis[moving, 0], omnis[moving, 1]]    = 0

    # costo metabólico con modificador de terreno
    alive_omni = new_species == 4
    if np.any(alive_omni):
        if terrain is not None:
            terrain_mult = _TERRAIN_COST[terrain]
            omni_cost = np.maximum(
                np.round(OMNI_MOVE_COST * terrain_mult).astype(np.int16), 1
            )
            new_energy[alive_omni] = np.maximum(
                new_energy[alive_omni].astype(np.int16) - omni_cost[alive_omni], 0
            ).astype(np.uint8)
        else:
            new_energy[alive_omni] = np.maximum(
                new_energy[alive_omni].astype(np.int16) - OMNI_MOVE_COST, 0
            ).astype(np.uint8)

    starved = (new_species == 4) & (new_energy == 0)
    new_species[starved] = 0
    new_genome [starved] = 0
    if new_gender is not None:
        new_gender[starved] = 0

    result = {**state, "species": new_species, "energy": new_energy,
              "infected": new_infected, "genome": new_genome}
    if new_gender is not None:
        result["gender"] = new_gender
    return result
