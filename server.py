import asyncio
import base64
import json
import logging
import os
import time
from collections import deque

import numpy as np
from websockets.asyncio.server import broadcast, serve
from websockets.exceptions import ConnectionClosed

from simulation import create_state, tick, build_render
from rules.common import dominant_layer
from config import (
    FPS as DEFAULT_FPS, SPECIES, SPECIES_COLORS, GRID_WIDTH, GRID_HEIGHT,
    N_GENES, GENE_NAMES, GENOME_MIN, GENOME_MAX,
    TERRITORY_RENDER_THRESHOLD, SEASON_PERIOD, FIRE_PERIOD, FLOOD_PERIOD,
)

HOST = os.environ.get("SIM_HOST", "0.0.0.0")
PORT = int(os.environ.get("SIM_PORT", "8765"))
FPS  = float(os.environ.get("SIM_FPS", DEFAULT_FPS))
SEED = os.environ.get("SIM_SEED")

HISTORY_LEN = 300                 # muestras de población enviadas a clientes nuevos
EVENTS_LEN  = 30                  # últimos eventos (fuego, inundación, migración)
MAX_CLIENT_BUFFER = 1 << 20       # bytes pendientes a partir de los cuales se salta un frame

TERRAIN_NAMES = ["Libre", "Agua", "Roca", "Pantano"]
BIOME_NAMES   = ["Templado", "Ártico", "Desierto", "Tropical"]
SEASONS       = ["Primavera", "Verano", "Otoño", "Invierno"]

log = logging.getLogger("simulation")


def _advance(state):
    """Tick + render del frame (corre fuera del event loop)."""
    t0 = time.perf_counter()
    new_state = tick(state)
    tick_ms = (time.perf_counter() - t0) * 1e3
    return new_state, build_render(new_state).tobytes(), tick_ms


def _season_name(tick_count):
    return SEASONS[int((tick_count % SEASON_PERIOD) / SEASON_PERIOD * 4) % 4]


