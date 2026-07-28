#!/usr/bin/env python3
"""
ASIN Restriction Checker — SP-API Amazon
Vérifie en bulk si des ASINs sont éligibles à la vente sur Amazon FR.

Usage:
    pip install requests python-dotenv
    cp .env.example .env   # puis remplis tes credentials
    python check_asin.py
"""

import csv
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# ── Configuration ──────────────────────────────────────────────────────────────

load_dotenv()

LWA_CLIENT_ID     = os.getenv("LWA_CLIENT_ID")
LWA_CLIENT_SECRET = os.getenv("LWA_CLIENT_SECRET")
LWA_REFRESH_TOKEN = os.getenv("LWA_REFRESH_TOKEN")
SELLER_ID         = os.getenv("SELLER_ID")
MARKETPLACE_ID    = os.getenv("MARKETPLACE_ID", "A13V1IB3VIYZZH")

INPUT_FILE      = Path("asins.csv")
OUTPUT_FILE     = Path("output.csv")
CHECKPOINT_FILE = Path(".checkpoint.json")   # reprise automatique
CONDITION_TYPE  = "new"                       # modifier si besoin : used_good, etc.
DELAY_BETWEEN_CALLS = 0.25                    # 4 req/s (limite = 5/s, on reste prudent)
MAX_RETRIES     = 3

SP_API_HOST     = "https://sellingpartnerapi-eu.amazon.com"
RESTRICTIONS_PATH = "/listings/2021-08-01/restrictions"
LWA_TOKEN_URL   = "https://api.amazon.com/auth/o2/token"

# ── Validation des credentials ─────────────────────────────────────────────────

def check_credentials():
    missing = [k for k, v in {
        "LWA_CLIENT_ID": LWA_CLIENT_ID,
        "LWA_CLIENT_SECRET": LWA_CLIENT_SECRET,
        "LWA_REFRESH_TOKEN": LWA_REFRESH_TOKEN,
        "SELLER_ID": SELLER_ID,
    }.items() if not v]
    if missing:
        print(f"[ERREUR] Credentials manquants dans .env : {', '.join(missing)}")
        sys.exit(1)

# ── Authentification LWA ───────────────────────────────────────────────────────

_token_cache = {"access_token": None, "expires_at": 0}

