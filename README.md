# Sand Availability Notifier & AI Agent

An automated, intelligent monitoring system for the **Telangana Sand Sale Management System portal (Mana Isuka Vahanam - TGMIV)**. The agent continuously checks the official portal (`https://tgmiv.cgg.gov.in/home`) for sand stock availability, reach updates, slot announcements, and Indiramma housing sand allocations. Upon detecting keyword matches for your district, mandal, or village, it immediately sends instant alerts via **Telegram** and/or **Email**.

---

## Features

- 🌐 **Automated Portal Scraping**: Inspects news tickers, marquees, reach announcements, and status notices on the TGMIV website.
- 🎯 **Location & Keyword Targeting**: Multi-keyword filtering supporting both **English** and **Telugu** (e.g., `Jagitial`, `Karimnagar`, `Lingapur`, `Korutla`, `open`, `booking`, `ఇసుక`, `బుకింగ్స్`).
- ⚡ **Instant Telegram Alerts**: Sends HTML-formatted messages with direct links to book sand instantly before slots close.
- 📧 **SMTP Email Alerts**: Sends clean, formatted emails with match context and direct action buttons.
- 💾 **Deduplication State Persistence**: Caches processed notices in `seen_updates.json` using SHA256 hashes to prevent redundant spam notifications.
- 🛡️ **Robust Fault Tolerance**: Auto-resumes on network drops, HTTP timeouts, or temporary portal down times.

---

## Quick Start Guide

### 1. Prerequisites

Make sure Python 3.8+ is installed on your system.

Install required dependencies:

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` with your custom preferences:

```ini
# Target Portal URL
TARGET_URL=https://tgmiv.cgg.gov.in/home

# Comma-separated target keywords (district, mandal, village, reach name)
KEYWORDS=Jagitial,Karimnagar,Lingapur,Korutla,open,booking,ఇసుక,బుకింగ్స్

# Monitoring Interval in seconds (default: 300s / 5 min)
CHECK_INTERVAL_SECONDS=300

# Telegram Credentials
ENABLE_TELEGRAM=true
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
TELEGRAM_CHAT_ID=987654321

# Email Credentials (Optional)
ENABLE_EMAIL=false
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_TO=recipient@gmail.com
```

---

## Telegram Bot Setup Guide

1. Open Telegram and search for `@BotFather`.
2. Send `/newbot` and follow the prompts to create your bot and receive your `TELEGRAM_BOT_TOKEN`.
3. Start a chat with your new bot (or add it to a channel/group) and send any message.
4. Obtain your `TELEGRAM_CHAT_ID` by visiting:
   `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
5. Place both values into `.env` and set `ENABLE_TELEGRAM=true`.

---

## Usage Modes

### 1. Test / Single Check Run Mode (`--once`)

Runs a single check against the portal, updates the state cache, and exits:

```bash
python monitor.py --once
```

### 2. Dry Run / Test Mode (`--test`)

Parses the live site and displays matching announcements in console **without saving to state cache** or sending duplicate alerts:

```bash
python monitor.py --once --test
```

### 3. Daemon Mode (Continuous Background Monitoring)

Runs continuously, polling the portal at the configured interval (`CHECK_INTERVAL_SECONDS`):

```bash
python monitor.py
```

Override polling interval on the fly (e.g., every 60 seconds during peak slot opening times around 3:00 PM):

```bash
python monitor.py --interval 60
```

---

## Project Structure

```
SandBooking_Agent/
├── monitor.py           # Core agent logic: scraper, keyword engine, state cache, notifier
├── requirements.txt     # Python package dependencies
├── requirements.md      # Functional & Non-functional requirements specification
├── .env.example         # Template for environment configuration
├── .env                 # Active configuration file
├── seen_updates.json    # Deduplication cache storing seen notice hashes
├── sand_monitor.log     # Execution and alert audit logs
└── README.md            # User guide and documentation
```

---

---

## ☁️ GitHub Actions 24/7 Free Cloud Setup Guide

You can run this agent on **GitHub Actions for FREE** so it checks the website automatically every day (at **8:00 AM IST** and during peak slot release at **2:45 PM, 3:00 PM, and 3:15 PM IST**) even when your laptop is completely turned OFF!

### Step 1: Create a GitHub Repository
1. Go to [github.com/new](https://github.com/new) and create a repository named `SandBooking_Agent`.
2. Push your project files to GitHub:
   ```bash
   git init
   git add .
   git commit -m "Initial commit for Sand Availability Agent"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/SandBooking_Agent.git
   git push -u origin main
   ```

### Step 2: Add Secrets on GitHub
To keep your Telegram bot credentials secure:
1. Go to your GitHub Repository -> **Settings** -> **Secrets and variables** -> **Actions**.
2. Click **New repository secret**:
   - `TELEGRAM_BOT_TOKEN`: `8888583463:AAFJz234Cqz4ayoMFzJlsfcoZVVWRGsPqks`
   - `TELEGRAM_CHAT_ID`: `1311432483`

### Step 3: Trigger Manually anytime
1. Go to your repository's **Actions** tab on GitHub.
2. Click **Telangana Sand Availability Monitor** workflow.
3. Click **Run workflow** -> **Run workflow**.

GitHub will now execute the check automatically at **8:00 AM IST** every morning and around **3:00 PM IST** every afternoon!

