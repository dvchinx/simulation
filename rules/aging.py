import numpy as np
from config import SPECIES
from rules.common import copy_layers, kill

# Edad máxima indexada por id de especie (0 = vacío)
_MAX_AGE_BY_SPECIES = np.array([255] + [SPECIES[sp]["max_age"] for sp in sorted(SPECIES)], dtype=np.uint8)


def apply(state):
    layers = copy_layers(state)
    species, age = layers["species"], layers["age"]

    alive = species > 0
    age[alive] = np.minimum(age[alive].astype(np.int16) + 1, 255).astype(np.uint8)

    kill(layers, alive & (age >= _MAX_AGE_BY_SPECIES[species]))
    return {**state, **layers}
