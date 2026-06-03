# Fampay User Information Disclosure PoC

**Developer:** Syed Rehan

---

## 📌 Overview

This repository demonstrates a security research proof-of-concept (PoC) for an information disclosure vulnerability discovered in the Fampay backend system.

Using only a target user's **Fampay UPI ID**, this tool extracts their **phone number**, **name**, and **UPI ID** — information that is not visible in the official Fampay application under normal circumstances.

---

## 🔍 Vulnerability Summary

**Issue:** Information Disclosure via Block/Unblock API Endpoint

**Affected Platform:** Fampay

**Impact:** An attacker can retrieve a user's phone number and name using only their UPI ID.

**Root Cause:** When User A blocks User B on Fampay, the backend response contains User B's complete metadata (including phone number) even though the frontend does not display it.

---

## ⚙️ How It Works

The exploit follows this automated flow:

```

1. User provides target Fampay UPI ID
   ↓
2. Script sends a BLOCK request to Fampay API
   ↓
3. Fampay backend returns user details (name, phone, UPI)
   ↓
4. Script captures and displays the exposed information
   ↓
5. Script instantly sends UNBLOCK request
   ↓
6. Target user is unaware of any action

```

> ✅ The target is blocked for less than one second — no permanent change is made to their account.

---

## 🛠️ Technical Implementation

| Step | Method |
|------|--------|
| App Analysis | Reverse engineered and patched the official Fampay Android app |
| Traffic Capture | Intercepted and analyzed internal API requests/responses |
| Automation | Built a custom API wrapper to replicate block → capture → unblock sequence |

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Home page with API information and usage guide |
| GET | `/get-number?id=username@fam` | Main endpoint — extracts phone number, name, and UPI ID from target UPI ID |
| GET | `/auth-test` | Test authentication status with Fampay backend |
| GET | `/blocked` | View currently blocked users list |
| GET | `/credits` | Credits and developer information |
| GET | `/health` | Health check — verify API service status |

---

## 📥 Input / Output Example

**Request:**
```

GET /get-number?id=john_doe@fam

```

**Response:**
```json
{
  "status": "success",
  "data": {
    "name": "John Doe",
    "phone_number": "+919876543210",
    "upi_id": "john_doe@fam"
  }
}
```

Error Response:

```json
{
  "status": "error",
  "message": "Invalid UPI ID or user not found"
}
```

---

🚀 Purpose

This project was created exclusively for:

· Security research and vulnerability analysis
· Educational demonstration of API information disclosure
· Responsible disclosure awareness

---

⚠️ Disclaimer

This tool is for educational and research purposes only.

· Do not use this against real users without explicit permission.
· The developer does not condone unauthorized data collection, privacy violations, or harassment.
· You are solely responsible for how you use this code.
· Respect Fampay's Terms of Service and applicable laws.

---

📢 Responsible Disclosure

This vulnerability was discovered during authorized research.
If you are a representative of Fampay and would like this repository removed or further details disclosed privately, please reach out.

---

👨‍💻 Developer

Syed Rehan
Security Researcher

---

💔 Patched 

Not working anymore 
Fampay fix there bug 

---
