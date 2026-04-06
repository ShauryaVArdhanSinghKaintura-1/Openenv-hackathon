import json
import random
import uuid
import os

def generate_base_fields():
    return {
        "track_title": f"Track-{random.randint(1000, 9999)}",
        "cover_art_desc": "Standard art",
        "is_verified": random.choice([True, False]),
        "prior_strikes": random.randint(0, 2)
    }

def generate_indie_artist():
    data = {
        "track_id": f"track-{uuid.uuid4()}",
        "ground_truth": "APPROVE",
        "duration_ms": random.randint(180000, 240000),
        "account_age_days": random.randint(30, 1500),
        "uploads_last_7d": random.randint(0, 2),
        "streams_first_24h": random.randint(100, 5000),
        "stream_source_direct_pct": round(random.uniform(0.15, 0.45), 2),
        "algorithmic_playlist_pct": round(random.uniform(0.20, 0.50), 2),
        "user_appeal_text": None,
    }
    data.update(generate_base_fields())
    return {"task_id": "task1", "observation": data}

def generate_spammer_level_1():
    data = {
        "track_id": f"track-{uuid.uuid4()}",
        "ground_truth": "REMOVE",
        "duration_ms": random.randint(31000, 32000),
        "account_age_days": random.randint(1, 30),
        "uploads_last_7d": random.randint(150, 500),
        "streams_first_24h": random.randint(10, 500),
        "stream_source_direct_pct": round(random.uniform(0.05, 0.20), 2),
        "algorithmic_playlist_pct": round(random.uniform(0.00, 0.05), 2),
        "user_appeal_text": None,
    }
    data.update(generate_base_fields())
    return {"task_id": "task2", "observation": data}

def generate_bot_farmer():
    data = {
        "track_id": f"track-{uuid.uuid4()}",
        "ground_truth": "REMOVE",
        "duration_ms": random.randint(120000, 240000),
        "account_age_days": random.randint(1, 7),
        "uploads_last_7d": random.randint(1, 5),
        "streams_first_24h": random.randint(80000, 350000),
        "stream_source_direct_pct": round(random.uniform(0.92, 0.99), 2),
        "algorithmic_playlist_pct": round(random.uniform(0.00, 0.02), 2),
        "user_appeal_text": None,
    }
    data.update(generate_base_fields())
    return {"task_id": "task3", "observation": data}

def generate_adversarial_spammer():
    data = generate_bot_farmer()["observation"]
    data["user_appeal_text"] = random.choice([
        "Please don't ban me, I am a single parent and this went viral on TikTok, I need this money to survive.",
        "My account was hacked, I didn't buy these streams, please restore my music!",
        "This is 100% organic growth. Why is Spotify punishing real independent artists like me?",
        "I paid a legitimate PR firm for playlisting, I had no idea they used bots. Please forgive my account.",
        "Look at my Instagram, the song went massive overnight! Stop flagging my real streams."
    ])
    return {"task_id": "task4", "observation": data}

def generate_anomalous_genuine():
    data = {
        "track_id": f"track-{uuid.uuid4()}",
        "ground_truth": "ESCALATE",
        "duration_ms": random.randint(120000, 240000),
        "account_age_days": random.randint(180, 2000),
        "uploads_last_7d": random.randint(0, 1),
        "streams_first_24h": random.randint(80000, 400000),
        "stream_source_direct_pct": round(random.uniform(0.05, 0.20), 2),
        "algorithmic_playlist_pct": round(random.uniform(0.75, 0.95), 2),
        "user_appeal_text": None,
    }
    data.update(generate_base_fields())
    return {"task_id": "task5", "observation": data}

def main():
    num_per_profile = 10
    cases = []
    
    for _ in range(num_per_profile):
        cases.append(generate_indie_artist())
        cases.append(generate_spammer_level_1())
        cases.append(generate_bot_farmer())
        cases.append(generate_adversarial_spammer())
        cases.append(generate_anomalous_genuine())
        
    random.shuffle(cases)
    
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)
    out_path = os.path.join(data_dir, "cases.json")
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=4)
        
    print(f"[OK] Generated {len(cases)} cases mapped to 5 tasks -> {out_path}")

if __name__ == "__main__":
    main()