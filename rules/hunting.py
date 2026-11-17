"""Movimiento y caza compartidos por depredador y omnívoro."""
import numpy as np
from config import (
    GRID_WIDTH, GRID_HEIGHT, GENE_VISION, GENE_FOOD_EFFICIENCY, HUNTER_SATIATION,
    PREY_FLEE_WEIGHT, PREY_SWITCHING,
)
from rules.common import (
    DIRECTIONS, OPPOSITE, TERRAIN_ROCK, clip_positions, first_claims, scan_directions,
    copy_layers, move, metabolic_cost, pay_and_starve,
)

def hunt(state, *, species_id, prey_ids, prey_score, energy_from_prey,
         max_energy, move_cost, flock_key, food_score=None, pheromone_weight=0.0,
         threat_ids=()):
    species = state["species"]
    hunters = np.argwhere(species == species_id)
    if len(hunters) == 0:
        return state

    genome  = state["genome"]
    terrain = state.get("terrain")
    hy, hx  = hunters[:, 0], hunters[:, 1]
    is_prey = np.isin(species, prey_ids)

    vision = np.round(genome[hy, hx, GENE_VISION]).astype(np.int32)
    # Un cazador saciado ni persigue ni mata presas: solo deambula (y el
    # omnívoro sigue buscando pasto).
    hungry = state["energy"][hy, hx] < HUNTER_SATIATION * max_energy
    dir_scores = np.zeros((len(hunters), 4), dtype=np.float32)
    if np.any(hungry):
        dir_scores[hungry] = scan_directions(hunters[hungry], vision[hungry], [(is_prey, prey_score)])
    if food_score is not None:
        food_scores = scan_directions(hunters, vision, [(state["food"] > 0, food_score)])
        dir_scores = np.maximum(dir_scores, food_scores)

    # Huida de sus propios depredadores (el omnívoro escapa del depredador)
    if threat_ids and PREY_FLEE_WEIGHT:
        threat = scan_directions(hunters, vision, [(np.isin(species, threat_ids), 1.0)])
        dir_scores += PREY_FLEE_WEIGHT * (threat[:, OPPOSITE] - threat)

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
    eating = np.isin(target_sp, prey_ids) & hungry
    empty  = target_sp == 0
    if terrain is not None:
        empty &= terrain[targets[:, 0], targets[:, 1]] != TERRAIN_ROCK

    won = first_claims(targets[:, 0] * GRID_WIDTH + targets[:, 1], eating | empty)
    eating &= won
    # Cambio de presa (imagen de búsqueda): el cazador captura bien a la presa
    # común y mal a la rara. La probabilidad de captura de cada especie escala
    # con su proporción entre las presas; con k especies en igual proporción
    # vale 1. Da refugio a la especie que escasea y evita que la abundante
    # sostenga cazadores que extingan a la otra (competencia aparente).
    # Si falla, el cazador se queda en su celda.
    if PREY_SWITCHING and np.any(eating):
        counts = np.array([np.count_nonzero(species == p) for p in prey_ids], dtype=np.float32)
        share = counts / max(counts.sum(), 1.0)
        p_by_prey = np.minimum(1.0, PREY_SWITCHING * len(prey_ids) * share)
        p_capture = np.ones(len(hunters), dtype=np.float32)
        for prey_id, p in zip(prey_ids, p_by_prey):
            p_capture[target_sp == prey_id] = p
        eating &= np.random.random(len(hunters)) < p_capture
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
    pay_and_starve(layers, alive, metabolic_cost(move_cost, terrain, layers["genome"]))

    return {**state, **layers}
