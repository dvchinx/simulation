"""Utilidades compartidas por las reglas: direcciones, desplazamientos sin wrap y
movimiento/muerte de organismos manteniendo sincronizadas todas sus capas."""
import numpy as np
from config import TERRAIN_WATER_COST, TERRAIN_SWAMP_COST, GENOME_MAX, GENE_VISION

# N, S, W, E — orden común a todas las reglas de movimiento
DIRECTIONS = np.array([[-1, 0], [1, 0], [0, -1], [0, 1]], dtype=np.int32)

TERRAIN_ROCK = 2
# Multiplicadores de costo metabólico por tipo de terreno [libre, agua, roca, pantano]
TERRAIN_COST = np.array([1.0, TERRAIN_WATER_COST, 1.0, TERRAIN_SWAMP_COST], dtype=np.float32)

# Capas que describen a un organismo y deben viajar con él al moverse
ORGANISM_LAYERS = ("species", "energy", "age", "infected", "genome", "gender")

MAX_VISION = int(GENOME_MAX[GENE_VISION])


def scan_directions(positions, vision, layers):
    """Para cada dirección puntúa el objetivo más cercano dentro de la visión con
    escala / distancia. `layers` es una lista (máscara, escala) en orden de
    prioridad para objetivos a la misma distancia."""
    height, width = layers[0][0].shape
    dir_scores = np.zeros((len(positions), 4), dtype=np.float32)
    max_vision = min(int(vision.max()), MAX_VISION)
    for d_idx, (dy, dx) in enumerate(DIRECTIONS):
        for dist in range(1, max_vision + 1):
            look_y = np.clip(positions[:, 0] + dy * dist, 0, height - 1)
            look_x = np.clip(positions[:, 1] + dx * dist, 0, width - 1)
            for mask, scale in layers:
                found = (dir_scores[:, d_idx] == 0) & (vision >= dist) & mask[look_y, look_x]
                dir_scores[found, d_idx] = scale / dist
    return dir_scores


def neighbor_sum(arr):
    """Suma de los 4 vecinos cardinales con bordes absorbentes (sin wrap)."""
    out = np.zeros_like(arr)
    out[1:]     += arr[:-1]
    out[:-1]    += arr[1:]
    out[:, 1:]  += arr[:, :-1]
    out[:, :-1] += arr[:, 1:]
    return out


def dominant_layer(layer):
    """(valor máximo, índice de capa) sobre el último eje de un array (H, W, k).
    Encadenar np.maximum es ~20× más rápido que layer.max(axis=2) para k pequeño."""
    return np.maximum.reduce([layer[..., i] for i in range(layer.shape[-1])]), layer.argmax(axis=-1)


def clip_positions(pos, height, width):
    pos[:, 0] = np.clip(pos[:, 0], 0, height - 1)
    pos[:, 1] = np.clip(pos[:, 1], 0, width - 1)
    return pos


def first_claims(target_ids, candidates=None):
    """Máscara de los candidatos que ganan su celda destino cuando varios apuntan
    a la misma. El orden se baraja para no favorecer sistemáticamente a los
    organismos de la esquina superior izquierda (orden de np.argwhere)."""
    n = len(target_ids)
    won = np.zeros(n, dtype=bool)
    idx = np.arange(n) if candidates is None else np.flatnonzero(candidates)
    if len(idx) == 0:
        return won
    idx = np.random.permutation(idx)
    _, first = np.unique(target_ids[idx], return_index=True)
    won[idx[first]] = True
    return won


def copy_layers(state):
    return {k: state[k].copy() for k in ORGANISM_LAYERS}


def move(layers, src, dst):
    """Mueve organismos de src a dst (arrays (n, 2)) en todas las capas.
    El destino se sobrescribe; usar también para comer a la presa en dst."""
    if len(src) == 0:
        return
    sy, sx = src[:, 0], src[:, 1]
    dy, dx = dst[:, 0], dst[:, 1]
    for arr in layers.values():
        vals = arr[sy, sx].copy()
        arr[sy, sx] = 0
        arr[dy, dx] = vals


def kill(layers, mask):
    """Vacía por completo las celdas indicadas (todas las capas a cero)."""
    for arr in layers.values():
        arr[mask] = 0


def metabolic_cost(base_cost, terrain):
    """Costo entero por celda (>= 1) aplicando el multiplicador de terreno."""
    base = np.asarray(base_cost, dtype=np.float32)
    if terrain is None:
        return np.maximum(np.round(base).astype(np.int16), 1)
    return np.maximum(np.round(base * TERRAIN_COST[terrain]).astype(np.int16), 1)


def pay_and_starve(layers, alive, cost):
    """Descuenta el costo metabólico a los vivos indicados y elimina a los que
    llegan a energía cero."""
    energy = layers["energy"]
    cost = np.broadcast_to(cost, energy.shape)
    energy[alive] = np.maximum(energy[alive].astype(np.int16) - cost[alive], 0).astype(np.uint8)
    kill(layers, alive & (energy == 0))
