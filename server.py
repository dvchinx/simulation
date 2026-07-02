import asyncio
import base64
import json
import sys
import numpy as np
import websockets
from simulation import create_state, tick, build_render
from config import FPS, SPECIES_COLORS, GRID_WIDTH, GRID_HEIGHT, N_GENES, TERRITORY_RENDER_THRESHOLD, SEASON_PERIOD

clients = set()
sim_state = None


def _season_name(tick_count):
    phase = (tick_count % SEASON_PERIOD) / SEASON_PERIOD
    if phase < 0.25: return "Primavera"
    if phase < 0.50: return "Verano"
    if phase < 0.75: return "Otoño"
    return "Invierno"


def _mean_genes(mask):
    if not np.any(mask):
        return [0.0] * N_GENES
    return [round(float(v), 3) for v in sim_state["genome"][mask].mean(axis=0)]


def _stats():
    sp = sim_state["species"]
    tick_count = sim_state.get("tick_count", 0)
    stats = {
        "type":        "stats",
        "tick":        tick_count,
        "herb_a":      int(np.sum(sp == 1)),
        "predators":   int(np.sum(sp == 2)),
        "herb_b":      int(np.sum(sp == 3)),
        "omni":        int(np.sum(sp == 4)),
        "infected":    int(np.sum(sim_state["infected"] > 0)),
        "food":        int(np.sum((sim_state["food"] > 0) & (sp == 0))),
        "genome_a":    _mean_genes(sp == 1),
        "genome_p":    _mean_genes(sp == 2),
        "genome_b":    _mean_genes(sp == 3),
        "genome_o":    _mean_genes(sp == 4),
        "temperature": round(float(sim_state.get("global_temperature", 0.0)), 3),
        "season":      _season_name(tick_count),
    }
    if "territory" in sim_state:
        ter = sim_state["territory"]
        ter_max   = np.max(ter, axis=2)
        ter_which = np.argmax(ter, axis=2)
        strong = ter_max >= TERRITORY_RENDER_THRESHOLD
        stats["territory_a"] = int(np.sum(strong & (ter_which == 0)))
        stats["territory_p"] = int(np.sum(strong & (ter_which == 1)))
        stats["territory_b"] = int(np.sum(strong & (ter_which == 2)))
    return json.dumps(stats)


def _cell_info(r, c):
    sp  = int(sim_state["species"][r, c])
    names = {0: "Vacío", 1: "Herbívoro A", 2: "Depredador", 3: "Herbívoro B", 4: "Omnívoro"}
    info = {"type": "cell", "row": r, "col": c, "species": sp, "name": names.get(sp, "?")}
    if sp > 0:
        info["energy"]   = int(sim_state["energy"][r, c])
        info["age"]      = int(sim_state["age"][r, c])
        info["infected"] = bool(sim_state["infected"][r, c] > 0)
        if "gender" in sim_state:
            info["gender"] = {1: "♂", 2: "♀"}.get(int(sim_state["gender"][r, c]), "—")
        g = sim_state["genome"][r, c]
        info["genome"] = [round(float(v), 3) for v in g]
    return json.dumps(info)


async def simulation_loop():
    global sim_state, clients
    interval = 1.0 / FPS
    while True:
        sim_state = tick(sim_state)

        if clients:
            stats_msg = _stats()
            data = build_render(sim_state).tobytes()
            dead = set()
            for ws in clients.copy():
                try:
                    await ws.send(stats_msg)
                    await ws.send(data)
                except websockets.ConnectionClosed:
                    dead.add(ws)
            clients -= dead

        await asyncio.sleep(interval)


def _biome_frame_b64():
    """Construye el frame de heatmap de bioma (bioma + terreno superpuesto), base64."""
    biome_display = (sim_state["biome"] + 60).astype(np.uint8)
    terrain = sim_state["terrain"]
    biome_display[terrain == 1] = 30  # agua sobre bioma
    biome_display[terrain == 2] = 31  # roca
    biome_display[terrain == 3] = 32  # pantano
    return base64.b64encode(biome_display.tobytes()).decode()


async def handler(websocket):
    clients.add(websocket)
    try:
        await websocket.send(json.dumps({
            "type":   "init",
            "width":  GRID_WIDTH,
            "height": GRID_HEIGHT,
            "colors": {str(k): v for k, v in SPECIES_COLORS.items()},
            "biome":  _biome_frame_b64(),
        }))
        await websocket.send(_stats())
        await websocket.send(build_render(sim_state).tobytes())
        async for raw in websocket:
            try:
                msg = json.loads(raw)
                if msg.get("type") == "inspect":
                    r = int(msg["row"])
                    c = int(msg["col"])
                    if 0 <= r < GRID_HEIGHT and 0 <= c < GRID_WIDTH:
                        await websocket.send(_cell_info(r, c))
            except (json.JSONDecodeError, KeyError, ValueError):
                pass
    except websockets.ConnectionClosed:
        pass
    finally:
        clients.discard(websocket)


async def main():
    global sim_state
    sim_state = create_state()
    print(f"Simulación: {GRID_WIDTH}x{GRID_HEIGHT} grid, {FPS} FPS")
    print("WebSocket en ws://0.0.0.0:8765")
    async with websockets.serve(handler, "0.0.0.0", 8765):
        await simulation_loop()


if __name__ == "__main__":
    if "--reset" in sys.argv:
        print("Reiniciando simulación desde cero...")
    asyncio.run(main())
