import numpy as np
from config import (
    FOOD_ENERGY_GAIN, FOOD_REGEN_RATE, GENE_FOOD_EFFICIENCY,
    BIOME_REGEN_MULT, TEMP_REGEN_FACTOR,
    NUTRIENT_REGEN_BOOST, OMNI_FOOD_EFFICIENCY,
    HERBIVORE_B_BIOME_MULT,
)


def apply(state):
    species = state["species"]
    energy  = state["energy"].copy()
    food    = state["food"].copy()
    genome  = state["genome"]
    biome   = state.get("biome")

    # Herbívoros comen pasto
    eating_herb = ((species == 1) | (species == 3)) & (food > 0)
    if np.any(eating_herb):
        efficiency = genome[eating_herb, GENE_FOOD_EFFICIENCY]
        # Herbívoro B tiene nicho distinto: mejor en biomas duros, peor en templado/tropical
        if biome is not None:
            is_b = species[eating_herb] == 3
            efficiency = np.where(is_b, efficiency * HERBIVORE_B_BIOME_MULT[biome[eating_herb]], efficiency)
        energy[eating_herb] = np.minimum(
            energy[eating_herb].astype(np.float32) + FOOD_ENERGY_GAIN * efficiency,
            255.0,
        ).astype(np.uint8)
    food[eating_herb] = 0

    # Omnívoro come pasto con menor eficiencia
    eating_omni = (species == 4) & (food > 0)
    if np.any(eating_omni):
        efficiency = genome[eating_omni, GENE_FOOD_EFFICIENCY] * OMNI_FOOD_EFFICIENCY
        energy[eating_omni] = np.minimum(
            energy[eating_omni].astype(np.float32) + FOOD_ENERGY_GAIN * efficiency,
            255.0,
        ).astype(np.uint8)
    food[eating_omni] = 0

    eating = eating_herb | eating_omni

    # Regeneración con modificadores de bioma, temperatura y nutriente
    regen_rate = np.full(food.shape, FOOD_REGEN_RATE, dtype=np.float32)

    if "biome" in state:
        regen_rate *= BIOME_REGEN_MULT[state["biome"]]

    if "local_temperature" in state:
        temp_factor = np.maximum(0.05, 1.0 - np.abs(state["local_temperature"]) * TEMP_REGEN_FACTOR)
        regen_rate *= temp_factor

    if "nutrient" in state:
        regen_rate += NUTRIENT_REGEN_BOOST * state["nutrient"]

    regen_rate = np.clip(regen_rate, 0.0, 0.95)

    regen_candidates = (species == 0) & (food == 0)
    if "terrain" in state:
        regen_candidates &= state["terrain"] != 2  # sin pasto en roca

    food[regen_candidates & (np.random.random(food.shape) < regen_rate)] = 1

    return {**state, "energy": energy, "food": food}
