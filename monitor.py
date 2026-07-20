#!/usr/bin/env python3
"""
Sand Availability Notifier & AI Agent
-------------------------------------
Monitors the Telangana Sand Sale Management System portal (Mana Isuka Vahanam)
for sand stock availability, reach updates, and slot announcements.
Alerts users via Telegram and/or Email when matching keywords are detected.
"""

import os
import sys
import json
import time
import hashlib
import logging
import argparse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Tuple, Dict, Set, Optional

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment configuration from .env file
load_dotenv()

# Ensure stdout handles UTF-8 characters (Telugu script and Emojis) on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Configure Logging
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("sand_monitor.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("SandMonitor")

# Configuration Constants
DEFAULT_TARGET_URL = "https://tgmiv.cgg.gov.in/home"
TARGET_URL = os.getenv("TARGET_URL", DEFAULT_TARGET_URL)
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))
CACHE_FILE = os.getenv("CACHE_FILE", "seen_updates.json")

# Keywords
RAW_KEYWORDS = os.getenv("KEYWORDS", "Jagitial,Karimnagar,Lingapur,Korutla,open,booking,ఇసుక,బుకింగ్స్")
KEYWORDS = [k.strip() for k in RAW_KEYWORDS.split(",") if k.strip()]

# Telegram Settings
ENABLE_TELEGRAM = os.getenv("ENABLE_TELEGRAM", "false").lower() == "true"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# Email Settings
ENABLE_EMAIL = os.getenv("ENABLE_EMAIL", "false").lower() == "true"
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
EMAIL_TO = os.getenv("EMAIL_TO", "").strip()

# User Agent Header for Requests
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,te;q=0.8",
}


class StateCache:
    """Manages persistence of seen announcements to prevent duplicate notifications."""

    def __init__(self, filepath: str = CACHE_FILE):
        self.filepath = filepath
        self.seen_data: Dict[str, dict] = self._load()

    def _load(self) -> Dict[str, dict]:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load state cache file {self.filepath}: {e}")
                return {}
        return {}

    def save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.seen_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save state cache to {self.filepath}: {e}")

    def get_hash(self, text: str) -> str:
        """Computes SHA256 hash of normalized announcement text."""
        normalized = " ".join(text.lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def is_seen(self, text: str) -> bool:
        notice_hash = self.get_hash(text)
        return notice_hash in self.seen_data

    def add(self, text: str, matched_keywords: List[str]):
        notice_hash = self.get_hash(text)
        self.seen_data[notice_hash] = {
            "text": text,
            "matched_keywords": matched_keywords,
            "first_seen": datetime.now().isoformat()
        }
        self.save()


def fetch_announcements(url: str = TARGET_URL) -> List[str]:
    """
    Fetches the TGMIV homepage and extracts text announcements from tickers,
    marquees, lists, and main notification elements.
    """
    logger.info(f"Fetching portal updates from {url}...")
    try:
        response = requests.get(url, headers=HEADERS, timeout=20, verify=True)
        logger.info(f"Portal HTTP Response Code: {response.status_code}")
        response.raise_for_status()
        response.encoding = "utf-8"
    except requests.RequestException as e:
        logger.error(f"Network error fetching portal content: {e}")
        # If running in automated environments, alert if portal is unreachable/blocked
        if ENABLE_TELEGRAM and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            try:
                err_msg = f"⚠️ <b>Sand Agent Alert:</b> Unable to reach TGMIV portal from server IP ({e})."
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={"chat_id": TELEGRAM_CHAT_ID, "text": err_msg, "parse_mode": "HTML"},
                    timeout=5
                )
            except Exception:
                pass
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    announcements: Set[str] = set()

    # 1. Inspect Marquee and Ticker Elements
    for elem in soup.find_all(["marquee", "div", "ul", "ol"], class_=lambda c: c and any(k in c.lower() for k in ["ticker", "marquee", "notice", "news", "announcement"])):
        for item in elem.find_all(["li", "p", "a", "span"]):
            text = item.get_text(strip=True)
            if len(text) > 15:  # Filter out tiny nav labels
                announcements.add(text)

    # 2. Inspect List Items across the page that contain reach or sand info
    for li in soup.find_all("li"):
        text = li.get_text(separator=" ", strip=True)
        if any(term in text.lower() or term in text for term in ["reach", "booking", "sand", "మండలం", "జిల్లా", "రీచ్", "బుకింగ్"]):
            announcements.add(text)

    # 3. Direct Anchor Text (links containing announcements)
    for a in soup.find_all("a"):
        text = a.get_text(separator=" ", strip=True)
        if any(term in text.lower() or term in text for term in ["reach", "booking", "sand", "మండలం", "జిల్లా", "రీచ్", "బుకింగ్"]):
            if len(text) > 20:
                announcements.add(text)

    # Clean up results
    cleaned_announcements = []
    for ann in announcements:
        # Collapse extra whitespaces
        clean_text = " ".join(ann.split())
        if len(clean_text) >= 20:
            cleaned_announcements.append(clean_text)

    logger.info(f"Extracted {len(cleaned_announcements)} total portal announcement items.")
    return cleaned_announcements


