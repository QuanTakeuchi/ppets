"""Selection-free noise estimate for a 3-replicate heatmap cell.

    python validation/triple_retest.py

pilot_study.py picked its cells *because* their first three replicates looked
extreme, which exaggerates the n=3 vs n=100 gap (regression to the mean). This
script removes that selection effect: it cuts each cell's 100 replicates into
33 disjoint triples (reps 0-2, 3-5, ...) and asks how often a randomly chosen
3-replicate estimate lands far from the cell's 100-replicate estimate.

Output: evidence/validation/triple_retest.json
"""
import csv
import json
import statistics
from collections import defaultdict

from _common import EVIDENCE, provenance, write_json

cells = defaultdict(dict)
with open(EVIDENCE / "pilot_replicates.csv", newline="") as f:
    for r in csv.DictReader(f):
        g = r["extinction_generation"]
        extinct = g != "" and int(g) <= 150
        cells[(float(r["predator_density"]), float(r["predator_repro_rate"]))][int(r["replicate"])] = extinct

out, miss_all, n_all = [], 0, 0
for (pd, pr), reps in sorted(cells.items()):
    n = len(reps)
    p100 = sum(reps.values()) / n
    triples = [sum(reps[i + j] for j in range(3)) / 3 for i in range(0, n - n % 3, 3)]
    far = sum(abs(t - p100) > 0.25 for t in triples)
    miss_all += far
    n_all += len(triples)
    out.append(dict(predator_density=pd, predator_repro_rate=pr, p_hat_100=round(p100, 2),
                    triples=len(triples), triple_sd=round(statistics.pstdev(triples), 3),
                    triple_min=round(min(triples), 2), triple_max=round(max(triples), 2),
                    triples_off_by_more_than_0_25=far))
payload = dict(provenance=provenance(), cells=out, triples_total=n_all,
               triples_off_by_more_than_0_25=miss_all,
               fraction_off=round(miss_all / n_all, 3))
write_json(EVIDENCE / "triple_retest.json", payload)
for c in out:
    print(c)
print("overall: ", miss_all, "/", n_all, "=", payload["fraction_off"])
