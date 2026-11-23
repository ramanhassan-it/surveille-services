# rapport
# lit logs/historique.csv et calcule la dispo de chaque service
# usage : python rapport.py                          (tout l'historique)
#         python rapport.py 7                        (7 derniers jours)
#         python rapport.py exemple/historique.csv   (un autre fichier)

import csv
import sys
from datetime import datetime, timedelta

fichier = "logs/historique.csv"
jours = None

for arg in sys.argv[1:]:
    if arg.isdigit():
        jours = int(arg)
    else:
        fichier = arg

limite = None
if jours:
    limite = datetime.now() - timedelta(days=jours)

stats = {}
with open(fichier, encoding="utf-8-sig") as f:
    for l in csv.DictReader(f, delimiter=";"):
        date = datetime.strptime(l["date"], "%Y-%m-%d %H:%M:%S")
        if limite and date < limite:
            continue

        s = stats.setdefault(l["nom"], {"tests": 0, "ok": 0, "temps": [], "dernier_down": "-"})
        s["tests"] += 1
        if l["etat"] == "OK":
            s["ok"] += 1
            s["temps"].append(int(l["temps_ms"]))
        else:
            s["dernier_down"] = l["date"]

if not stats:
    print("rien dans l'historique pour cette periode")
    sys.exit()

print(f"{'service':<16} {'dispo':>7} {'moy':>7} {'tests':>6}  dernier down")
print("-" * 62)

# les pires en haut
for nom, s in sorted(stats.items(), key=lambda x: x[1]["ok"] / x[1]["tests"]):
    dispo = s["ok"] / s["tests"] * 100
    if s["temps"]:
        moy = str(round(sum(s["temps"]) / len(s["temps"]))) + "ms"
    else:
        moy = "-"
    print(f"{nom:<16} {dispo:>6.1f}% {moy:>7} {s['tests']:>6}  {s['dernier_down']}")
