"""
AI Workshop Referral Command Center - FastAPI Backend Microservice
==================================================================
Production-grade integration server for NxtWave Growth Challenge.
Architecture:
  - Google Sheets CRM: "NxtWave_Registration_CRM"
  - Schema: Timestamp | Phone_Number | Name | College | My_Referral_Code | Referred_By | Total_Referrals
  - Twilio WhatsApp Webhook: POST /whatsapp
  - OpenAI NLP Entity Extraction: gpt-4o-mini with regex fallback
  - High-frequency live polling endpoints for React frontend (3s polling)
  - Thread-safe in-memory caching to prevent Google Sheets 429 rate limit
  - Resilient in-memory fallback for zero-failure live demos
"""

import os
import re
import json
import secrets
import string
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from threading import Lock

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import gspread
from google.oauth2.service_account import Credentials
from openai import OpenAI
from twilio.twiml.messaging_response import MessagingResponse

# -----------------------------------------------------------------------------
# 1. Environment & Logging Setup
# -----------------------------------------------------------------------------
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | [%(levelname)s] | %(name)s | %(message)s"
)
logger = logging.getLogger("referral-backend")

GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "NxtWave_Registration_CRM")
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
TOTAL_MARKETING_BUDGET_INR = float(os.getenv("MARKETING_BUDGET_INR", "2000.0"))
CAMPAIGN_GOAL = int(os.getenv("CAMPAIGN_GOAL", "500"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

app = FastAPI(
    title="NxtWave Referral Command Center API",
    description="High-performance backend for viral WhatsApp student acquisition sprint.",
    version="2.0.0",
    docs_url="/docs"
)

# -----------------------------------------------------------------------------
# 2. CORS Middleware (Essential for React Frontend connection)
# -----------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*"  # Fully permissive for hackathon & live screen recording
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# 3. Google Sheets CRM Engine (With Caching & Resilient Demo Mode)
# -----------------------------------------------------------------------------
SHEET_HEADERS = [
    "Timestamp",
    "Phone_Number",
    "Name",
    "College",
    "My_Referral_Code",
    "Referred_By",
    "Total_Referrals"
]

class GoogleSheetsCRM:
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    def __init__(self, sheet_name: str, creds_path: str):
        self.sheet_name = sheet_name
        self.creds_path = creds_path
        self._sheet: Optional[gspread.Worksheet] = None
        self._cache_lock = Lock()
        self._cached_rows: List[Dict[str, Any]] = []
        self._last_cache_time = 0.0
        self._cache_ttl = 2.5  # 2.5 second cache prevents hitting Google Sheets 60 req/min limit
        self._mock_db: List[Dict[str, Any]] = []  # Resilient fallback store

    def connect(self) -> bool:
        """Connects to Google Sheets via file or GOOGLE_CREDENTIALS_JSON env var, or falls back to in-memory mode."""
        creds = None
        if os.path.exists(self.creds_path):
            try:
                creds = Credentials.from_service_account_file(self.creds_path, scopes=self.SCOPES)
            except Exception as e:
                logger.warning(f"[CRM] Error loading credentials file: {e}")
        elif os.getenv("GOOGLE_CREDENTIALS_JSON"):
            try:
                raw_json = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
                creds_info = json.loads(raw_json)
                creds = Credentials.from_service_account_info(creds_info, scopes=self.SCOPES)
                logger.info("[CRM] Loaded service account credentials from GOOGLE_CREDENTIALS_JSON environment variable.")
            except Exception as e:
                logger.warning(f"[CRM] Error parsing GOOGLE_CREDENTIALS_JSON: {e}")

        if not creds:
            logger.warning(
                f"[CRM] No credentials file ('{self.creds_path}') or GOOGLE_CREDENTIALS_JSON env var found! "
                "Activating in-memory mock CRM. All reads/writes will work seamlessly for the demo."
            )
            return False

        try:
            client = gspread.authorize(creds)
            spreadsheet = client.open(self.sheet_name)
            self._sheet = spreadsheet.sheet1
            self._ensure_headers()
            logger.info(f"[CRM] Successfully connected to Google Sheet: '{self.sheet_name}'")
            return True
        except Exception as e:
            logger.error(f"[CRM] Connection failed: {e}. Running with resilient in-memory fallback.")
            return False

    def _ensure_headers(self) -> None:
        if not self._sheet:
            return
        try:
            existing = self._sheet.row_values(1)
            if not existing:
                self._sheet.insert_row(SHEET_HEADERS, index=1)
                logger.info("[CRM] Initialized Google Sheet headers.")
        except Exception as e:
            logger.warning(f"[CRM] Failed to inspect headers: {e}")

    def get_all_records(self) -> List[Dict[str, Any]]:
        """
        Thread-safe, TTL-cached retrieval of all CRM rows.
        Standardizes column access across both Google Sheets and in-memory mode.
        """
        with self._cache_lock:
            now = time.time()
            if self._cached_rows and (now - self._last_cache_time) < self._cache_ttl:
                return self._cached_rows

            if not self._sheet:
                self._cached_rows = [dict(r) for r in self._mock_db]
                self._last_cache_time = now
                return self._cached_rows

            try:
                raw_records = self._sheet.get_all_records()
                standardized = []
                for r in raw_records:
                    phone = str(r.get("Phone_Number") or r.get("Phone") or "")
                    standardized.append({
                        "Timestamp": str(r.get("Timestamp", "")),
                        "Phone_Number": phone,
                        "Phone": phone,
                        "Name": str(r.get("Name", "")),
                        "College": str(r.get("College", "")),
                        "My_Referral_Code": str(r.get("My_Referral_Code", "")),
                        "Referred_By": str(r.get("Referred_By", "")),
                        "Total_Referrals": int(r.get("Total_Referrals", 0)) if str(r.get("Total_Referrals", "")).isdigit() else 0
                    })
                self._cached_rows = standardized
                self._last_cache_time = now
                return self._cached_rows
            except Exception as e:
                logger.error(f"[CRM] Error reading Google Sheets: {e}")
                return [dict(r) for r in self._mock_db]

    def append_registration(
        self,
        phone: str,
        name: str,
        college: str,
        my_code: str,
        referred_by: str = ""
    ) -> Dict[str, Any]:
        """Appends a new student row to the CRM."""
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        record = {
            "Timestamp": now_str,
            "Phone_Number": phone,
            "Phone": phone,
            "Name": name,
            "College": college,
            "My_Referral_Code": my_code,
            "Referred_By": referred_by,
            "Total_Referrals": 0
        }

        # 1. Update in-memory DB & cache immediately for zero-latency response
        with self._cache_lock:
            self._mock_db.append(record)
            self._cached_rows.append(record)
            self._last_cache_time = time.time()

        # 2. Asynchronously write to Google Sheet if connected
        if self._sheet:
            try:
                row_data = [
                    now_str,
                    phone,
                    name,
                    college,
                    my_code,
                    referred_by,
                    0
                ]
                self._sheet.append_row(row_data)
                logger.info(f"[CRM] Synced new registration to Google Sheet: {name} ({my_code})")
            except Exception as e:
                logger.error(f"[CRM] Failed writing to Google Sheet: {e}")

        return record

    def find_user_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Looks up user by phone number from cached CRM records."""
        clean = self.normalize_phone(phone)
        records = self.get_all_records()
        for r in records:
            if self.normalize_phone(r.get("Phone_Number", "")) == clean or self.normalize_phone(r.get("Phone", "")) == clean:
                return {
                    "name": r.get("Name", ""),
                    "college": r.get("College", ""),
                    "my_code": r.get("My_Referral_Code", ""),
                    "referred_by": r.get("Referred_By", ""),
                    "total_referrals": int(r.get("Total_Referrals", 0))
                }
        return None

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Strips whatsapp: prefix and whitespace."""
        return re.sub(r"^whatsapp:", "", phone.strip()).strip()

    create_registration = append_registration

    def increment_referral_count(self, referral_code: str) -> None:
        """Finds the referrer's row and increments Total_Referrals by 1."""
        if not referral_code:
            return

        referral_code = referral_code.strip().upper()

        # 1. Update in-memory cache instantly
        with self._cache_lock:
            for r in self._mock_db:
                if r.get("My_Referral_Code", "").upper() == referral_code:
                    r["Total_Referrals"] += 1
                    logger.info(f"[CRM In-Memory] Incremented {referral_code} count to {r['Total_Referrals']}")
            if self._sheet:
                for r in self._cached_rows:
                    if r.get("My_Referral_Code", "").upper() == referral_code:
                        r["Total_Referrals"] += 1

        # 2. Update Google Sheet cell if connected
        if not self._sheet:
            return

        try:
            cell = self._sheet.find(referral_code)
            if cell and cell.col == 5:  # My_Referral_Code is Column 5 (E)
                row = cell.row
                current_val = self._sheet.cell(row, 7).value  # Total_Referrals is Column 7 (G)
                new_val = int(current_val or 0) + 1
                self._sheet.update_cell(row, 7, new_val)
                logger.info(f"[CRM Live Sheet] Incremented {referral_code} referral count to {new_val}")
        except Exception as e:
            logger.error(f"[CRM] Failed updating referrer cell in sheet: {e}")

crm = GoogleSheetsCRM(GOOGLE_SHEET_NAME, GOOGLE_CREDENTIALS_FILE)
crm.connect()

# -----------------------------------------------------------------------------
# 4. Helper Utilities (NLP & Code Generation)
# -----------------------------------------------------------------------------
def generate_referral_code(prefix: str = "NXT-", length: int = 4) -> str:
    """Generates a unique NXT-XXXX code with 4 uppercase alphanumeric chars."""
    random_suffix = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(length))
    return f"{prefix}{random_suffix}"

def generate_unique_referral_code(existing_codes=None, prefix: str = "NXT-", length: int = 4) -> str:
    existing = set(existing_codes or [])
    for _ in range(100):
        code = generate_referral_code(prefix=prefix, length=length)
        if code not in existing:
            return code
    return generate_referral_code(prefix=prefix, length=length)

def parse_whatsapp_body(body: str) -> Dict[str, Optional[str]]:
    """Deterministic regex extraction fallback for student messages."""
    body_clean = body.strip()
    lines = [l.strip() for l in body_clean.splitlines() if l.strip()]

    # Extract referral code pattern: NXT-XXXX or NXT-XXXXX
    ref_match = re.search(r"\b(NXT-[A-Z0-9]{4,6})\b", body_clean.upper())
    referred_by = ref_match.group(1) if ref_match else ""

    name = None
    college = None

    if len(lines) >= 2:
        name = lines[0]
        if ref_match and ref_match.group(1) in lines[1].upper() and len(lines) >= 3:
            college = lines[2]
        else:
            college = lines[1]
    elif len(lines) == 1 and "," in lines[0]:
        parts = [p.strip() for p in lines[0].split(",")]
        name = parts[0]
        if len(parts) > 1:
            college = parts[1]
    else:
        name = lines[0] if lines else "Student"
        college = "Autonomous / Open Tech"

    name = re.sub(r"(?i)^(my name is|i am|this is)\s+", "", name).strip()
    return {
        "name": name.title() if name else "Student",
        "college": college.title() if college else "Engineering College",
        "referred_by": referred_by
    }

def extract_with_openai(body_text: str) -> Dict[str, Optional[str]]:
    """Uses OpenAI gpt-4o-mini structured extraction with fallback to regex parser."""
    if not openai_client:
        return parse_whatsapp_body(body_text)

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a growth marketing assistant for an AI College Workshop.\n"
                        "Extract 3 variables from the student's incoming message:\n"
                        "- 'name': Student's full name (null if not provided)\n"
                        "- 'college': College/University name (null if not provided)\n"
                        "- 'referral_code': Any referral code (like NXT-XXXX) if mentioned, else null\n"
                        "Return strictly valid JSON with keys: name, college, referral_code."
                    )
                },
                {"role": "user", "content": body_text}
            ]
        )
        data = json.loads(response.choices[0].message.content)
        name = data.get("name")
        college = data.get("college")
        referral_code = data.get("referral_code") or ""

        if not name or not college:
            # Fall back to regex if LLM was overly conservative
            fallback = parse_whatsapp_body(body_text)
            name = name or fallback["name"]
            college = college or fallback["college"]
            referral_code = referral_code or fallback["referred_by"]

        return {
            "name": name.title() if name else "Student",
            "college": college.title() if college else "Engineering College",
            "referred_by": referral_code.upper() if referral_code else ""
        }
    except Exception as e:
        logger.warning(f"OpenAI extraction failed ({e}), executing regex fallback.")
        return parse_whatsapp_body(body_text)

