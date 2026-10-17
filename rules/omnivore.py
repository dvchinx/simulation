from config import OMNI_MOVE_COST, OMNI_MAX_ENERGY, OMNI_ENERGY_FROM_PREY
from rules.hunting import hunt


def apply(state):
    # Dieta mixta: prioriza herbívoros (1.2/dist) sobre pasto (0.8/dist).
    # El pasto lo come en rules/food.py al pisarlo.
    return hunt(
        state,
        species_id=4,
        prey_ids=(1, 3),
        prey_score=1.2,
        food_score=0.8,
        energy_from_prey=OMNI_ENERGY_FROM_PREY,
        max_energy=OMNI_MAX_ENERGY,
        move_cost=OMNI_MOVE_COST,
        flock_key="flock_omni",
    )
