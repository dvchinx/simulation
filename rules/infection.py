import numpy as np
from config import INFECTION_ENERGY_DRAIN, INFECTION_SPREAD_PROB, INFECTION_CLEAR_PROB


def apply(state):
    species = state["species"]
    energy = state["energy"].copy()
    infected = state["infected"].copy()

    susceptible = (species == 1) | (species == 3) | (species == 4)
    is_infected = infected > 0

    # drenar energía de los organismos infectados
    draining = susceptible & is_infected
    energy[draining] = np.maximum(
        energy[draining].astype(np.int16) - INFECTION_ENERGY_DRAIN, 0
    ).astype(np.uint8)

    # contar vecinos infectados (sin wrap-around: pad con ceros en los bordes)
    i_mask = is_infected.astype(np.float32)
    neighbor_count = (
        np.roll(i_mask,  1, axis=0) + np.roll(i_mask, -1, axis=0) +
        np.roll(i_mask,  1, axis=1) + np.roll(i_mask, -1, axis=1)
    )

    # propagar a organismos susceptibles sanos adyacentes a al menos un infectado
    can_catch = susceptible & ~is_infected & (neighbor_count > 0)
    infected[can_catch & (np.random.random(infected.shape) < INFECTION_SPREAD_PROB)] = 1

    # recuperación espontánea
    recovering = is_infected & susceptible & (np.random.random(infected.shape) < INFECTION_CLEAR_PROB)
    infected[recovering] = 0

    # limpiar infección en celdas sin organismo
    infected[species == 0] = 0

    return {**state, "energy": energy, "infected": infected}