# -----------------------------------------------------------------------------
# 5. Core REST API Endpoints for React Frontend
# -----------------------------------------------------------------------------
@app.get("/api/stats", tags=["Dashboard"])
def get_stats():
    """
    Computes real-time growth analytics for the React CommandCenter:
      - Total Registered (Goal: 500)
      - Viral Coefficient (Total Referrals / Base Users)
      - Blended CAC (₹2000 Marketing Budget / Total Registrations)
      - Rewards Unlocked (Students with >= 3 referrals)
    """
    records = crm.get_all_records()
    total_registered = len(records)

    viral_signups = sum(1 for r in records if r.get("Referred_By"))
    seed_signups = max(1, total_registered - viral_signups)

    # Viral Coefficient = Viral Referrals / Base Users
    if total_registered > 0 and seed_signups > 0:
        viral_coefficient = round(viral_signups / seed_signups, 2)
    else:
        viral_coefficient = 0.0

    # Blended CAC calculation (₹2000 total budget / total registered)
    if total_registered > 0:
        blended_cac = round(TOTAL_MARKETING_BUDGET_INR / total_registered, 2)
    else:
        blended_cac = TOTAL_MARKETING_BUDGET_INR

    rewards_unlocked = sum(1 for r in records if r.get("Total_Referrals", 0) >= 3)

    # College Distribution
    colleges: Dict[str, int] = {}
    for r in records:
        c = (r.get("College") or "Other").title()
        colleges[c] = colleges.get(c, 0) + 1

    progress_percentage = min(100.0, round((total_registered / CAMPAIGN_GOAL) * 100, 1))

    return {
        "total_registered": total_registered,
        "target": CAMPAIGN_GOAL,
        "progress_percentage": progress_percentage,
        "base_users": seed_signups,
        "viral_users": viral_signups,
        "viral_coefficient": viral_coefficient,
        "k_factor": viral_coefficient,
        "blended_cac_inr": blended_cac,
        "blended_cac": blended_cac,
        "seed_count": seed_signups,
        "viral_count": viral_signups,
        "rewards_unlocked": rewards_unlocked,
        "colleges": colleges
    }


