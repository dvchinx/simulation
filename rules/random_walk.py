import numpy as np
from config import (
    GRID_WIDTH, GRID_HEIGHT, MOVE_ENERGY_COST,
    GENE_SPEED, GENE_VISION,
    PHEROMONE_HERB_ATTRACTION,
    TERRITORY_ATTRACTION, TERRITORY_FEAR_WEIGHT,
    TEMP_SPEED_FACTOR,
    NUTRIENT_CHEMOTAXIS,
)
from rules.common import (
    DIRECTIONS, TERRAIN_ROCK, clip_positions, first_claims, scan_directions,
    copy_layers, move, metabolic_cost, pay_and_starve,
)


def apply(state):
    species  = state["species"]
    genome   = state["genome"]
    food     = state["food"]
    terrain  = state.get("terrain")

    positions = np.argwhere((species == 1) | (species == 3))
    if len(positions) == 0:
        return state

    n           = len(positions)
    py, px      = positions[:, 0], positions[:, 1]
    species_ids = species[py, px]
    is_a        = species_ids == 1

    herb_speed  = genome[py, px, GENE_SPEED]
    herb_vision = np.round(genome[py, px, GENE_VISION]).astype(np.int32)

    # --- Puntuación base: comida visible (quimiotaxis primaria) ---
    dir_scores = scan_directions(positions, herb_vision, [(food > 0, 1.0)])

    nutrient  = state.get("nutrient")
    pheromone = state.get("pheromone")
    territory = state.get("territory")
    own_layer = np.where(is_a, 0, 2)  # capa propia en feromona/territorio

    # Señales locales en la celda vecina de cada dirección
    for d_idx, (dy, dx) in enumerate(DIRECTIONS):
        ny = np.clip(py + dy, 0, GRID_HEIGHT - 1)
        nx = np.clip(px + dx, 0, GRID_WIDTH - 1)
        if nutrient is not None:   # Fase 5: gradiente de nutriente (largo alcance)
            dir_scores[:, d_idx] += NUTRIENT_CHEMOTAXIS * nutrient[ny, nx]
        if pheromone is not None:  # Fase 4: rastro propio de la especie
            dir_scores[:, d_idx] += PHEROMONE_HERB_ATTRACTION * pheromone[ny, nx, own_layer]
        if territory is not None:  # Fase 4: atracción al propio territorio, miedo al del depredador
            dir_scores[:, d_idx] += TERRITORY_ATTRACTION * territory[ny, nx, own_layer]
            dir_scores[:, d_idx] -= TERRITORY_FEAR_WEIGHT * territory[ny, nx, 1]

    # --- Fase 4: cardumen ---
    if "flock_a" in state and "flock_b" in state:
        dir_scores += np.where(is_a[:, None], state["flock_a"][py, px], state["flock_b"][py, px])

    # Ruido de desempate y dirección elegida
    dir_scores += np.random.uniform(0, 1e-4, dir_scores.shape)
    no_preference = np.all(dir_scores <= 1e-4, axis=1)
    best_dir      = np.argmax(dir_scores, axis=1)
    random_dir    = np.random.randint(0, 4, n)
    chosen        = np.where(no_preference, random_dir, best_dir)

    targets = clip_positions(positions + DIRECTIONS[chosen], GRID_HEIGHT, GRID_WIDTH)

    # --- Fase 5: temperatura reduce probabilidad de movimiento ---
    if "local_temperature" in state:
        temp_abs = np.abs(state["local_temperature"][py, px])
        speed_modifier = np.maximum(0.2, 1.0 - temp_abs * TEMP_SPEED_FACTOR)
        effective_speed = np.minimum(herb_speed * speed_modifier, 1.0)
    else:
        effective_speed = herb_speed

    # --- Fase 5: terreno bloquea roca; el resto es transitable ---
    attempting = np.random.random(n) < effective_speed
    can_reach  = species[targets[:, 0], targets[:, 1]] == 0
    if terrain is not None:
        can_reach &= terrain[targets[:, 0], targets[:, 1]] != TERRAIN_ROCK

    valid  = attempting & can_reach
    moving = valid & first_claims(targets[:, 0] * GRID_WIDTH + targets[:, 1], valid)

    layers = copy_layers(state)
    move(layers, positions[moving], targets[moving])

    # --- Costo metabólico: proporcional al gen de velocidad y al terreno ---
    alive = (layers["species"] == 1) | (layers["species"] == 3)
    cost = metabolic_cost(MOVE_ENERGY_COST * layers["genome"][:, :, GENE_SPEED], terrain)
    pay_and_starve(layers, alive, cost)

    return {**state, **layers}
