import asyncio
import json
import sys
import numpy as np
import websockets
from simulation import create_state, tick, build_render
from config import FPS, SPECIES_COLORS, GRID_WIDTH, GRID_HEIGHT, N_GENES, TERRITORY_RENDER_THRESHOLD

clients = set()
sim_state = None
tick_count = 0


def _mean_genes(mask):
    if not np.any(mask):
        return [0.0] * N_GENES
    return [round(float(v), 3) for v in sim_state["genome"][mask].mean(axis=0)]


def _stats():
    sp = sim_state["species"]
    stats = {
        "type":      "stats",
        "tick":      tick_count,
        "herb_a":    int(np.sum(sp == 1)),
        "predators": int(np.sum(sp == 2)),
        "herb_b":    int(np.sum(sp == 3)),
        "infected":  int(np.sum(sim_state["infected"] > 0)),
        "food":      int(np.sum((sim_state["food"] > 0) & (sp == 0))),
        "genome_a":  _mean_genes(sp == 1),
        "genome_p":  _mean_genes(sp == 2),
        "genome_b":  _mean_genes(sp == 3),
    }
    # Fase 4: celdas con territorio dominante por especie
    if "territory" in sim_state:
        ter = sim_state["territory"]
        ter_max   = np.max(ter, axis=2)
        ter_which = np.argmax(ter, axis=2)
        strong = ter_max >= TERRITORY_RENDER_THRESHOLD
        stats["territory_a"] = int(np.sum(strong & (ter_which == 0)))
        stats["territory_p"] = int(np.sum(strong & (ter_which == 1)))
        stats["territory_b"] = int(np.sum(strong & (ter_which == 2)))
    return json.dumps(stats)


async def simulation_loop():
    global sim_state, tick_count, clients
    interval = 1.0 / FPS
    while True:
        sim_state = tick(sim_state)
        tick_count += 1

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


async def handler(websocket):
    clients.add(websocket)
    try:
        await websocket.send(json.dumps({
            "type":   "init",
            "width":  GRID_WIDTH,
            "height": GRID_HEIGHT,
            "colors": {str(k): v for k, v in SPECIES_COLORS.items()},
        }))
        await websocket.send(_stats())
        await websocket.send(build_render(sim_state).tobytes())
        async for _ in websocket:
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
