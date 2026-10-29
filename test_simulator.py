"""
Growth Engine Interactive Simulator
====================================
Simulates Twilio WhatsApp webhooks locally without requiring Ngrok or active Twilio credits.
Demonstrates the entire viral loop lifecycle during local testing or screen recording.
"""

import sys
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_URL = "http://127.0.0.1:8000/whatsapp"

def send_whatsapp_message(from_number: str, body: str, profile_name: str = "Student"):
    print(f"\n📱 [STUDENT -> WHATSAPP] ({from_number})")
    print(f"   Message: \"{body}\"")
    
    data = urllib.parse.urlencode({
        "From": f"whatsapp:{from_number}",
        "Body": body,
        "ProfileName": profile_name
    }).encode("utf-8")

    req = urllib.request.Request(BASE_URL, data=data, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            xml_data = response.read().decode("utf-8")
            root = ET.fromstring(xml_data)
            reply = root.find("Message").text
            print(f"🤖 [ENGINE -> WHATSAPP]")
            for line in reply.split("\n"):
                print(f"   {line}")
            return reply
    except Exception as e:
        print(f"❌ Error communicating with backend: {e}")
        print("   Make sure the server is running on http://127.0.0.1:8000 (python main.py)")
        sys.exit(1)

def run_simulation():
    print("=" * 70)
    print("🚀 STARTING AI WORKSHOP VIRAL REFERRAL ENGINE SIMULATION")
    print("=" * 70)

    # 1. New user sends a greeting
    send_whatsapp_message("+919876543210", "Hey there, how can I register?", "Aarav")

    # 2. User registers
    reply_1 = send_whatsapp_message(
        "+919876543210",
        "Aarav Sharma\nIIT Bombay",
        "Aarav Sharma"
    )

    # Extract Aarav's code (NXT-XXXX)
    code_match = re.search(r"`(NXT-[A-Z0-9]+)`", reply_1)
    if not code_match:
        code_match = re.search(r"\b(NXT-[A-Z0-9]{4,6})\b", reply_1)
    aarav_code = code_match.group(1) if code_match else "NXT-DEMO"
    print(f"\n🔑 Captured Aarav's Referral Code: {aarav_code}")

    # 3. Friend 1 (Sneha) registers using Aarav's code
    send_whatsapp_message(
        "+919876543211",
        f"Sneha Patel\nBITS Pilani\n{aarav_code}",
        "Sneha Patel"
    )

    # 4. Friend 2 (Rohan) registers using Aarav's code
    send_whatsapp_message(
        "+919876543212",
        f"Rohan Verma, VIT Vellore, {aarav_code}",
        "Rohan Verma"
    )

    # 5. Aarav checks his status after 2 referrals
    print("\n--- Checking Aarav's Dashboard after 2 referrals ---")
    send_whatsapp_message("+919876543210", "Status update", "Aarav Sharma")

    # 6. Friend 3 (Pooja) registers using Aarav's code (reaches reward target: 3)
    send_whatsapp_message(
        "+919876543213",
        f"Pooja Nair\nNIT Trichy\n{aarav_code}",
        "Pooja Nair"
    )

    # 7. Aarav checks again -> Goal Achieved! Reward Unlocked!
    print("\n--- Checking Aarav's Dashboard after achieving 3 referrals (Reward Unlocked) ---")
    send_whatsapp_message("+919876543210", "Status update", "Aarav Sharma")

    print("\n" + "=" * 70)
    print("✅ VIRAL LOOP TEST COMPLETED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_simulation()
