"""
Headless entry point: runs one seeded engine and prints a CSV trace
(generation, prey_count, predator_count), stopping early on extinction.

    python main.py                                   # the reference run (30x30, seed 42, 50 generations)
    python main.py --seed 7 --generations 200
    python main.py --config configs/default.json --output trace.csv

With no arguments the output is identical to evidence/hs5/main_expected.txt,
which is what the README's smoke test and validation/hs5_clean_run.py check.
Invalid input exits with status 2 and a one-line message, never a traceback.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import fields
from pathlib import Path

from ppets.simulation import CellularAutomatonEngine, SimulationConfig, PopulationStats

# The reference run. Changing these changes the expected smoke-test output.
DEFAULTS = dict(
    width=30,
    height=30,
    prey_density=0.30,
    predator_density=0.10,
    prey_repro_rate=0.20,
    predator_repro_rate=0.15,
    prey_death_threshold=3,
    starvation_rate=3,
    seed=42,
)
DEFAULT_GENERATIONS = 50
MAX_GENERATIONS = 100_000

_TYPES = {f.name: f.type for f in fields(SimulationConfig)}
_INT_FIELDS = {"width", "height", "prey_death_threshold", "starvation_rate", "seed"}
_FLOAT_FIELDS = {"prey_density", "predator_density", "prey_repro_rate", "predator_repro_rate"}


class UsageError(Exception):
    """Bad command-line or config-file input; reported without a traceback."""


def _coerce(name: str, value):
    """Check one config value's type, so a typo in a JSON file is reported by name."""
    if name in _INT_FIELDS:
        if isinstance(value, bool) or not isinstance(value, int):
            if name == "seed" and value is None:
                return None
            raise UsageError(f"{name} must be an integer, got {value!r}")
        return value
    if name in _FLOAT_FIELDS:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise UsageError(f"{name} must be a number, got {value!r}")
        return float(value)
    if name == "toroidal":
        if not isinstance(value, bool):
            raise UsageError(f"toroidal must be true or false, got {value!r}")
        return value
    raise UsageError(f"unknown parameter {name!r}; allowed: {', '.join(sorted(_TYPES))}")


def load_config_file(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise UsageError(f"config file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise UsageError(f"config file {path} is not valid JSON: {exc}") from None
    if not isinstance(data, dict):
        raise UsageError(f"config file {path} must contain a JSON object")
    generations = data.pop("generations", None)
    params = {k: _coerce(k, v) for k, v in data.items()}
    if generations is not None:
        params["generations"] = generations
    return params


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Run one PPETS simulation and print a CSV trace.")
    ap.add_argument("--config", type=Path, help="JSON file of SimulationConfig fields (and optional 'generations')")
    ap.add_argument("--width", type=int)
    ap.add_argument("--height", type=int)
    ap.add_argument("--prey-density", type=float)
    ap.add_argument("--predator-density", type=float)
    ap.add_argument("--prey-repro-rate", type=float)
    ap.add_argument("--predator-repro-rate", type=float)
    ap.add_argument("--prey-death-threshold", type=int)
    ap.add_argument("--starvation-rate", type=int)
    ap.add_argument("--seed", type=int, help="integer seed (default 42); the same seed gives the same trace")
    ap.add_argument("--fixed-boundary", action="store_true", help="non-wrapping grid edges (default: toroidal)")
    ap.add_argument("--generations", type=int, help=f"steps to run (default {DEFAULT_GENERATIONS})")
    ap.add_argument("--output", type=Path, help="write the CSV here instead of stdout")
    return ap


def resolve(args: argparse.Namespace) -> tuple[SimulationConfig, int]:
    params = dict(DEFAULTS)
    generations = DEFAULT_GENERATIONS
    if args.config is not None:
        from_file = load_config_file(args.config)
        generations = from_file.pop("generations", generations)
        params.update(from_file)
    for name in DEFAULTS:
        value = getattr(args, name)
        if value is not None:
            params[name] = value
    if args.fixed_boundary:
        params["toroidal"] = False
    if args.generations is not None:
        generations = args.generations
    if isinstance(generations, bool) or not isinstance(generations, int) or not 1 <= generations <= MAX_GENERATIONS:
        raise UsageError(f"generations must be an integer from 1 to {MAX_GENERATIONS}, got {generations!r}")
    try:
        config = SimulationConfig(**params)
    except ValueError as exc:
        raise UsageError(str(exc)) from None
    return config, generations


def run(config: SimulationConfig, generations: int, out) -> None:
    engine = CellularAutomatonEngine(config)
    print(PopulationStats.csv_header(), file=out)
    print(engine.history[0].to_csv_row(), file=out)
    for _ in range(generations):
        stats = engine.step()
        print(stats.to_csv_row(), file=out)
        if engine.is_extinct():
            print(f"Extinction reached at generation {stats.generation}", file=out)
            break


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config, generations = resolve(args)
        if args.output is None:
            run(config, generations, sys.stdout)
        else:
            try:
                with args.output.open("w", encoding="utf-8", newline="\n") as fh:
                    run(config, generations, fh)
            except OSError as exc:
                raise UsageError(f"cannot write {args.output}: {exc.strerror}") from None
    except UsageError as exc:
        parser.exit(2, f"{parser.prog}: error: {exc}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