def matches_keywords(text: str, keywords: List[str] = KEYWORDS) -> Tuple[bool, List[str]]:
    """
    Checks if announcement text contains any of the target keywords (case-insensitive).
    Supports English and Telugu text.
    """
    text_lower = text.lower()
    matched = []
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in text_lower or kw in text:
            matched.append(kw)
    return (len(matched) > 0, matched)


def send_telegram_alert(notice_text: str, matched_keywords: List[str]):
    """Dispatches instant notification via Telegram Bot API."""
    if not ENABLE_TELEGRAM:
        logger.debug("Telegram notification disabled in configuration.")
        return

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram enabled but TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing.")
        return

    keywords_str = ", ".join([f"<code>{kw}</code>" for kw in matched_keywords])
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    message_html = (
        f"🚨 <b>SAND AVAILABILITY ALERT</b> 🚨\n\n"
        f"📍 <b>Matched Keywords:</b> {keywords_str}\n"
        f"🕒 <b>Detected At:</b> {timestamp}\n\n"
        f"📢 <b>Announcement Notice:</b>\n"
        f"<i>{notice_text}</i>\n\n"
        f"🔗 <a href='{TARGET_URL}'>Open Mana Isuka Vahanam Portal</a>"
    )

    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message_html,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    try:
        resp = requests.post(telegram_url, json=payload, timeout=10)
        resp_json = resp.json()
        if resp_json.get("ok"):
            logger.info("✅ Telegram alert sent successfully.")
        else:
            logger.error(f"Telegram API Error: {resp_json.get('description')}")
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")


def send_email_alert(notice_text: str, matched_keywords: List[str]):
    """Dispatches formatted email notification using standard SMTP."""
    if not ENABLE_EMAIL:
        logger.debug("Email notification disabled in configuration.")
        return

    if not SMTP_USER or not SMTP_PASSWORD or not EMAIL_TO:
        logger.warning("Email enabled but SMTP_USER, SMTP_PASSWORD, or EMAIL_TO missing.")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = f"🚨 Sand Slot Alert: Matched [{', '.join(matched_keywords)}]"

    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px;">
          <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
            🚨 Sand Stock / Slot Availability Alert
          </h2>
          <p><strong>Matched Keywords:</strong> <span style="background-color: #f39c12; color: #fff; padding: 3px 8px; border-radius: 4px;">{', '.join(matched_keywords)}</span></p>
          <p><strong>Detection Time:</strong> {timestamp}</p>
          <hr style="border: 0; border-top: 1px solid #eee;">
          <h3>Announcement Notice:</h3>
          <blockquote style="background: #f9f9f9; border-left: 5px solid #3498db; margin: 10px 0; padding: 10px 15px; font-style: italic;">
            {notice_text}
          </blockquote>
          <p style="margin-top: 20px;">
            <a href="{TARGET_URL}" style="background-color: #27ae60; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">
              Book Sand Now on Portal
            </a>
          </p>
        </div>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, EMAIL_TO, msg.as_string())
        logger.info(f"✅ Email alert sent successfully to {EMAIL_TO}.")
    except Exception as e:
        logger.error(f"Failed to send Email alert: {e}")


def extract_karimnagar_summary(announcements: List[str]) -> str:
    """Extracts all notice strings relevant to Karimnagar to track overall section diffs."""
    karimnagar_items = []
    for ann in announcements:
        if any(kw.lower() in ann.lower() or kw in ann for kw in ["karimnagar", "కరీంనగర్", "lingapur", "లింగాపూర్", "korekal", "కోరేకల్", "saidapur", "సైదాపూర్"]):
            karimnagar_items.append(ann.strip())
    karimnagar_items.sort()
    return " | ".join(karimnagar_items)


