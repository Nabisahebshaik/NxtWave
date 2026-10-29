"""
NxtWave AI Workshop - Live Campaign Terminal Simulator
======================================================
Runs an end-to-end simulation of 8 college student registrations,
demonstrates the viral attribution loop, K-factor calculation,
and updates the local database in real time.
"""

import sys
import time
import re
from fastapi.testclient import TestClient

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from main import app, crm

client = TestClient(app)

def print_banner():
    print("\n" + "=" * 75)
    print(" 🚀  NXTWAVE GROWTH CHALLENGE - VIRAL ENGINE SIMULATOR")
    print(" Target: 500 Registrations | Budget: ₹2,000 | Goal K-factor: ≥ 1.5")
    print("=" * 75 + "\n")

def simulate_student(phone: str, message: str, name: str):
    print(f"📱 [INBOUND WHATSAPP] {name} ({phone})")
    print(f"   Message: \"{message.replace(chr(10), ' | ')}\"")
    
    response = client.post(
        "/whatsapp",
        data={"From": f"whatsapp:{phone}", "Body": message, "ProfileName": name}
    )
    
    # Extract response text from TwiML XML
    xml_text = response.text
    msg_match = re.search(r"<Message>(.*?)</Message>", xml_text, re.DOTALL)
    reply = msg_match.group(1) if msg_match else xml_text
    
    # Print reply snippet
    lines = [l.strip() for l in reply.split("\n") if l.strip()]
    first_two = " ".join(lines[:2])
    print(f"🤖 [BOT RESPONSE] {first_two}...\n")
    time.sleep(0.4)
    return reply

def run():
    print_banner()
    crm._mock_db.clear()

    # Step 1: Casual inquiry (incomplete details)
    simulate_student("+919876543210", "Hey, tell me about the AI workshop?", "Aarav Sharma")

    # Step 2: Seed Student 1 (Aarav from IIT Bombay) registers
    reply_aarav = simulate_student("+919876543210", "Aarav Sharma\nIIT Bombay", "Aarav Sharma")
    code_match = re.search(r"`(NXT-[A-Z0-9]+)`", reply_aarav)
    aarav_code = code_match.group(1) if code_match else "NXT-A1B2C"
    print(f"🔑 [SYSTEM GENERATED CODE FOR AARAV]: {aarav_code}\n")

    # Step 3: Seed Student 2 (Kavita from BITS Pilani) registers
    reply_kavita = simulate_student("+919876543211", "Kavita Reddy\nBITS Pilani", "Kavita Reddy")
    kavita_match = re.search(r"\b(NXT-[A-Z0-9]+)\b", reply_kavita)
    kavita_code = kavita_match.group(1) if kavita_match else "NXT-KAV1"
    print(f"🔑 [SYSTEM GENERATED CODE FOR KAVITA]: {kavita_code}\n")

    # Step 4: Viral Loop Activation - 3 friends use Aarav's code
    print("🔥 [VIRAL CASCADE 1] 3 Friends register using Aarav's code (" + aarav_code + "):")
    simulate_student("+919876543212", f"Sneha Patel\nIIT Bombay\n{aarav_code}", "Sneha Patel")
    simulate_student("+919876543213", f"Rohan Verma\nIIT Bombay\n{aarav_code}", "Rohan Verma")
    simulate_student("+919876543214", f"Pooja Nair\nIIT Bombay\n{aarav_code}", "Pooja Nair")

    # Step 5: Check Aarav's dashboard
    print("📊 [CHECK STATUS] Aarav checks his dashboard:")
    simulate_student("+919876543210", "What's my status?", "Aarav Sharma")

    # Step 6: Viral Loop Activation - 2 friends use Kavita's code
    print("🔥 [VIRAL CASCADE 2] 2 Friends register using Kavita's code (" + kavita_code + "):")
    simulate_student("+919876543215", f"Aditya Joshi\nBITS Pilani\n{kavita_code}", "Aditya Joshi")
    simulate_student("+919876543216", f"Meera Krishnan\nBITS Pilani\n{kavita_code}", "Meera Krishnan")

    # Step 7: Print Final Real-Time Analytics
    stats_res = client.get("/api/stats")
    stats = stats_res.json()

    print("\n" + "=" * 75)
    print(" 📈  LIVE GROWTH TELEMETRY SUMMARY")
    print("=" * 75)
    print(f" • Total Registrations:    {stats['total_registered']}")
    print(f" • Seed Cohort:            {stats['seed_count']}")
    print(f" • Viral Referrals:        {stats['viral_count']}")
    print(f" • Viral Coefficient (K):  {stats['k_factor']}  (Goal: ≥ 1.50)")
    print(f" • Blended CAC:            ₹{stats['blended_cac_inr']:.2f} per student (Budget: ₹2,000)")
    print(f" • Rewards Unlocked:       {stats['rewards_unlocked']} students (>= 3 referrals)")
    print(f" • College Distribution:   {stats['colleges']}")
    print("=" * 75)
    print("\n✅ Simulation complete! You can open http://localhost:8000/dashboard to view the live GUI.")

if __name__ == "__main__":
    run()