@app.get("/api/feed", tags=["Dashboard"])
def get_feed():
    """
    Returns the 10 most recent rows from the Google Sheet for the live dashboard feed.
    """
    records = crm.get_all_records()
    recent = records[-10:][::-1]
    return {
        "count": len(recent),
        "feed": recent
    }


@app.get("/api/ambassadors", tags=["Campus Partners"])
@app.get("/ambassadors", tags=["Campus Partners"])
def get_ambassadors():
    """
    Groups and counts registrations by college for Campus Ambassador tracking:
      - Target: 40 registrations
      - Milestone 1: 20 registrations (₹150 payout)
      - Milestone 2: 40 registrations (₹300 total payout)
    """
    records = crm.get_all_records()

    leads = [
        {"college": "IIT Bombay", "lead_name": "Aarav Sharma", "club": "Coding Society", "target": 40},
        {"college": "BITS Pilani", "lead_name": "Sneha Patel", "club": "Tech Team", "target": 40},
        {"college": "VIT Vellore", "lead_name": "Rohan Verma", "club": "Developer Club", "target": 40},
        {"college": "NIT Trichy", "lead_name": "Pooja Nair", "club": "Placement Cell", "target": 40},
        {"college": "DTU Delhi", "lead_name": "Vikram Rao", "club": "ACM Chapter", "target": 40},
    ]

    ambassadors_data = []
    for item in leads:
        c_search = item["college"].lower()
        count = sum(1 for r in records if c_search in (r.get("College") or "").lower())

        milestone_1 = count >= 20
        milestone_2 = count >= 40

        if milestone_2:
            payout_status = "₹300 (Completed! 🎉)"
        elif milestone_1:
            payout_status = "₹150 (Milestone 1 Unlocked)"
        else:
            payout_status = "₹0 (Pending 20 regs)"

        ambassadors_data.append({
            "college": item["college"],
            "lead_name": item["lead_name"],
            "club": item["club"],
            "current_registrations": count,
            "target": item["target"],
            "progress_percent": min(100, int((count / item["target"]) * 100)),
            "milestone_1_paid": milestone_1,
            "milestone_2_paid": milestone_2,
            "payout_status": payout_status
        })

    return {"ambassadors": ambassadors_data}


