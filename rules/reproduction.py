import numpy as np
from config import (
    GRID_WIDTH, GRID_HEIGHT,
    INITIAL_ENERGY, PREDATOR_INITIAL_ENERGY, OMNI_INITIAL_ENERGY,
    N_GENES, GENOME_MIN, GENOME_MAX,
    GENE_REPRO_ENERGY, GENE_MUTATION_RATE,
    TEMP_REPRO_PENALTY, MATE_SEARCH_RADIUS,
)

_DIRECTIONS = np.array([[-1, 0], [1, 0], [0, -1], [0, 1]], dtype=np.int32)

# rejillas de índice estáticas (200×200) para lookup de vecinos sin loops
_ROWS, _COLS = np.mgrid[0:GRID_HEIGHT, 0:GRID_WIDTH]

# offsets dentro de MATE_SEARCH_RADIUS (excluyendo el propio origen), ordenados por distancia
_MATE_OFFSETS = sorted(
    (
        (dy, dx)
        for dy in range(-MATE_SEARCH_RADIUS, MATE_SEARCH_RADIUS + 1)
        for dx in range(-MATE_SEARCH_RADIUS, MATE_SEARCH_RADIUS + 1)
        if (dy, dx) != (0, 0) and dy * dy + dx * dx <= MATE_SEARCH_RADIUS ** 2
    ),
    key=lambda o: o[0] ** 2 + o[1] ** 2,
)


def apply(state):
    species  = state["species"]
    energy   = state["energy"]
    age      = state["age"]
    infected = state["infected"]
    genome   = state["genome"]
    gender   = state["gender"]
    terrain  = state.get("terrain")

    new_species  = species.copy()
    new_energy   = energy.copy()
    new_age      = age.copy()
    new_infected = infected.copy()
    new_genome   = genome.copy()
    new_gender   = gender.copy()

    repro_thresh = genome[:, :, GENE_REPRO_ENERGY].astype(np.float32)
    if "local_temperature" in state:
        repro_thresh = repro_thresh + np.abs(state["local_temperature"]) * TEMP_REPRO_PENALTY

    # --- Todas las especies: reproducción sexual con crossover ---
    for sp_id, init_energy in [(1, INITIAL_ENERGY), (2, PREDATOR_INITIAL_ENERGY), (3, INITIAL_ENERGY), (4, OMNI_INITIAL_ENERGY)]:
        fertile = (
            (new_species == sp_id) &
            (new_energy.astype(np.float32) >= repro_thresh) &
            (gender > 0)
        )

        # Buscar pareja de género opuesto dentro de MATE_SEARCH_RADIUS celdas
        partner_found  = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=bool)
        partner_genome = np.zeros((GRID_HEIGHT, GRID_WIDTH, N_GENES), dtype=np.float32)

        for dy, dx in _MATE_OFFSETS:
            ny = np.clip(_ROWS + dy, 0, GRID_HEIGHT - 1)
            nx = np.clip(_COLS + dx, 0, GRID_WIDTH  - 1)
            has_mate = (
                fertile & ~partner_found &
                fertile[ny, nx] &
                (gender[ny, nx] != gender) &
                (gender > 0) & (gender[ny, nx] > 0)
            )
            partner_found [has_mate] = True
            partner_genome[has_mate] = genome[ny[has_mate], nx[has_mate]]

        ready = fertile & partner_found
        parents = np.argwhere(ready)
        if len(parents) == 0:
            continue

        m       = len(parents)
        targets = parents + _DIRECTIONS[np.random.randint(0, 4, m)]
        targets[:, 0] = np.clip(targets[:, 0], 0, GRID_HEIGHT - 1)
        targets[:, 1] = np.clip(targets[:, 1], 0, GRID_WIDTH  - 1)

        can_birth = new_species[targets[:, 0], targets[:, 1]] == 0
        if terrain is not None:
            can_birth &= terrain[targets[:, 0], targets[:, 1]] != 2

        target_ids = targets[:, 0] * GRID_WIDTH + targets[:, 1]
        _, first_occ = np.unique(target_ids, return_index=True)
        no_conflict  = np.zeros(m, dtype=bool)
        no_conflict[first_occ] = True

        birthing = can_birth & no_conflict
        n_born = int(np.sum(birthing))
        if n_born == 0:
            continue

        new_species[targets[birthing, 0], targets[birthing, 1]] = sp_id
        new_energy [targets[birthing, 0], targets[birthing, 1]] = init_energy
        new_age    [targets[birthing, 0], targets[birthing, 1]] = 0
        new_energy [parents[birthing, 0], parents[birthing, 1]] = init_energy

        # género aleatorio 50/50 para el hijo
        child_gender = np.random.randint(1, 3, n_born, dtype=np.uint8)
        new_gender[targets[birthing, 0], targets[birthing, 1]] = child_gender

        # crossover uniforme por gen + mutación con tasa promedio de ambos padres
        pa_g = genome         [parents[birthing, 0], parents[birthing, 1]]
        pb_g = partner_genome [parents[birthing, 0], parents[birthing, 1]]
        cross_mask = np.random.random((n_born, N_GENES)) < 0.5
        child_g = np.where(cross_mask, pa_g, pb_g).astype(np.float32)
        avg_mut = (pa_g[:, GENE_MUTATION_RATE] + pb_g[:, GENE_MUTATION_RATE]) / 2.0
        noise   = (np.random.randn(n_born, N_GENES) * avg_mut[:, None]).astype(np.float32)
        child_g = np.clip(child_g + noise, GENOME_MIN, GENOME_MAX)
        new_genome[targets[birthing, 0], targets[birthing, 1]] = child_g

        # infección heredada del padre (herbívoros y omnívoros; depredador es inmune)
        if sp_id in (1, 3, 4):
            parent_inf = infected[parents[birthing, 0], parents[birthing, 1]]
            new_infected[targets[birthing, 0], targets[birthing, 1]] = parent_inf

    return {**state,
            "species":  new_species,
            "energy":   new_energy,
            "age":      new_age,
            "infected": new_infected,
            "genome":   new_genome,
            "gender":   new_gender}
