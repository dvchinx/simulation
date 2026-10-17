import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from simulation import create_state, tick, build_render  # noqa: E402
from config import (  # noqa: E402
    GRID_WIDTH, GRID_HEIGHT, N_GENES, SPECIES, SPECIES_COLORS,
    INITIAL_POPULATION, HERBIVORE_B_POPULATION, PREDATOR_POPULATION, OMNI_POPULATION,
    GENE_REPRO_ENERGY, GENE_SPEED, MIGRATION_DELAY, MATE_SEARCH_RADIUS_BY_SPECIES,
)
from rules import aging, migration, predation, omnivore, random_walk, reproduction  # noqa: E402
from rules.common import ORGANISM_LAYERS, first_claims, neighbor_sum  # noqa: E402

VALID_SPECIES = {0, *SPECIES}
SHAPE = (GRID_HEIGHT, GRID_WIDTH)


@pytest.fixture(autouse=True)
def _seed():
    np.random.seed(1234)


def empty_world():
    """Estado real (terreno, capas) sin organismos, pasto ni terreno bloqueante."""
    state = create_state()
    for key in ORGANISM_LAYERS:
        state[key] = np.zeros_like(state[key])
    state["food"] = np.zeros_like(state["food"])
    state["terrain"] = np.zeros_like(state["terrain"])
    state["local_temperature"] = np.zeros(SHAPE, dtype=np.float32)
    return state


def place(state, sp, row, col, energy=None, gender=1, age=0, infected=0, **genes):
    spec = SPECIES[sp]
    state["species"][row, col] = sp
    state["energy"][row, col] = spec["initial_energy"] if energy is None else energy
    state["age"][row, col] = age
    state["gender"][row, col] = gender
    state["infected"][row, col] = infected
    genome = spec["genome"].copy()
    for idx, value in genes.items():
        genome[int(idx.removeprefix("g"))] = value
    state["genome"][row, col] = genome


# ---------------------------------------------------------------------------
# Estado inicial
# ---------------------------------------------------------------------------

def test_grid_shapes():
    state = create_state()
    for key in ORGANISM_LAYERS:
        expected = (*SHAPE, N_GENES) if key == "genome" else SHAPE
        assert state[key].shape == expected, key
    for key in ("pheromone", "territory"):
        assert state[key].shape == (*SHAPE, 3)
    for key in ("flock_a", "flock_b", "flock_pred", "flock_omni"):
        assert state[key].shape == (*SHAPE, 4)
    for key in ("food", "terrain", "biome", "biome_border", "nutrient", "fire", "flood"):
        assert state[key].shape == SHAPE


def test_initial_population_and_energy():
    state = create_state()
    expected = {1: INITIAL_POPULATION, 2: PREDATOR_POPULATION, 3: HERBIVORE_B_POPULATION, 4: OMNI_POPULATION}
    for sp, count in expected.items():
        mask = state["species"] == sp
        assert int(mask.sum()) == count
        assert np.all(state["energy"][mask] == SPECIES[sp]["initial_energy"])
        assert np.all(state["gender"][mask] > 0)


def test_initial_ages_are_staggered():
    state = create_state()
    for sp, spec in SPECIES.items():
        ages = state["age"][state["species"] == sp]
        assert ages.max() < spec["max_age"] // 2
        assert len(np.unique(ages)) > 5, "la cohorte fundadora no debe tener una sola edad"


def test_initial_infection_only_on_herbivores():
    state = create_state()
    infected_species = set(np.unique(state["species"][state["infected"] > 0]))
    assert infected_species <= {1, 3}


def test_no_organisms_on_rock():
    state = create_state()
    assert not np.any((state["terrain"] == 2) & (state["species"] > 0))


# ---------------------------------------------------------------------------
# Invariantes tras varios ticks
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def evolved_state():
    np.random.seed(7)
    state = create_state()
    for _ in range(40):
        state = tick(state)
    return state


def test_only_valid_species(evolved_state):
    assert set(np.unique(evolved_state["species"])) <= VALID_SPECIES


def test_alive_have_positive_energy(evolved_state):
    sp = evolved_state["species"]
    assert np.all(evolved_state["energy"][sp > 0] > 0)


def test_empty_cells_have_no_leftover_state(evolved_state):
    """Regresión: al morir o moverse, ninguna capa debe quedarse en la celda vacía."""
    empty = evolved_state["species"] == 0
    for key in ORGANISM_LAYERS:
        leftover = evolved_state[key][empty]
        assert not np.any(leftover), f"capa '{key}' con datos en celdas vacías"


def test_ages_within_species_limits(evolved_state):
    for sp, spec in SPECIES.items():
        ages = evolved_state["age"][evolved_state["species"] == sp]
        if len(ages):
            assert ages.max() < spec["max_age"]


def test_predators_never_infected(evolved_state):
    assert not np.any(evolved_state["infected"][evolved_state["species"] == 2])


def test_render_codes_have_colors(evolved_state):
    codes = set(np.unique(build_render(evolved_state)))
    assert codes <= set(SPECIES_COLORS), codes - set(SPECIES_COLORS)


# ---------------------------------------------------------------------------
# Reglas individuales
# ---------------------------------------------------------------------------

