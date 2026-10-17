import numpy as np
from config import (
    GRID_WIDTH, GRID_HEIGHT,
    SPECIES, N_GENES, GENOME_MIN, GENOME_MAX,
    GENE_REPRO_ENERGY, GENE_MUTATION_RATE,
    TEMP_REPRO_PENALTY, MATE_SEARCH_RADIUS_BY_SPECIES,
)
from rules.common import DIRECTIONS, TERRAIN_ROCK, clip_positions, first_claims


def _mate_offsets(radius):
    """Offsets dentro del radio (excluyendo el origen), ordenados por distancia."""
    offsets = [
        (dy, dx)
        for dy in range(-radius, radius + 1)
        for dx in range(-radius, radius + 1)
        if (dy, dx) != (0, 0) and dy * dy + dx * dx <= radius * radius
    ]
    return np.array(sorted(offsets, key=lambda o: o[0] ** 2 + o[1] ** 2), dtype=np.int32)


_MATE_OFFSETS = {sp: _mate_offsets(r) for sp, r in MATE_SEARCH_RADIUS_BY_SPECIES.items()}

def _find_partners(parents, parent_gender, fertile_gender, offsets):
    """Para cada progenitor fértil busca la pareja fértil de género opuesto más
    cercana dentro del radio de búsqueda. Trabaja sobre (n_fértiles, n_offsets)
    en vez de sobre la grilla completa.

    Devuelve (máscara de quién tiene pareja, posiciones de la pareja)."""
    ny = parents[:, 0, None] + offsets[None, :, 0]
    nx = parents[:, 1, None] + offsets[None, :, 1]
    inside = (ny >= 0) & (ny < GRID_HEIGHT) & (nx >= 0) & (nx < GRID_WIDTH)
    g = fertile_gender[np.clip(ny, 0, GRID_HEIGHT - 1), np.clip(nx, 0, GRID_WIDTH - 1)]
    match = inside & (g > 0) & (g != parent_gender[:, None])

    has_partner = match.any(axis=1)
    first = np.argmax(match, axis=1)  # offsets ordenados → pareja más cercana
    rows = np.arange(len(parents))
    partners = np.stack([ny[rows, first], nx[rows, first]], axis=1)
    return has_partner, partners


def apply(state):
    species  = state["species"]
    genome   = state["genome"]
    gender   = state["gender"]
    infected = state["infected"]
    terrain  = state.get("terrain")

    new_species  = species.copy()
    new_energy   = state["energy"].copy()
    new_age      = state["age"].copy()
    new_infected = infected.copy()
    new_genome   = genome.copy()
    new_gender   = gender.copy()

    # Umbral de reproducción individual (gen) + penalización por temperatura extrema
    repro_thresh = genome[:, :, GENE_REPRO_ENERGY]
    if "local_temperature" in state:
        repro_thresh = repro_thresh + np.abs(state["local_temperature"]) * TEMP_REPRO_PENALTY
    can_breed = (new_energy >= repro_thresh) & (gender > 0)

    # --- Todas las especies: reproducción sexual con crossover ---
    for sp_id, spec in SPECIES.items():
        init_energy = spec["initial_energy"]
        fertile = can_breed & (species == sp_id)
        parents = np.argwhere(fertile)
        if len(parents) < 2:
            continue

        fertile_gender = np.where(fertile, gender, 0)
        parent_gender  = gender[parents[:, 0], parents[:, 1]]
        has_partner, partners = _find_partners(parents, parent_gender, fertile_gender, _MATE_OFFSETS[sp_id])
        parents, partners = parents[has_partner], partners[has_partner]
        m = len(parents)
        if m == 0:
            continue

        # La cría nace en una celda adyacente aleatoria, libre y transitable
        targets = clip_positions(parents + DIRECTIONS[np.random.randint(0, 4, m)],
                                 GRID_HEIGHT, GRID_WIDTH)
        can_birth = new_species[targets[:, 0], targets[:, 1]] == 0
        if terrain is not None:
            can_birth &= terrain[targets[:, 0], targets[:, 1]] != TERRAIN_ROCK
        birthing = can_birth & first_claims(targets[:, 0] * GRID_WIDTH + targets[:, 1], can_birth)

        n_born = int(np.count_nonzero(birthing))
        if n_born == 0:
            continue
        parents, partners, targets = parents[birthing], partners[birthing], targets[birthing]
        ty, tx = targets[:, 0], targets[:, 1]

        # crossover uniforme por gen + mutación con tasa promedio de ambos padres
        pa_g = genome[parents[:, 0], parents[:, 1]]
        pb_g = genome[partners[:, 0], partners[:, 1]]
        child_g = np.where(np.random.random((n_born, N_GENES)) < 0.5, pa_g, pb_g)
        avg_mut = (pa_g[:, GENE_MUTATION_RATE] + pb_g[:, GENE_MUTATION_RATE]) / 2.0
        child_g = child_g + np.random.randn(n_born, N_GENES).astype(np.float32) * avg_mut[:, None]

        new_species [ty, tx] = sp_id
        new_energy  [ty, tx] = init_energy
        new_age     [ty, tx] = 0
        new_gender  [ty, tx] = np.random.randint(1, 3, n_born, dtype=np.uint8)
        new_genome  [ty, tx] = np.clip(child_g, GENOME_MIN, GENOME_MAX)
        # infección heredada del progenitor (el depredador nunca está infectado)
        new_infected[ty, tx] = infected[parents[:, 0], parents[:, 1]]
        new_energy  [parents[:, 0], parents[:, 1]] = init_energy

    return {**state,
            "species":  new_species,
            "energy":   new_energy,
            "age":      new_age,
            "infected": new_infected,
            "genome":   new_genome,
            "gender":   new_gender}
