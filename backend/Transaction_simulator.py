import random, time, argparse, threading, requests, os
import numpy as np
from datetime import datetime
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

# Import de notre base de données
from ORM_db_traducteur_SQL import SessionLocal, Client

# --- ADAPTATION RENDER : ON UTILISE L'URL PUBLIQUE ---
API_URL = os.getenv("API_URL", "https://kyc-operation-serveur.onrender.com")

random.seed()

PAYS_BAS_RISQUE  = ["France", "Allemagne", "Royaume-Uni", "Pays-Bas", "Suède"]
PAYS_HAUT_RISQUE = ["Iran", "Corée du Nord", "Syrie", "Venezuela", "Russie"]

class DriftDetector:
    def __init__(self, window: int = 100, threshold_sigma: float = 2.0):
        self.window = window
        self.threshold = threshold_sigma
        self.buffer = deque(maxlen=window)
        self.reference_mean, self.reference_std = None, None

    def update(self, montant: float) -> bool:
        self.buffer.append(montant)
        if len(self.buffer) < self.window // 2: return False
        current_mean = np.mean(self.buffer)
        if self.reference_mean is None:
            self.reference_mean, self.reference_std = current_mean, max(np.std(self.buffer), 1.0)
            return False
        if abs(current_mean - self.reference_mean) / self.reference_std > self.threshold:
            self.reference_mean = current_mean
            return True
        return False

@dataclass
class GlobalStats:
    total: int = 0
    approuvees: int = 0
    surveillees: int = 0
    bloquees: int = 0
    erreurs: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def update(self, decision: str):
        with self.lock:
            self.total += 1
            if "APPROUV" in decision: self.approuvees += 1
            elif "SURVEILL" in decision: self.surveillees += 1
            elif "BLOQU" in decision: self.bloquees += 1

    def print_summary(self):
        with self.lock:
            if self.total == 0: return
            print(f"\n📊 RÉSUMÉ GLOBAL : 🟢 {self.approuvees} | 🟡 {self.surveillees} | 🔴 {self.bloquees} | ⚠️ {self.erreurs}\n")

stats = GlobalStats()
drift_detector = DriftDetector(window=100)

def generer_transaction(client_id: str) -> dict:
    r = random.random()
    if r < 0.12: return {"client_id": client_id, "montant": round(random.uniform(8500, 9990), 2), "type_transaction": "virement_international", "pays_destination": random.choice(PAYS_HAUT_RISQUE)}
    elif r < 0.27: return {"client_id": client_id, "montant": round(random.uniform(25000, 250000), 2), "type_transaction": "virement_international", "pays_destination": random.choice(PAYS_HAUT_RISQUE)}
    elif r < 0.40: return {"client_id": client_id, "montant": round(random.uniform(5000, 45000), 2), "type_transaction": random.choice(["virement_international", "achat_crypto"]), "pays_destination": random.choice(PAYS_HAUT_RISQUE)}
    else: return {"client_id": client_id, "montant": min(round(abs(np.random.lognormal(6.0, 0.8)), 2), 5000), "type_transaction": "virement", "pays_destination": random.choice(PAYS_BAS_RISQUE)}

def worker_client(client_id: str, interval: float, duration: float, stop_event: threading.Event):
    end_time = time.time() + duration
    while not stop_event.is_set() and time.time() < end_time:
        tx_data = generer_transaction(client_id)
        try:
            resp = requests.post(f"{API_URL}/score", json=tx_data, timeout=5.0)
            if resp.status_code == 200:
                res = resp.json()
                decision, score = res.get("decision", "INCONNUE"), res.get("score_risque", 0)
                is_drift = drift_detector.update(tx_data["montant"])
                stats.update(decision)
                if decision != "APPROUVÉE" or is_drift:
                    emoji = {"APPROUVÉE": "🟢", "SURVEILLANCE": "🟡", "BLOQUÉE": "🔴"}.get(decision, "⚪")
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] {emoji} {decision:<12} | {client_id[:8]}... | {tx_data['montant']:>10,.2f}€ | Score {score}")
            else: stats.erreurs += 1
        except: stats.erreurs += 1
        time.sleep(interval * random.uniform(0.7, 1.3))

def get_client_ids_from_db():
    db = SessionLocal()
    try: return [record[0] for record in db.query(Client.client_id).all()]
    except: return []
    finally: db.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--clients", type=int, default=15)
    parser.add_argument("--interval", type=float, default=0.8)
    parser.add_argument("--duration", type=int, default=60)
    args = parser.parse_args()

    print("🔄 Récupération des clients depuis PostgreSQL...")
    client_ids = get_client_ids_from_db()
    if not client_ids: client_ids = [f"CLIENT_{i:04d}" for i in range(100)]
    
    selected = random.sample(client_ids, min(args.clients, len(client_ids)))
    stop_event = threading.Event()

    print(f"▶️ Simulation : {args.clients} clients actifs pour {args.duration} secondes...")
    threads = [threading.Thread(target=worker_client, args=(cid, args.interval, args.duration, stop_event), daemon=True) for cid in selected]
    for t in threads: t.start()

    try:
        for t in threads: t.join()
    except KeyboardInterrupt: stop_event.set()

    print("\n✅ Fin du Simulateur.")
    stats.print_summary()

if __name__ == "__main__":
    main()