class SimulationServer:
    def __init__(self):
        self.clients = set()
        self.state = None
        self.history = deque(maxlen=HISTORY_LEN)
        self.events = deque(maxlen=EVENTS_LEN)
        self.tick_ms = 0.0
        self.frame = b""
        self.reset()

    # ---- Estado ----

    def reset(self):
        self.state = create_state()
        self.frame = build_render(self.state).tobytes()
        self.history.clear()
        self.events.clear()
        self.history.append(self._counts())

    def _counts(self):
        c = np.bincount(self.state["species"].ravel(), minlength=len(SPECIES) + 1)
        return [int(c[sp]) for sp in sorted(SPECIES)]

    async def step(self):
        """Avanza un tick. El cálculo corre en un hilo (NumPy libera el GIL) para
        no bloquear el event loop; el estado se publica desde el loop, así los
        handlers nunca ven el historial a medio modificar."""
        new_state, self.frame, self.tick_ms = await asyncio.to_thread(_advance, self.state)
        self.state = new_state
        self.history.append(self._counts())
        self.events.extend(new_state["events"])

    # ---- Mensajes ----

    def init_message(self):
        st = self.state
        biome_display = (st["biome"] + 60).astype(np.uint8)
        terrain = st["terrain"]
        biome_display[terrain > 0] = 29 + terrain[terrain > 0]  # agua/roca/pantano sobre el bioma
        return json.dumps({
            "type":    "init",
            "width":   GRID_WIDTH,
            "height":  GRID_HEIGHT,
            "fps":     FPS,
            "colors":  {str(k): v for k, v in SPECIES_COLORS.items()},
            "biome":   base64.b64encode(biome_display.tobytes()).decode(),
            "species": [
                {"id": sp, "key": s["key"], "name": s["name"],
                 "color": SPECIES_COLORS[sp], "max_energy": s["max_energy"], "max_age": s["max_age"]}
                for sp, s in SPECIES.items()
            ],
            "genes": [
                {"name": GENE_NAMES[i], "min": float(GENOME_MIN[i]), "max": float(GENOME_MAX[i])}
                for i in range(N_GENES)
            ],
            "biomes":  BIOME_NAMES,
            "periods": {"season": SEASON_PERIOD, "fire": FIRE_PERIOD, "flood": FLOOD_PERIOD},
            "history": list(self.history),
            "events":  list(self.events),
        })

    def stats_message(self):
        st = self.state
        sp = st["species"]
        counts = np.bincount(sp.ravel(), minlength=len(SPECIES) + 1)

        genes = {}
        for sp_id, spec in SPECIES.items():
            mask = sp == sp_id
            genes[spec["key"]] = (
                [round(float(v), 3) for v in st["genome"][mask].mean(axis=0)]
                if counts[sp_id] else None
            )

        strength, which = dominant_layer(st["territory"])
        territory = np.bincount(which[strength >= TERRITORY_RENDER_THRESHOLD], minlength=3)

        tick_count = st["tick_count"]
        return json.dumps({
            "type":        "stats",
            "tick":        tick_count,
            "tick_ms":     round(self.tick_ms, 1),
            "clients":     len(self.clients),
            "counts":      {SPECIES[k]["key"]: int(counts[k]) for k in SPECIES},
            "infected":    int(np.count_nonzero(st["infected"])),
            "food":        int(np.count_nonzero((st["food"] > 0) & (sp == 0))),
            "genes":       genes,
            "temperature": round(float(st["global_temperature"]), 3),
            "season":      _season_name(tick_count),
            "territory":   {"herb_a": int(territory[0]), "predator": int(territory[1]),
                            "herb_b": int(territory[2])},
            "events":      st["events"],
        })

    def cell_message(self, r, c):
        st = self.state
        sp = int(st["species"][r, c])
        info = {
            "type":    "cell",
            "row":     r,
            "col":     c,
            "species": sp,
            "name":    SPECIES[sp]["name"] if sp in SPECIES else "Vacío",
            "terrain": TERRAIN_NAMES[int(st["terrain"][r, c])],
            "biome":   BIOME_NAMES[int(st["biome"][r, c])],
            "temperature": round(float(st["local_temperature"][r, c]), 2),
            "food":    bool(st["food"][r, c]),
            "nutrient": round(float(st["nutrient"][r, c]), 2),
        }
        if sp > 0:
            info.update({
                "energy":   int(st["energy"][r, c]),
                "age":      int(st["age"][r, c]),
                "infected": bool(st["infected"][r, c]),
                "gender":   {1: "♂", 2: "♀"}.get(int(st["gender"][r, c]), "—"),
                "genome":   [round(float(v), 3) for v in st["genome"][r, c]],
            })
        return json.dumps(info)

    # ---- Red ----

    def _ready_clients(self):
        """Clientes cuyo buffer de salida no está saturado: a un cliente lento se
        le saltan frames en vez de acumular memoria en el servidor."""
        ready = []
        for ws in self.clients:
            transport = ws.transport
            if transport is None or transport.get_write_buffer_size() < MAX_CLIENT_BUFFER:
                ready.append(ws)
        return ready

    async def handler(self, ws):
        self.clients.add(ws)
        log.info("cliente conectado (%d activos)", len(self.clients))
        try:
            await ws.send(self.init_message())
            await ws.send(self.stats_message())
            await ws.send(self.frame)
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                    if msg.get("type") == "inspect":
                        r, c = int(msg["row"]), int(msg["col"])
                        if 0 <= r < GRID_HEIGHT and 0 <= c < GRID_WIDTH:
                            await ws.send(self.cell_message(r, c))
                except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                    pass
        except ConnectionClosed:
            pass
        finally:
            self.clients.discard(ws)
            log.info("cliente desconectado (%d activos)", len(self.clients))

    async def run(self):
        interval = 1.0 / FPS
        next_tick = time.monotonic()
        while True:
            await self.step()

            if self.clients:
                ready = self._ready_clients()
                broadcast(ready, self.stats_message())
                broadcast(ready, self.frame)

            # Programación por deadline: el periodo no se alarga con el costo del tick
            next_tick += interval
            delay = next_tick - time.monotonic()
            if delay < 0:
                next_tick = time.monotonic()
                delay = 0
            await asyncio.sleep(delay)


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("websockets").setLevel(logging.WARNING)
    if SEED is not None:
        np.random.seed(int(SEED))
    server = SimulationServer()
    log.info("Simulación %dx%d a %.1f FPS — ws://%s:%d", GRID_WIDTH, GRID_HEIGHT, FPS, HOST, PORT)
    # max_size: el cliente solo envía peticiones de inspección pequeñas
    async with serve(server.handler, HOST, PORT, max_size=4096):
        await server.run()


if __name__ == "__main__":
    asyncio.run(main())