# -----------------------------------------------------------------------------
# 6. Twilio WhatsApp Webhook (POST /whatsapp)
# -----------------------------------------------------------------------------
@app.post("/whatsapp", tags=["Twilio Webhook"])
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    ProfileName: Optional[str] = Form(None)
):
    """
    Twilio WhatsApp Webhook Endpoint:
      1. Receives message from student on WhatsApp.
      2. Checks if phone number already exists in Google Sheet CRM.
      3. Uses OpenAI gpt-4o-mini to extract Name, College, and Referral Code.
      4. Generates unique 'NXT-XXXX' referral code.
      5. Appends user to Google Sheet & updates referrer's 'Total_Referrals' count.
      6. Returns a Twilio TwiML success response.
    """
    phone_clean = From.replace("whatsapp:", "").strip()
    body_clean = Body.strip()
    logger.info(f"[WhatsApp] Received text from {phone_clean}: {body_clean}")

    records = crm.get_all_records()
    existing_user = next((r for r in records if r["Phone_Number"] == phone_clean or r.get("Phone") == phone_clean), None)
    twiml = MessagingResponse()

    # Case A: Returning user checking referral status
    if existing_user and any(w in body_clean.lower() for w in ["status", "count", "referral", "reward", "stats"]):
        code = existing_user["My_Referral_Code"]
        count = existing_user["Total_Referrals"]
        needed = max(0, 3 - count)

        if count >= 3:
            msg = (
                f"🎉 *CONGRATULATIONS, {existing_user['Name']}!*\n\n"
                f"You have referred *{count} friends* and unlocked your reward:\n"
                f"📘 *Top 50 AI Interview Prompts Guide*\n\n"
                f"📥 Download here: https://nxtwave.tech/rewards/{code}\n\n"
                f"Keep sharing to top the Campus Leaderboard!"
            )
        else:
            msg = (
                f"Welcome back {existing_user['Name']}! 👋\n\n"
                f"Your referral code is *{code}*.\n"
                f"You have *{count} referrals*.\n"
                f"({needed} more needed to unlock the 'Top 50 AI Interview Prompts')\n\n"
                f"📲 Share your code with batchmates to claim your reward!"
            )
        twiml.message(msg)
        return Response(content=str(twiml), media_type="application/xml")

    # Case B: Returning user sending any other message
    if existing_user:
        twiml.message(
            f"Welcome back {existing_user['Name']}! Your referral code is {existing_user['My_Referral_Code']}. You have {existing_user['Total_Referrals']} referrals."
        )
        return Response(content=str(twiml), media_type="application/xml")

    # Case C: Casual greeting without registration info
    is_inquiry = any(g in body_clean.lower() for g in ["hi", "hello", "hey", "register", "join", "tell me", "how can i", "what is", "info"])
    has_multiline = "\n" in body_clean
    has_two_fields = "," in body_clean and len([p for p in body_clean.split(",") if p.strip()]) >= 2 and not any(q in body_clean.lower() for q in ["tell me", "what is", "how"])
    
    if is_inquiry and not (has_multiline or has_two_fields):
        twiml.message(
            "Hey there! 🚀 Welcome to the *AI Workshop Registration*.\n\n"
            "To secure your spot and grab your unique referral code, please reply with:\n\n"
            "👉 *Full Name*\n"
            "👉 *College / University*\n"
            "👉 *Referral Code* (Optional, if invited by a friend)\n\n"
            "💡 *Example:*\n"
            "Aarav Sharma\n"
            "IIT Bombay\n"
            "NXT-7K9M"
        )
        return Response(content=str(twiml), media_type="application/xml")

    # Case D: New Student Registration via OpenAI
    parsed = extract_with_openai(body_clean)
    name = parsed["name"] or ProfileName or "Student"
    college = parsed["college"] or "Engineering College"
    referred_by = (parsed["referred_by"] or "").strip().upper()

    # Generate unique 4-char code: NXT-XXXX
    existing_codes = {r.get("My_Referral_Code", "").upper() for r in records}
    my_code = generate_referral_code()
    while my_code.upper() in existing_codes:
        my_code = generate_referral_code()

    # Attribute viral referral if valid referrer exists
    if referred_by and referred_by != my_code:
        crm.increment_referral_count(referred_by)

    # Save to CRM
    crm.append_registration(
        phone=phone_clean,
        name=name,
        college=college,
        my_code=my_code,
        referred_by=referred_by
    )

    # Step 6 WhatsApp Response
    reply_msg = (
        f"Registration successful, {name}! 🎉\n\n"
        f"To unlock the 'Top 50 AI Interview Prompts', get 3 friends to register using your unique code: {my_code}"
    )
    twiml.message(reply_msg)
    return Response(content=str(twiml), media_type="application/xml")