def test_moving_herbivore_keeps_its_age():
    """Regresión: la edad viajaba con la celda en lugar de con el organismo."""
    state = empty_world()
    place(state, 1, 100, 100, age=42, g0=1.0)  # velocidad 1 → siempre intenta moverse
    after = random_walk.apply(state)
    pos = np.argwhere(after["species"] == 1)
    assert len(pos) == 1
    r, c = pos[0]
    assert (r, c) != (100, 100)
    assert after["age"][r, c] == 42
    assert after["age"][100, 100] == 0


def test_moving_omnivore_keeps_infection():
    """Regresión: el omnívoro perdía la infección al moverse."""
    state = empty_world()
    place(state, 4, 50, 50, infected=1)
    after = omnivore.apply(state)
    pos = np.argwhere(after["species"] == 4)
    assert len(pos) == 1
    assert after["infected"][tuple(pos[0])] == 1


def test_predator_eats_adjacent_prey():
    state = empty_world()
    place(state, 2, 5, 5, energy=50)
    place(state, 1, 5, 6)
    after = predation.apply(state)
    assert after["species"][5, 6] == 2
    assert after["species"][5, 5] == 0
    assert np.count_nonzero(after["species"] == 1) == 0
    assert after["energy"][5, 6] > 50 - 2


def test_starving_organism_is_fully_removed():
    state = empty_world()
    place(state, 2, 10, 10, energy=1)
    after = predation.apply(state)
    assert not np.any(after["species"])
    for key in ORGANISM_LAYERS:
        assert not np.any(after[key]), key


def test_aging_kills_at_max_age():
    state = empty_world()
    max_age = SPECIES[1]["max_age"]
    place(state, 1, 20, 20, age=max_age - 1)
    place(state, 1, 30, 30, age=max_age - 2)
    after = aging.apply(state)
    assert after["species"][20, 20] == 0 and after["gender"][20, 20] == 0
    assert after["species"][30, 30] == 1 and after["age"][30, 30] == max_age - 1


def _fertile_pair(state, sp, distance, same_gender=False):
    energy = SPECIES[sp]["max_energy"]
    thresh = float(SPECIES[sp]["genome"][GENE_REPRO_ENERGY])
    assert energy >= thresh
    place(state, sp, 100, 100, energy=energy, gender=1)
    place(state, sp, 100, 100 + distance, energy=energy, gender=1 if same_gender else 2)


def test_reproduction_needs_opposite_gender():
    for same_gender, expect_birth in ((False, True), (True, False)):
        state = empty_world()
        _fertile_pair(state, 1, 1, same_gender=same_gender)
        after = reproduction.apply(state)
        born = int(np.count_nonzero(after["species"] == 1)) - 2
        assert (born > 0) == expect_birth


def test_newborn_has_fresh_state():
    state = empty_world()
    _fertile_pair(state, 1, 1)
    after = reproduction.apply(state)
    newborn = (after["species"] == 1) & (state["species"] == 0)
    assert np.any(newborn)
    assert np.all(after["age"][newborn] == 0)
    assert np.all(after["gender"][newborn] > 0)
    assert np.all(after["energy"][newborn] == SPECIES[1]["initial_energy"])


def test_mate_search_radius_is_per_species():
    distance = MATE_SEARCH_RADIUS_BY_SPECIES[2]
    assert distance > MATE_SEARCH_RADIUS_BY_SPECIES[1]
    for sp, expect_birth in ((2, True), (1, False)):
        state = empty_world()
        _fertile_pair(state, sp, distance)
        after = reproduction.apply(state)
        born = int(np.count_nonzero(after["species"] == sp)) - 2
        assert (born > 0) == expect_birth, sp


def test_migration_reintroduces_extinct_species():
    state = empty_world()
    place(state, 1, 10, 10)
    for t in range(MIGRATION_DELAY + 1):
        state = migration.apply({**state, "tick_count": t, "events": []})
    counts = np.bincount(state["species"].ravel(), minlength=5)
    assert counts[2] > 0 and counts[3] > 0 and counts[4] > 0
    assert any(e["kind"] == "migration" for e in state["events"])
    assert not np.any((state["terrain"] == 2) & (state["species"] > 0))


def test_food_regenerates():
    state = empty_world()
    food_before = int(np.sum(state["food"]))
    for _ in range(20):
        state = tick({**state, "extinct_since": {sp: 0 for sp in SPECIES}, "tick_count": 1})
    assert int(np.sum(state["food"])) > food_before


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def test_first_claims_picks_one_winner_per_target():
    targets = np.array([5, 5, 7, 5, 9, 7])
    won = first_claims(targets)
    assert won.sum() == 3
    assert sorted(targets[won]) == [5, 7, 9]


def test_first_claims_respects_candidates():
    targets = np.array([1, 1, 2])
    won = first_claims(targets, np.array([False, True, False]))
    assert won.tolist() == [False, True, False]


def test_neighbor_sum_does_not_wrap():
    a = np.zeros((4, 4), dtype=np.uint8)
    a[0, 0] = 1
    n = neighbor_sum(a)
    assert n[0, 1] == 1 and n[1, 0] == 1
    assert n[3, 0] == 0 and n[0, 3] == 0
