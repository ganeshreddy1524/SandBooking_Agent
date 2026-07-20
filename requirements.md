# Requirements Document: Sand Availability Notifier & AI Agent

## 1. Executive Summary
The goal of this project is to build an automated AI monitoring agent that continuously checks the Telangana Sand Sale Management System portal (Mana Isuka Vahanam - TGMIV) for sand stock availability, reach updates, and slot announcements for house construction. Upon detecting matching availability in target districts/villages, the system immediately alerts the user via Telegram and/or Email.

## 2. Problem Statement
In Telangana state, sand for residential house construction is booked online through the Mana Isuka Vahanam (TGMIV) portal (`https://tgmiv.cgg.gov.in/home`). Sand reaches and slot bookings are opened periodically and often close within 5 to 10 minutes due to high demand. Manual tracking is inefficient and unreliable, leading users to miss booking windows for their village/district.

## 3. Key Functional Requirements

### FR-1: Web Scraping & Portal Monitoring
- **FR-1.1**: The agent must inspect `https://tgmiv.cgg.gov.in/home` for active ticker announcements, marquee notices, reach updates, and status messages.
- **FR-1.2**: Support configurable polling intervals (e.g., every 60s, 300s, 600s).
- **FR-1.3**: Gracefully handle HTTP timeouts, network dropouts, SSL verification, and temporary server errors.

### FR-2: Keyword Filtering & Targeting
- **FR-2.1**: Filter announcements based on user-provided location keywords (e.g., district name, mandal name, reach name, or booking status keywords like Jagitial, Karimnagar, Lingapur, open, booking).
- **FR-2.2**: Allow case-insensitive matching in both English and Telugu text.

### FR-3: Notification Channels
- **FR-3.1 Telegram Integration**:
  - Support instant dispatch of alerts using Telegram Bot API (`sendMessage`).
  - Format messages with HTML styling, timestamp, matched keywords, and direct site URL.
- **FR-3.2 Email Integration**:
  - Support sending emails using standard SMTP (Gmail/Outlook/Custom).
  - Format email subject and body with clear notice context and direct portal link.

### FR-4: State Persistence & Deduplication
- **FR-4.1**: Maintain a local cache file (`seen_updates.json`) storing previously processed notices (by hash or raw text content).
- **FR-4.2**: Prevent duplicate notifications for the same notice across repeated polling cycles.

## 4. Non-Functional Requirements
- **NFR-1 Performance & Lightweight Design**: Low resource footprint; runnable on standard desktop, cloud VM, or Raspberry Pi.
- **NFR-2 Reliability**: Auto-resume and robust error handling to prevent script crashes on network failure.
- **NFR-3 Security**: Store sensitive API tokens, SMTP passwords, and chat IDs securely in environment configuration (`.env`).

## 5. System Architecture & Component Interactions

```
+-----------------------------+
| TGMIV Sand Booking Portal   |
| (tgmiv.cgg.gov.in/home)     |
+--------------+--------------+
               | (HTTP Request)
               v
+--------------+--------------+
| Sand Monitor Agent          |
| (monitor.py)                |
|  - HTML Parser (BS4)        |
|  - Keyword Filter Engine    |
|  - State Cache Manager      |
+------+---------------+------+
       |               |
       v               v
+------+------+ +------+------+
| Telegram    | | Email SMTP  |
| Bot Alert   | | Alert       |
+-------------+ +-------------+
```
