import numpy as np
from config import (
    GRID_WIDTH, GRID_HEIGHT,
    TERRAIN_SMOOTH_ITER, BIOME_SMOOTH_ITER,
    WATER_THRESHOLD, ROCK_THRESHOLD, SWAMP_MIN, SWAMP_MAX,
)

TERRAIN_FREE  = np.uint8(0)
TERRAIN_WATER = np.uint8(1)
TERRAIN_ROCK  = np.uint8(2)
TERRAIN_SWAMP = np.uint8(3)

BIOME_TEMPERATE = np.uint8(0)
BIOME_ARCTIC    = np.uint8(1)
BIOME_DESERT    = np.uint8(2)
BIOME_TROPICAL  = np.uint8(3)


def generate():
    H, W = GRID_HEIGHT, GRID_WIDTH

    # Terreno: ruido fino suavizado en patches
    noise_t = np.random.random((H, W)).astype(np.float32)
    smooth_t = _diffuse(noise_t, TERRAIN_SMOOTH_ITER)
    smooth_t = _normalize(smooth_t)

    terrain = np.zeros((H, W), dtype=np.uint8)
    terrain[smooth_t < WATER_THRESHOLD] = TERRAIN_WATER
    terrain[(smooth_t >= SWAMP_MIN) & (smooth_t < ROCK_THRESHOLD)] = TERRAIN_SWAMP
    terrain[smooth_t >= ROCK_THRESHOLD] = TERRAIN_ROCK

    # Biomas: ruido de escala mayor (patches más grandes)
    noise_b = np.random.random((H, W)).astype(np.float32)
    smooth_b = _diffuse(noise_b, BIOME_SMOOTH_ITER)
    smooth_b = _normalize(smooth_b)

    biome = np.zeros((H, W), dtype=np.uint8)  # 0 = templado
    biome[smooth_b < 0.25] = BIOME_ARCTIC
    biome[(smooth_b >= 0.50) & (smooth_b < 0.75)] = BIOME_DESERT
    biome[smooth_b >= 0.75] = BIOME_TROPICAL

    return terrain, biome


def _diffuse(arr, n):
    """Suavizado por promedio de vecinos cardinales repetido n veces (aproxima blur gaussiano)."""
    r = arr.copy()
    for _ in range(n):
        r = (r
             + np.roll(r,  1, axis=0)
             + np.roll(r, -1, axis=0)
             + np.roll(r,  1, axis=1)
             + np.roll(r, -1, axis=1)) / 5.0
    return r


def _normalize(arr):
    mn, mx = float(arr.min()), float(arr.max())
    if mx > mn:
        return (arr - mn) / (mx - mn)
    return arr
