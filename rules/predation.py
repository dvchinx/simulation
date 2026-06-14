import numpy as np
from config import (
    GRID_WIDTH, GRID_HEIGHT,
    PREDATOR_MOVE_COST, PREDATOR_MAX_ENERGY, PREDATOR_ENERGY_FROM_PREY,
    GENE_VISION, GENE_FOOD_EFFICIENCY,
    PHEROMONE_PRED_ATTRACTION,
)

_DIRECTIONS = np.array([[-1, 0], [1, 0], [0, -1], [0, 1]], dtype=np.int32)
_MAX_VISION = 12  # techo global del rango de visión del genoma


def apply(state):
    species = state["species"]
    energy  = state["energy"]
    genome  = state["genome"]

    predators = np.argwhere(species == 2)
    if len(predators) == 0:
        return state

    n    = len(predators)
    prey = (species == 1) | (species == 3)

    # Rango de visión individual por genoma
    pred_vision = np.round(genome[predators[:, 0], predators[:, 1], GENE_VISION]).astype(np.int32)
    dir_scores  = np.zeros((n, 4), dtype=np.float32)

    for d_idx in range(4):
        dy, dx = _DIRECTIONS[d_idx]
        for dist in range(1, _MAX_VISION + 1):
            look_y = np.clip(predators[:, 0] + dy * dist, 0, GRID_HEIGHT - 1)
            look_x = np.clip(predators[:, 1] + dx * dist, 0, GRID_WIDTH - 1)
            within = pred_vision >= dist
            unset  = dir_scores[:, d_idx] == 0
            found  = unset & within & prey[look_y, look_x]
            dir_scores[found, d_idx] = 1.0 / dist

    # --- Fase 4: rastreo de feromona de presas (quimiotaxis de caza) ---
    # Los depredadores siguen el rastro químico combinado de herbívoros A y B,
    # lo que les permite cazar en zonas recientemente visitadas aunque no haya
    # presa en línea de visión directa.
    if "pheromone" in state:
        prey_ph = state["pheromone"][:, :, 0] + state["pheromone"][:, :, 2]
        for d_idx in range(4):
            dy, dx = _DIRECTIONS[d_idx]
            ny = np.clip(predators[:, 0] + dy, 0, GRID_HEIGHT - 1)
            nx = np.clip(predators[:, 1] + dx, 0, GRID_WIDTH - 1)
            dir_scores[:, d_idx] += PHEROMONE_PRED_ATTRACTION * prey_ph[ny, nx]

    dir_scores += np.random.uniform(0, 1e-4, dir_scores.shape)
    no_prey    = np.all(dir_scores <= 1e-4, axis=1)
    best_dir   = np.argmax(dir_scores, axis=1)
    random_dir = np.random.randint(0, 4, n)
    chosen     = np.where(no_prey, random_dir, best_dir)

    targets = predators + _DIRECTIONS[chosen]
    targets[:, 0] = np.clip(targets[:, 0], 0, GRID_HEIGHT - 1)
    targets[:, 1] = np.clip(targets[:, 1], 0, GRID_WIDTH - 1)

    target_sp       = species[targets[:, 0], targets[:, 1]]
    is_prey_target  = (target_sp == 1) | (target_sp == 3)
    is_empty_target = target_sp == 0

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

    # Comer: energía ganada escalada por gen de eficiencia alimentaria
    if np.any(eating):
        efficiency    = genome[predators[eating, 0], predators[eating, 1], GENE_FOOD_EFFICIENCY]
        energy_gained = np.minimum(
            energy[predators[eating, 0], predators[eating, 1]].astype(np.float32)
            + PREDATOR_ENERGY_FROM_PREY * efficiency,
            PREDATOR_MAX_ENERGY,
        ).astype(np.uint8)

        new_species [predators[eating, 0], predators[eating, 1]] = 0
        new_species [targets [eating, 0], targets [eating, 1]]   = 2
        new_energy  [targets [eating, 0], targets [eating, 1]]   = energy_gained
        new_energy  [predators[eating, 0], predators[eating, 1]] = 0
        new_infected[targets [eating, 0], targets [eating, 1]]   = 0
        new_genome  [targets [eating, 0], targets [eating, 1]]   = genome[predators[eating, 0], predators[eating, 1]]
        new_genome  [predators[eating, 0], predators[eating, 1]] = 0

    # Mover a celda vacía
    if np.any(moving):
        new_species [predators[moving, 0], predators[moving, 1]] = 0
        new_species [targets [moving, 0], targets [moving, 1]]   = 2
        new_energy  [targets [moving, 0], targets [moving, 1]]   = energy[predators[moving, 0], predators[moving, 1]]
        new_energy  [predators[moving, 0], predators[moving, 1]] = 0
        new_genome  [targets [moving, 0], targets [moving, 1]]   = genome[predators[moving, 0], predators[moving, 1]]
        new_genome  [predators[moving, 0], predators[moving, 1]] = 0

    # Costo metabólico para todos los depredadores vivos
    alive_pred = new_species == 2
    new_energy[alive_pred] = np.maximum(
        new_energy[alive_pred].astype(np.int16) - PREDATOR_MOVE_COST, 0
    ).astype(np.uint8)

    starved = (new_species == 2) & (new_energy == 0)
    new_species[starved] = 0
    new_genome [starved] = 0

    return {**state, "species": new_species, "energy": new_energy, "infected": new_infected, "genome": new_genome}
