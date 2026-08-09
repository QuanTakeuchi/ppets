"""
Quick manual check for the CA engine core. Not a substitute for the
pytest suite Rohit can add later (test cases TC1-TC12 already exist
for the higher-level use cases; this just exercises the raw engine).
"""

from ppets.simulation import CellularAutomatonEngine, SimulationConfig, PopulationStats


def main():
    config = SimulationConfig(
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

    engine = CellularAutomatonEngine(config)

    print(PopulationStats.csv_header())
    print(engine.history[0].to_csv_row())

    for _ in range(50):
        stats = engine.step()
        print(stats.to_csv_row())
        if engine.is_extinct():
            print(f"Extinction reached at generation {stats.generation}")
            break


if __name__ == "__main__":
    main()
