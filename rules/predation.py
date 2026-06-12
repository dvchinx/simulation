import numpy as np
from config import (
    GRID_WIDTH, GRID_HEIGHT,
    PREDATOR_MOVE_COST, PREDATOR_MAX_ENERGY, PREDATOR_ENERGY_FROM_PREY,
    PREDATOR_VISION_RANGE,
)

_DIRECTIONS = np.array([[-1, 0], [1, 0], [0, -1], [0, 1]], dtype=np.int32)


def apply(state):
    species = state["species"]
    energy = state["energy"]

    predators = np.argwhere(species == 2)
    if len(predators) == 0:
        return state

    n = len(predators)
    prey = (species == 1) | (species == 3)

    # --- puntuación por dirección: 1/distancia a la presa más cercana ---
    # shape (n, 4): una puntuación por depredador por dirección
    dir_scores = np.zeros((n, 4), dtype=np.float32)

    for d_idx in range(4):
        dy, dx = _DIRECTIONS[d_idx]
        for dist in range(1, PREDATOR_VISION_RANGE + 1):
            look_y = np.clip(predators[:, 0] + dy * dist, 0, GRID_HEIGHT - 1)
            look_x = np.clip(predators[:, 1] + dx * dist, 0, GRID_WIDTH - 1)
            # solo actualizar los que aún no encontraron presa en esta dirección
            unset = dir_scores[:, d_idx] == 0
            found = unset & prey[look_y, look_x]
            dir_scores[found, d_idx] = 1.0 / dist

    # ruido mínimo para romper empates aleatoriamente
    dir_scores += np.random.uniform(0, 1e-4, dir_scores.shape)

    # si hay presa visible → mejor dirección; si no → dirección aleatoria
    no_prey_visible = np.all(dir_scores <= 1e-4, axis=1)
    best_dir = np.argmax(dir_scores, axis=1)
    random_dir = np.random.randint(0, 4, n)
    chosen = np.where(no_prey_visible, random_dir, best_dir)

    targets = predators + _DIRECTIONS[chosen]
    targets[:, 0] = np.clip(targets[:, 0], 0, GRID_HEIGHT - 1)
    targets[:, 1] = np.clip(targets[:, 1], 0, GRID_WIDTH - 1)

    target_sp = species[targets[:, 0], targets[:, 1]]
    is_prey_target  = (target_sp == 1) | (target_sp == 3)
    is_empty_target = target_sp == 0

    # resolver conflictos: primer depredador en índice gana la celda
    target_ids = targets[:, 0] * GRID_WIDTH + targets[:, 1]
    _, first_occ = np.unique(target_ids, return_index=True)
    no_conflict = np.zeros(n, dtype=bool)
    no_conflict[first_occ] = True

    eating = is_prey_target  & no_conflict
    moving = is_empty_target & no_conflict

    new_species = species.copy()
    new_energy = energy.copy()
    new_infected = state["infected"].copy()

    # comer: depredador se mueve a la celda de la presa
    new_species[predators[eating, 0], predators[eating, 1]] = 0
    new_species[targets[eating, 0], targets[eating, 1]] = 2
    new_energy[targets[eating, 0], targets[eating, 1]] = np.minimum(
        energy[predators[eating, 0], predators[eating, 1]].astype(np.int16) + PREDATOR_ENERGY_FROM_PREY,
        PREDATOR_MAX_ENERGY,
    ).astype(np.uint8)
    new_energy[predators[eating, 0], predators[eating, 1]] = 0
    new_infected[targets[eating, 0], targets[eating, 1]] = 0

    # mover a celda vacía
    new_species[predators[moving, 0], predators[moving, 1]] = 0
    new_species[targets[moving, 0], targets[moving, 1]] = 2
    new_energy[targets[moving, 0], targets[moving, 1]] = energy[predators[moving, 0], predators[moving, 1]]
    new_energy[predators[moving, 0], predators[moving, 1]] = 0

    # costo metabólico para todos los depredadores vivos
    alive_pred = new_species == 2
    new_energy[alive_pred] = np.maximum(
        new_energy[alive_pred].astype(np.int16) - PREDATOR_MOVE_COST, 0
    ).astype(np.uint8)

    # muerte por inanición
    starved = (new_species == 2) & (new_energy == 0)
    new_species[starved] = 0

    return {**state, "species": new_species, "energy": new_energy, "infected": new_infected}