def get_access_token():
    """Retourne un access token valide, le rafraîchit si expiré."""
    now = time.time()
    if _token_cache["access_token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["access_token"]

    print("[AUTH] Récupération d'un nouveau token LWA…")
    resp = requests.post(LWA_TOKEN_URL, data={
        "grant_type":    "refresh_token",
        "refresh_token": LWA_REFRESH_TOKEN,
        "client_id":     LWA_CLIENT_ID,
        "client_secret": LWA_CLIENT_SECRET,
    }, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=15)

    if resp.status_code != 200:
        print(f"[ERREUR AUTH] {resp.status_code} — {resp.text}")
        sys.exit(1)

    data = resp.json()
    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"]   = now + data.get("expires_in", 3600)
    print("[AUTH] Token OK ✓")
    return _token_cache["access_token"]

# ── Lecture du CSV d'entrée ────────────────────────────────────────────────────

def load_asins(filepath: Path) -> list[str]:
    """
    Accepte deux formats :
      - Avec header 'asin'  → première colonne après header
      - Sans header          → une valeur par ligne
    """
    asins = []
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        sample = f.read(512)
        f.seek(0)
        has_header = "asin" in sample.lower().split("\n")[0]

        if has_header:
            reader = csv.DictReader(f)
            col = next((c for c in reader.fieldnames if c.strip().lower() == "asin"), None)
            if not col:
                print("[ERREUR] Colonne 'asin' introuvable dans le header du CSV.")
                sys.exit(1)
            for row in reader:
                v = row[col].strip()
                if v:
                    asins.append(v.upper())
        else:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip():
                    asins.append(row[0].strip().upper())

    print(f"[INFO] {len(asins)} ASINs chargés depuis {filepath}")
    return asins

# ── Checkpoint (reprise) ───────────────────────────────────────────────────────

def load_checkpoint() -> dict:
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            data = json.load(f)
        print(f"[REPRISE] Checkpoint trouvé : {len(data)} ASINs déjà traités.")
        return data
    return {}

def save_checkpoint(done: dict):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(done, f)

# ── Appel API SP-API ───────────────────────────────────────────────────────────

def call_restrictions_api(asin: str, token: str) -> dict:
    """
    Appelle GET /listings/2021-08-01/restrictions pour un ASIN.
    Retourne le JSON brut ou un dict d'erreur.
    """
    url = SP_API_HOST + RESTRICTIONS_PATH
    params = {
        "asin":           asin,
        "sellerId":       SELLER_ID,
        "marketplaceIds": MARKETPLACE_ID,
    }
    headers = {
        "x-amz-access-token": token,
        "Content-Type":       "application/json",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=15)

            if resp.status_code == 200:
                return {"ok": True, "body": resp.json()}

            elif resp.status_code == 429:
                wait = 2 ** attempt
                print(f"  [429] Rate limit — attente {wait}s (tentative {attempt}/{MAX_RETRIES})")
                time.sleep(wait)
                continue

            elif resp.status_code == 403:
                # Token peut-être expiré : on le renouvelle une fois
                print(f"  [403] Token invalide ou accès refusé pour {asin}")
                return {"ok": False, "status_code": 403, "body": resp.text}

            elif resp.status_code == 400:
                return {"ok": False, "status_code": 400, "body": resp.text}

            elif resp.status_code == 404:
                return {"ok": False, "status_code": 404, "body": resp.text}

            else:
                print(f"  [HTTP {resp.status_code}] {asin} — tentative {attempt}/{MAX_RETRIES}")
                time.sleep(1)

        except requests.exceptions.RequestException as e:
            print(f"  [RÉSEAU] {asin} — {e} — tentative {attempt}/{MAX_RETRIES}")
            time.sleep(2)

    return {"ok": False, "status_code": 0, "body": "Max retries atteint"}

# ── Classification du résultat ─────────────────────────────────────────────────

def classify(asin: str, api_result: dict) -> dict:
    """
    Transforme la réponse brute de l'API en statut métier.

    Retourne un dict : asin, status, reason_code, message, raw_response
    """
    STATUS_MESSAGES = {
        "ELIGIBLE":          "Vente libre",
        "APPROVAL_REQUIRED": "Autorisation requise",
        "NOT_ELIGIBLE":      "Non éligible",
        "NOT_FOUND":         "ASIN introuvable",
        "ERROR":             "Erreur",
    }

    if not api_result["ok"]:
        code = api_result.get("status_code", 0)
        body = api_result.get("body", "")

        if code == 404:
            return {
                "ASIN": asin, "Statut": "NOT_FOUND",
                "Code restriction": "404", "Message": STATUS_MESSAGES["NOT_FOUND"],
            }
        return {
            "ASIN": asin, "Statut": "ERROR",
            "Code restriction": str(code), "Message": str(body)[:300],
        }

    body = api_result["body"]
    restrictions = body.get("restrictions", [])

    # Filtre uniquement les restrictions dont le conditionType commence par "new" (new_new, new_oem…)
    new_restrictions = [r for r in restrictions if r.get("conditionType", "").startswith("new")]

    if not new_restrictions:
        # Pas de restriction en condition new → éligible
        return {
            "ASIN": asin, "Statut": "ELIGIBLE",
            "Code restriction": "", "Message": STATUS_MESSAGES["ELIGIBLE"],
        }

    # Analyse des reasons sur les restrictions new uniquement
    all_reasons = []
    has_approval_link = False

    for r in new_restrictions:
        for reason in r.get("reasons", []):
            code = reason.get("reasonCode", "")
            all_reasons.append(code)
            if reason.get("links"):
                has_approval_link = True

    reason_str = ", ".join(set(all_reasons))

    if has_approval_link or "APPROVAL_REQUIRED" in all_reasons:
        status = "APPROVAL_REQUIRED"
    else:
        status = "NOT_ELIGIBLE"

    return {
        "ASIN": asin, "Statut": status,
        "Code restriction": reason_str,
        "Message": STATUS_MESSAGES[status],
    }

# ── Export CSV ─────────────────────────────────────────────────────────────────

FIELDNAMES = ["ASIN", "Statut", "Code restriction", "Message"]

def write_results(results: list[dict], filepath: Path):
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(results)
    print(f"\n[OK] Résultats exportés → {filepath}")

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  ASIN Restriction Checker — Amazon SP-API")
    print("=" * 55)

    check_credentials()

    asins    = load_asins(INPUT_FILE)
    done     = load_checkpoint()    # ASINs déjà traités (reprise)
    results  = list(done.values())  # résultats déjà obtenus
    token    = get_access_token()

    todo = [a for a in asins if a not in done]
    print(f"[INFO] {len(todo)} ASINs à traiter ({len(done)} déjà dans le checkpoint)\n")

    for i, asin in enumerate(todo, 1):
        # Renouvelle le token toutes les 50 requêtes (précaution)
        if i % 50 == 0:
            token = get_access_token()

        print(f"[{i}/{len(todo)}] {asin}", end=" … ", flush=True)

        api_result = call_restrictions_api(asin, token)
        row = classify(asin, api_result)

        print(row["Statut"])

        results.append(row)
        done[asin] = row
        save_checkpoint(done)

        time.sleep(DELAY_BETWEEN_CALLS)

    write_results(results, OUTPUT_FILE)

    # Nettoyage du checkpoint une fois tout terminé
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
        print("[INFO] Checkpoint supprimé (traitement complet).")

    # Résumé
    from collections import Counter
    counts = Counter(r["Statut"] for r in results)
    print("\n── Résumé ──────────────────────")
    for status, n in sorted(counts.items()):
        print(f"  {status:<20} {n}")
    print(f"  {'TOTAL':<20} {len(results)}")
    print("────────────────────────────────")

if __name__ == "__main__":
    main()
