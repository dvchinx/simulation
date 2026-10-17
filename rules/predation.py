from config import (
    PREDATOR_MOVE_COST, PREDATOR_MAX_ENERGY, PREDATOR_ENERGY_FROM_PREY,
    PHEROMONE_PRED_ATTRACTION,
)
from rules.hunting import hunt


def apply(state):
    # El depredador caza a ambos herbívoros y al omnívoro, y rastrea la
    # feromona combinada de las presas cuando no las ve directamente.
    return hunt(
        state,
        species_id=2,
        prey_ids=(1, 3, 4),
        prey_score=1.0,
        energy_from_prey=PREDATOR_ENERGY_FROM_PREY,
        max_energy=PREDATOR_MAX_ENERGY,
        move_cost=PREDATOR_MOVE_COST,
        flock_key="flock_pred",
        pheromone_weight=PHEROMONE_PRED_ATTRACTION,
    )
