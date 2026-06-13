Markdown

# OSINT-Utility V2 🕵️‍♂️✨

A professional, fully asynchronous, and modular Open Source Intelligence (OSINT) suite built with Python 3.10+ and a modern graphical interface. This platform integrates 10 specialized collection modules under strict production-grade software engineering standards.

---

## 🏗️ Architectural Core Features

This version marks the evolution from a collection of scripts into a robust desktop security tool, built around the following technical pillars:

- **Asynchronous Core (`asyncio`):** Entirely non-blocking event loops. Heavy network requests or intensive CLI subprocesses run concurrently on separate tasks, keeping the CustomTkinter GUI completely responsive.
- **Modular Plugin Architecture (`BaseModule`):** All analytical tools inherit strictly from an Abstract Base Class contract. This ensures rigorous parameter control, predefined execution pipelines, and seamless extensibility for future modules.
- **Secure Subprocessing (Bastion Guard):** External CLI binaries (such as Sherlock or PhoneInfoga) are invoked using native async executors. Arguments are passed strictly as sanitized lists, and `shell=True` is completely banned across the codebase to neutralize command injection vulnerabilities.
- **Granular Fault Isolation:** Banned generic `except Exception:` blocks. The application catches specific network exceptions (`httpx.HTTPStatusError`, `httpx.TimeoutException`), socket failures, and system-level input/output anomalies independently, ensuring a single failing endpoint never crashes the environment.
- **Streamlined Native Logging:** The legacy `print()` functions have been replaced by the native Python `logging` module. A custom Tkinter log handler intercepts execution logs in real-time, safely formatting and injecting them into the GUI console.

---

## 🛠️ Specialized Modules

| Category          | Module         | Technology / Target       | Description                                                                               |
| :---------------- | :------------- | :------------------------ | :---------------------------------------------------------------------------------------- |
| **Identities**    | `Holehe`       | Email OSINT               | Traces email registration footprints across hundreds of sites.                            |
|                   | `Sherlock`     | Username Tracking         | Correlates social media and forum accounts using exact handles.                           |
|                   | `PhoneInfoga`  | Phone Intel               | Advanced scanner for phone numbers leveraging external APIs.                              |
| **Network & Web** | `VirusTotal`   | Reputation Scan           | Passive reputation check via VirusTotal v3 API for IPs/domains.                           |
|                   | `WHOIS / DNS`  | Domain Records            | Async resolution of A, MX, and TXT entries alongside registrar metadata.                  |
|                   | `Subdomains`   | Infrastructure Map        | Discovers subdomains via crt.sh/HackerTarget and renders an interactive relational chart. |
|                   | `Port Scanner` | Passive Mapping           | Passive port scanning powered by Shodan InternetDB.                                       |
|                   | `HTTP Headers` | Server Hardening          | Evaluates security headers (HSTS, CSP, X-Frame-Options) and flags exposures.              |
|                   | `Wayback`      | Passive Timeline          | Crawls the internet archive database to locate the oldest indexed snapshot.               |
| **Forensics**     | `Metadata`     | Local Metadata Extraction | Context-managed metadata extraction from images (EXIF/GPS) and PDF records.               |

---

## 🚀 Deployment and Setup

### Prerequisites

- Linux Operating System (Ubuntu/Debian/Arch/Fedora)
- Python 3.10 or higher installed

### Automated Launch

The platform provides a secure bash script to handle dependency compilation and isolation automatically. Run the following commands in your terminal:

```bash
# 1. Clone the repository
git clone [https://github.com/G0rri/OSINT-Utility.git](https://github.com/G0rri/OSINT-Utility.git)
cd OSINT-Utility

# 2. Grant execution permissions and run the bootstrap script
chmod +x start.sh
./start.sh
```

    ⚙️ Behind the Scenes: start.sh provisions a virtual environment (venv), securely hooks pip within the isolated namespace, satisfies requirements (requirements.txt), verifies/fetches the PhoneInfoga Go binary, and safely launches the graphical central panel.

## 🔑 Secret and API Configuration

The application implements strict passive validation for development and production secrets. To make use of premium data streams, create a .env file in the root directory of the project:
Fragmento de código

# VirusTotal Configuration

VIRUSTOTAL_API_KEY=your_virustotal_api_key_here

# PhoneInfoga Scanner Enhancements

NUMVERIFY_API_KEY=your_numverify_key_here
APILAYER_KEY=your_apilayer_key_here

    ℹ️ Note: If the secrets are missing or unmodified, the core application will warn you through its logging routines but will maintain its initialization pipeline, gracefully setting the affected modules to an idle warning state (🟠/🔴) without crashing.

## ⚠️ Ethical Use Notice / Disclaimer

Strictly for authorized security testing, educational purposes, and defensive research. Utilizing this tool to gather intelligence against target entities without explicit prior consent may constitute an infringement of privacy regulations or computer abuse acts depending on your jurisdiction. The author and project contributors disclaim all liabilities for misapplication, damages, or illicit overhead incurred through this software stack.
