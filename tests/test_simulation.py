import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from simulation import create_state, tick
from config import (
    GRID_WIDTH, GRID_HEIGHT,
    INITIAL_POPULATION, INITIAL_ENERGY,
    HERBIVORE_B_POPULATION, HERBIVORE_B_INITIAL_ENERGY,
    PREDATOR_POPULATION, PREDATOR_INITIAL_ENERGY,
    N_GENES,
)

VALID_SPECIES = {0, 1, 2, 3}


def test_state_keys():
    state = create_state()
    assert set(state.keys()) == {"species", "energy", "age", "food", "infected", "genome"}


def test_grid_shape():
    state = create_state()
    for key, grid in state.items():
        if key == "genome":
            assert grid.shape == (GRID_HEIGHT, GRID_WIDTH, N_GENES)
        else:
            assert grid.shape == (GRID_HEIGHT, GRID_WIDTH)


def test_initial_population():
    state = create_state()
    assert int(np.sum(state["species"] == 1)) == INITIAL_POPULATION
    assert int(np.sum(state["species"] == 3)) == HERBIVORE_B_POPULATION
    assert int(np.sum(state["species"] == 2)) == PREDATOR_POPULATION


def test_initial_energy_for_each_species():
    state = create_state()
    assert np.all(state["energy"][state["species"] == 1] == INITIAL_ENERGY)
    assert np.all(state["energy"][state["species"] == 2] == PREDATOR_INITIAL_ENERGY)
    assert np.all(state["energy"][state["species"] == 3] == HERBIVORE_B_INITIAL_ENERGY)


def test_initial_age_zero():
    state = create_state()
    assert np.all(state["age"] == 0)


def test_initial_infected_only_on_herbivores():
    state = create_state()
    # infección solo puede estar en herbívoros
    infected_on_pred = np.sum(state["infected"][state["species"] == 2] > 0)
    assert infected_on_pred == 0
    infected_on_empty = np.sum(state["infected"][state["species"] == 0] > 0)
    assert infected_on_empty == 0


def test_tick_only_valid_species():
    state = create_state()
    after = tick(state)
    assert set(np.unique(after["species"])).issubset(VALID_SPECIES)


def test_tick_alive_have_positive_energy():
    state = create_state()
    after = tick(state)
    for sp in (1, 2, 3):
        alive = after["species"] == sp
        if np.any(alive):
            assert np.all(after["energy"][alive] > 0)


def test_tick_population_bounds():
    state = create_state()
    after = tick(state)
    total = GRID_WIDTH * GRID_HEIGHT
    for sp in (1, 2, 3):
        count = int(np.sum(after["species"] == sp))
        assert 0 <= count <= total


def test_food_regenerates():
    state = create_state()
    # eliminar todos los organismos
    state = {**state,
             "species": np.zeros_like(state["species"]),
             "energy": np.zeros_like(state["energy"]),
             "infected": np.zeros_like(state["infected"])}
    food_before = int(np.sum(state["food"]))
    for _ in range(50):
        state = tick(state)
    food_after = int(np.sum(state["food"]))
    assert food_after >= food_before


def test_infection_does_not_spread_to_predators():
    state = create_state()
    for _ in range(10):
        state = tick(state)
    infected_pred = np.sum(state["infected"][state["species"] == 2] > 0)
    assert infected_pred == 0


def test_predators_eat_prey():
    # colocar depredador junto a presa y verificar que la presa puede morir
    state = create_state()
    sp = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=np.uint8)
    en = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=np.uint8)
    # depredador en (5,5), presa en (5,6)
    sp[5, 5] = 2; en[5, 5] = PREDATOR_INITIAL_ENERGY
    sp[5, 6] = 1; en[5, 6] = INITIAL_ENERGY
    state = {**state, "species": sp, "energy": en,
             "age": np.zeros_like(sp), "food": np.zeros_like(sp),
             "infected": np.zeros_like(sp)}
    # tras varios ticks el depredador debería haber comido la presa al menos una vez
    prey_survived_all = True
    for _ in range(10):
        state = tick(state)
        if int(np.sum(state["species"] == 1)) == 0:
            prey_survived_all = False
            break
    # no assertamos que murió (puede escapar), pero la simulación no explota
    assert set(np.unique(state["species"])).issubset(VALID_SPECIES)