# -----------------------------------------------------------------------------
# 7. Diagnostic & Asset Endpoints
# -----------------------------------------------------------------------------
@app.get("/", tags=["Health"])
@app.get("/health", tags=["Health"])
def health_check():
    """Health check for uptime monitors."""
    records = crm.get_all_records()
    return {
        "status": "healthy",
        "service": "AI Workshop WhatsApp Referral Engine",
        "crm_connected": crm._sheet is not None,
        "openai_configured": openai_client is not None,
        "total_registrations_in_memory": len(records),
        "target_sheet": GOOGLE_SHEET_NAME,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "campaign": {
            "target_referrals": 3,
            "reward": "Top 50 AI Interview Prompts",
            "code_prefix": "NXT-"
        }
    }


@app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
def get_dashboard_html():
    """Fallback HTML redirect/view for dashboard."""
    return HTMLResponse(
        content="""<!DOCTYPE html><html><head><title>AI Workshop Referral Command Center</title></head>
        <body style='background:#020617;color:#f8fafc;font-family:sans-serif;padding:2rem;'>
        <h2>AI Workshop Referral Command Center</h2>
        <p>React Frontend running on <a style='color:#38bdf8' href='http://localhost:5173'>http://localhost:5173</a></p>
        <p>API Docs: <a style='color:#38bdf8' href='/docs'>/docs</a></p>
        </body></html>"""
    )


@app.get("/reward/download", tags=["Reward"])
def download_reward():
    """Serves the 'Top 50 AI Interview Prompts' guide."""
    reward_file = os.path.join(os.path.dirname(__file__), "rewards", "TOP_50_AI_INTERVIEW_PROMPTS.md")
    if os.path.exists(reward_file):
        return FileResponse(
            path=reward_file,
            filename="Top_50_AI_Placement_Interview_Prompts.md",
            media_type="text/markdown"
        )
    return Response(
        content="# Top 50 AI Placement Interview Prompts\nUnlocked via NxtWave Referral Engine!",
        media_type="text/markdown"
    )


# -----------------------------------------------------------------------------
# 8. Mount Built React Frontend (If dist exists)
# -----------------------------------------------------------------------------
dist_path = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(dist_path):
    app.mount("/", StaticFiles(directory=dist_path, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
