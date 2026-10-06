import json
import time

# 1. Chargement des opérations de ledger2.json
print("Chargement de ledger2.json en cours...")
with open("ledger2.json", "r") as file:
    ops = json.load(file)

target_var = "c2d55089ad0cfada"

# -------------------------------------------------------------
# Méthode 1 : Suivi de l'état complet (sans vérification de validité)
# -------------------------------------------------------------
t0 = time.perf_counter()
state = {}
for op in ops:
    if op["op_type"] == "Transfer":
        state[op["source"]] -= op["amount"]
        if op["target"] in state:
            state[op["target"]] += op["amount"]
        else:
            state[op["target"]] = op["amount"]
    elif op["op_type"] == "Init":
        if op["name"] not in state:
            state[op["name"]] = op["value"]
t1 = time.perf_counter()

full_state_val = state.get(target_var, 0)
full_state_time = t1 - t0
print(f"\n[Méthode complète] Solde de {target_var} : {full_state_val}")
print(f"[Méthode complète] Temps d'exécution : {full_state_time:.4f} secondes")


# -------------------------------------------------------------
# Méthode 2 : Suivi d'une SEULE variable (réponse à la question)
# -------------------------------------------------------------
# Principe : Comme les opérations sont valides, on ignore toutes
# les opérations qui ne concernent ni la source ni la cible ciblée.
t0 = time.perf_counter()
balance = 0

for op in ops:
    op_type = op["op_type"]
    if op_type == "Transfer":
        # Deux 'if' indépendants pour gérer le cas où source == target == target_var
        if op["source"] == target_var:
            balance -= op["amount"]
        if op["target"] == target_var:
            balance += op["amount"]
    elif op_type == "Init":
        if op["name"] == target_var:
            balance = op["value"]

t1 = time.perf_counter()

single_var_val = balance
single_var_time = t1 - t0
print(f"\n[Méthode 1 variable] Solde de {target_var} : {single_var_val}")
print(f"[Méthode 1 variable] Temps d'exécution : {single_var_time:.4f} secondes")


# -------------------------------------------------------------
# Comparaison / Réponse à la question
# -------------------------------------------------------------
speedup = full_state_time / single_var_time
print(f"\n=> Facteur d'accélération : x{speedup:.2f} plus rapide !")
