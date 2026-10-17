"""Mide el costo medio por tick de cada regla, del render y de las estadísticas.

Uso:  python scripts/benchmark.py [ticks] [semilla]
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np  # noqa: E402

import simulation  # noqa: E402
from server import SimulationServer  # noqa: E402


def main():
    n_ticks = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    np.random.seed(int(sys.argv[2]) if len(sys.argv) > 2 else 0)

    server = SimulationServer()
    state = server.state
    timings = {rule.__name__.split(".")[-1]: 0.0 for rule in simulation.RULES}
    render = stats = 0.0

    for _ in range(n_ticks):
        state = {**state, "tick_count": state["tick_count"] + 1, "events": []}
        for rule in simulation.RULES:
            t0 = time.perf_counter()
            state = rule.apply(state)
            timings[rule.__name__.split(".")[-1]] += time.perf_counter() - t0
        t0 = time.perf_counter()
        simulation.build_render(state)
        render += time.perf_counter() - t0
        server.state = state
        t0 = time.perf_counter()
        server.stats_message()
        stats += time.perf_counter() - t0

    ms = lambda total: total / n_ticks * 1e3  # noqa: E731
    print(f"{n_ticks} ticks — ms por tick\n")
    for name, total in sorted(timings.items(), key=lambda kv: -kv[1]):
        print(f"  {name:<16} {ms(total):7.2f}")
    print(f"  {'-' * 24}\n  {'tick total':<16} {ms(sum(timings.values())):7.2f}")
    print(f"  {'build_render':<16} {ms(render):7.2f}\n  {'stats':<16} {ms(stats):7.2f}")
    counts = np.bincount(state["species"].ravel(), minlength=5)[1:]
    print(f"\npoblación final A/P/B/O: {'/'.join(map(str, counts))}")


if __name__ == "__main__":
    main()
