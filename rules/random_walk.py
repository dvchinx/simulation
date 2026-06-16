import numpy as np
from config import (
    GRID_WIDTH, GRID_HEIGHT, MOVE_ENERGY_COST,
    GENE_SPEED, GENE_VISION,
    PHEROMONE_HERB_ATTRACTION,
    TERRITORY_ATTRACTION, TERRITORY_FEAR_WEIGHT,
    TEMP_SPEED_FACTOR,
    TERRAIN_WATER_COST, TERRAIN_SWAMP_COST,
    NUTRIENT_CHEMOTAXIS,
)

_DIRECTIONS = np.array([[-1, 0], [1, 0], [0, -1], [0, 1]], dtype=np.int32)
# Multiplicadores de costo metabólico por tipo de terreno [libre, agua, roca, pantano]
_TERRAIN_COST = np.array([1.0, TERRAIN_WATER_COST, 1.0, TERRAIN_SWAMP_COST], dtype=np.float32)


def apply(state):
    species  = state["species"]
    energy   = state["energy"]
    infected = state["infected"]
    genome   = state["genome"]
    food     = state["food"]
    terrain  = state.get("terrain")

    positions = np.argwhere((species == 1) | (species == 3))
    if len(positions) == 0:
        return state

    n           = len(positions)
    species_ids = species[positions[:, 0], positions[:, 1]]
    is_a        = species_ids == 1
    is_b        = species_ids == 3

    herb_speed  = genome[positions[:, 0], positions[:, 1], GENE_SPEED]
    herb_vision = np.round(genome[positions[:, 0], positions[:, 1], GENE_VISION]).astype(np.int32)
    max_vision  = int(herb_vision.max()) if n > 0 else 1

    # --- Puntuación base: comida visible (quimiotaxis primaria) ---
    dir_scores = np.zeros((n, 4), dtype=np.float32)
    for d_idx in range(4):
        dy, dx = _DIRECTIONS[d_idx]
        for dist in range(1, max_vision + 1):
            look_y = np.clip(positions[:, 0] + dy * dist, 0, GRID_HEIGHT - 1)
            look_x = np.clip(positions[:, 1] + dx * dist, 0, GRID_WIDTH - 1)
            within = herb_vision >= dist
            unset  = dir_scores[:, d_idx] == 0
            found  = unset & within & (food[look_y, look_x] > 0)
            dir_scores[found, d_idx] = 1.0 / dist

    # --- Fase 5: gradiente de nutriente difundido (quimiotaxis de largo alcance) ---
    if "nutrient" in state:
        nu = state["nutrient"]
        for d_idx in range(4):
            dy, dx = _DIRECTIONS[d_idx]
            ny = np.clip(positions[:, 0] + dy, 0, GRID_HEIGHT - 1)
            nx = np.clip(positions[:, 1] + dx, 0, GRID_WIDTH - 1)
            dir_scores[:, d_idx] += NUTRIENT_CHEMOTAXIS * nu[ny, nx]

    # --- Fase 4: feromonas ---
    if "pheromone" in state:
        ph = state["pheromone"]
        for d_idx in range(4):
            dy, dx = _DIRECTIONS[d_idx]
            ny = np.clip(positions[:, 0] + dy, 0, GRID_HEIGHT - 1)
            nx = np.clip(positions[:, 1] + dx, 0, GRID_WIDTH - 1)
            ph_score = np.where(is_a, ph[ny, nx, 0], np.where(is_b, ph[ny, nx, 2], 0.0))
            dir_scores[:, d_idx] += PHEROMONE_HERB_ATTRACTION * ph_score

    # --- Fase 4: cardumen ---
    if "flock_a" in state and "flock_b" in state:
        fa = state["flock_a"]
        fb = state["flock_b"]
        for d_idx in range(4):
            sa = fa[positions[:, 0], positions[:, 1], d_idx]
            sb = fb[positions[:, 0], positions[:, 1], d_idx]
            dir_scores[:, d_idx] += np.where(is_a, sa, sb)

    # --- Fase 4: territorio ---
    if "territory" in state:
        ter = state["territory"]
        for d_idx in range(4):
            dy, dx = _DIRECTIONS[d_idx]
            ny = np.clip(positions[:, 0] + dy, 0, GRID_HEIGHT - 1)
            nx = np.clip(positions[:, 1] + dx, 0, GRID_WIDTH - 1)
            own_ter  = np.where(is_a, ter[ny, nx, 0], np.where(is_b, ter[ny, nx, 2], 0.0))
            pred_ter = ter[ny, nx, 1]
            dir_scores[:, d_idx] += TERRITORY_ATTRACTION * own_ter
            dir_scores[:, d_idx] -= TERRITORY_FEAR_WEIGHT * pred_ter

    # Ruido de desempate y dirección elegida
    dir_scores += np.random.uniform(0, 1e-4, dir_scores.shape)
    no_preference = np.all(dir_scores <= 1e-4, axis=1)
    best_dir      = np.argmax(dir_scores, axis=1)
    random_dir    = np.random.randint(0, 4, n)
    chosen        = np.where(no_preference, random_dir, best_dir)

    targets = positions + _DIRECTIONS[chosen]
    targets[:, 0] = np.clip(targets[:, 0], 0, GRID_HEIGHT - 1)
    targets[:, 1] = np.clip(targets[:, 1], 0, GRID_WIDTH - 1)

    # --- Fase 5: temperatura reduce probabilidad de movimiento ---
    if "local_temperature" in state:
        temp_abs = np.abs(state["local_temperature"][positions[:, 0], positions[:, 1]])
        speed_modifier = np.maximum(0.2, 1.0 - temp_abs * TEMP_SPEED_FACTOR)
        effective_speed = np.minimum(herb_speed * speed_modifier, 1.0)
    else:
        effective_speed = herb_speed

    # --- Fase 5: terreno bloquea roca; el resto es transitable ---
    attempting = np.random.random(n) < effective_speed
    can_reach  = species[targets[:, 0], targets[:, 1]] == 0
    if terrain is not None:
        can_reach &= terrain[targets[:, 0], targets[:, 1]] != 2  # roca = infranqueable

    valid = attempting & can_reach

    # Resolución de conflictos (primer llegado)
    no_conflict = np.zeros(n, dtype=bool)
    valid_idx   = np.where(valid)[0]
    if len(valid_idx) > 0:
        t_ids = targets[valid_idx, 0] * GRID_WIDTH + targets[valid_idx, 1]
        _, first = np.unique(t_ids, return_index=True)
        no_conflict[valid_idx[first]] = True

    moving = valid & no_conflict

    new_species  = species.copy()
    new_energy   = energy.copy()
    new_infected = infected.copy()
    new_genome   = genome.copy()

    new_species [positions[moving, 0], positions[moving, 1]] = 0
    new_species [targets [moving, 0], targets [moving, 1]]   = species_ids[moving]
    new_energy  [targets [moving, 0], targets [moving, 1]]   = energy  [positions[moving, 0], positions[moving, 1]]
    new_energy  [positions[moving, 0], positions[moving, 1]] = 0
    new_infected[targets [moving, 0], targets [moving, 1]]   = infected[positions[moving, 0], positions[moving, 1]]
    new_infected[positions[moving, 0], positions[moving, 1]] = 0
    new_genome  [targets [moving, 0], targets [moving, 1]]   = genome  [positions[moving, 0], positions[moving, 1]]
    new_genome  [positions[moving, 0], positions[moving, 1]] = 0

    # --- Costo metabólico con modificador de terreno por bioma ---
    alive = (new_species == 1) | (new_species == 3)
    if np.any(alive):
        base_cost = np.maximum(
            np.round(MOVE_ENERGY_COST * new_genome[:, :, GENE_SPEED]).astype(np.int16), 1
        )
        if terrain is not None:
            terrain_mult = _TERRAIN_COST[terrain]  # (H, W) float32
            cost = np.maximum(np.round(base_cost.astype(np.float32) * terrain_mult).astype(np.int16), 1)
        else:
            cost = base_cost
        new_energy[alive] = np.maximum(
            new_energy[alive].astype(np.int16) - cost[alive], 0
        ).astype(np.uint8)

    starved = alive & (new_energy == 0)
    new_species [starved] = 0
    new_infected[starved] = 0
    new_genome  [starved] = 0

    return {**state, "species": new_species, "energy": new_energy,
            "infected": new_infected, "genome": new_genome}
