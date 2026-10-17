"""Movimiento y caza compartidos por depredador y omnívoro."""
import numpy as np
from config import GRID_WIDTH, GRID_HEIGHT, GENE_VISION, GENE_FOOD_EFFICIENCY
from rules.common import (
    DIRECTIONS, TERRAIN_ROCK, clip_positions, first_claims, scan_directions,
    copy_layers, move, metabolic_cost, pay_and_starve,
)

def hunt(state, *, species_id, prey_ids, prey_score, energy_from_prey,
         max_energy, move_cost, flock_key, food_score=None, pheromone_weight=0.0):
    species = state["species"]
    hunters = np.argwhere(species == species_id)
    if len(hunters) == 0:
        return state

    genome  = state["genome"]
    terrain = state.get("terrain")
    hy, hx  = hunters[:, 0], hunters[:, 1]
    is_prey = np.isin(species, prey_ids)

    vision = np.round(genome[hy, hx, GENE_VISION]).astype(np.int32)
    targets_by_priority = [(is_prey, prey_score)]
    if food_score is not None:
        targets_by_priority.append((state["food"] > 0, food_score))
    dir_scores = scan_directions(hunters, vision, targets_by_priority)

    if pheromone_weight and "pheromone" in state:
        prey_ph = state["pheromone"][:, :, 0] + state["pheromone"][:, :, 2]
        for d_idx, (dy, dx) in enumerate(DIRECTIONS):
            ny = np.clip(hy + dy, 0, GRID_HEIGHT - 1)
            nx = np.clip(hx + dx, 0, GRID_WIDTH - 1)
            dir_scores[:, d_idx] += pheromone_weight * prey_ph[ny, nx]

    # Cohesión de grupo: facilita encontrar pareja
    if flock_key in state:
        dir_scores += state[flock_key][hy, hx]

    dir_scores += np.random.uniform(0, 1e-4, dir_scores.shape)
    chosen  = np.argmax(dir_scores, axis=1)
    targets = clip_positions(hunters + DIRECTIONS[chosen], GRID_HEIGHT, GRID_WIDTH)

    target_sp = species[targets[:, 0], targets[:, 1]]
    eating = np.isin(target_sp, prey_ids)
    empty  = target_sp == 0
    if terrain is not None:
        empty &= terrain[targets[:, 0], targets[:, 1]] != TERRAIN_ROCK

    won = first_claims(targets[:, 0] * GRID_WIDTH + targets[:, 1], eating | empty)
    eating &= won
    moving  = (eating | empty) & won

    layers = copy_layers(state)
    if np.any(eating):
        efficiency = genome[hy[eating], hx[eating], GENE_FOOD_EFFICIENCY]
        fed = np.minimum(
            layers["energy"][hy[eating], hx[eating]].astype(np.float32)
            + energy_from_prey * efficiency,
            max_energy,
        ).astype(np.uint8)
        layers["energy"][hy[eating], hx[eating]] = fed

    # La presa comida queda sobrescrita por el cazador (con su propia infección)
    move(layers, hunters[moving], targets[moving])

    alive = layers["species"] == species_id
    pay_and_starve(layers, alive, metabolic_cost(move_cost, terrain))

    return {**state, **layers}