def check_and_notify(cache: StateCache, test_mode: bool = False) -> int:
    """
    Scrapes portal, runs keyword matching, tracks Karimnagar section changes, checks cache, and fires alerts.
    Returns the count of new matching notices found.
    """
    logger.info(f"Running monitoring check against {TARGET_URL}...")
    announcements = fetch_announcements(TARGET_URL)
    new_alerts_count = 0

    # 1. Track overall Karimnagar Reach Section changes
    karimnagar_summary = extract_karimnagar_summary(announcements)
    if karimnagar_summary:
        summary_hash = hashlib.sha256(karimnagar_summary.encode("utf-8")).hexdigest()
        previous_hash = cache.seen_data.get("_karimnagar_section_hash", {}).get("hash", "")
        
        if summary_hash != previous_hash and not test_mode:
            logger.info("🔥 KARIMNAGAR REACH CONTENT / STATUS CHANGE DETECTED!")
            change_notice = f"📢 <b>KARIMNAGAR PORTAL SECTION UPDATED:</b>\n{karimnagar_summary}"
            send_telegram_alert(change_notice, ["Karimnagar Update"])
            cache.seen_data["_karimnagar_section_hash"] = {
                "hash": summary_hash,
                "summary": karimnagar_summary,
                "last_updated": datetime.now().isoformat()
            }
            cache.save()

    # 2. Individual notice match check
    for notice in announcements:
        is_match, matched_kws = matches_keywords(notice, KEYWORDS)
        if is_match:
            if not cache.is_seen(notice) or test_mode:
                logger.info(f"🔥 NEW MATCH DETECTED! Keywords: {matched_kws}")
                logger.info(f"   Notice: {notice}")

                if not test_mode:
                    cache.add(notice, matched_kws)

                # Send Alerts
                send_telegram_alert(notice, matched_kws)
                send_email_alert(notice, matched_kws)
                new_alerts_count += 1
            else:
                logger.debug(f"Skipping previously seen notice (hash match): {notice[:40]}...")

    if new_alerts_count == 0:
        logger.info("No new matching sand availability announcements found in this run.")
    else:
        logger.info(f"Completed run: Dispatched {new_alerts_count} new alert(s).")

    return new_alerts_count


def get_dynamic_interval(default_interval: int) -> int:
    """
    Returns high-frequency interval (40 seconds) during peak afternoon slot release hours
    around 3:00 PM (14:45 to 15:45 IST), otherwise returns default_interval.
    """
    now = datetime.now()
    if (now.hour == 14 and now.minute >= 45) or (now.hour == 15 and now.minute <= 45):
        logger.info("⚡ PEAK SLOT HOUR DETECTED (around 3:00 PM)! High-frequency polling active (40s).")
        return min(default_interval, 40)
    return default_interval


def main():
    parser = argparse.ArgumentParser(description="Telangana Sand Availability Notifier AI Agent")
    parser.add_argument("--once", action="store_true", help="Run a single check and exit immediately")
    parser.add_argument("--interval", type=int, help="Override polling interval in seconds")
    parser.add_argument("--test", action="store_true", help="Run in test mode (prints matches without updating state cache)")
    args = parser.parse_args()

    default_interval = args.interval if args.interval else CHECK_INTERVAL_SECONDS
    cache = StateCache(CACHE_FILE)

    logger.info("==================================================")
    logger.info("   Telangana Sand Availability Notifier Agent     ")
    logger.info("==================================================")
    logger.info(f"Target URL       : {TARGET_URL}")
    logger.info(f"Target Keywords  : {KEYWORDS}")
    logger.info(f"Telegram Enabled : {ENABLE_TELEGRAM}")
    logger.info(f"Email Enabled    : {EMAIL_TO if ENABLE_EMAIL else 'False'}")
    logger.info(f"Cache File       : {CACHE_FILE}")

    if args.once:
        logger.info("Mode: Single Execution (--once)")
        check_and_notify(cache, test_mode=args.test)
        sys.exit(0)

    logger.info(f"Mode: Smart Daemon Polling (Normal: {default_interval}s | Peak 3 PM: 40s)")
    try:
        while True:
            current_interval = get_dynamic_interval(default_interval)
            try:
                check_and_notify(cache, test_mode=args.test)
            except Exception as e:
                logger.error(f"Unexpected error in check loop: {e}", exc_info=True)

            logger.info(f"Sleeping for {current_interval} seconds until next check...")
            time.sleep(current_interval)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down Sand Availability Notifier Agent. Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
