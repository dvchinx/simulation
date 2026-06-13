import numpy as np
from config import MAX_AGE, PREDATOR_MAX_AGE


def apply(state):
    species  = state["species"].copy()
    age      = state["age"].copy()
    infected = state["infected"].copy()
    genome   = state["genome"].copy()

    alive = species > 0
    age[alive] = np.minimum(age[alive].astype(np.int16) + 1, 255).astype(np.uint8)

    too_old = (
        ((species == 1) & (age >= MAX_AGE)) |
        ((species == 2) & (age >= PREDATOR_MAX_AGE)) |
        ((species == 3) & (age >= MAX_AGE))
    )
    species [too_old] = 0
    age     [too_old] = 0
    infected[too_old] = 0
    genome  [too_old] = 0

    return {**state, "species": species, "age": age, "infected": infected, "genome": genome}
