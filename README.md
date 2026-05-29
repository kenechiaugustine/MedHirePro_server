# 🩺 MedHirePro Backend Server

[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.0%2B-47A248.svg)](https://www.mongodb.com/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Welcome to the backend engine of **MedHirePro**—a robust, high-performance staffing and hiring platform tailored specifically for the healthcare sector. Built on a state-of-the-art asynchronous architecture, this API leverages **FastAPI**, **MongoDB (via Motor driver)**, and **Docker** to provide a secure, fast, and scalable service layer that connects medical professionals with healthcare institutes.

---

## 📌 Table of Contents

- [🚀 Key Architecture & Highlights](#-key-architecture--highlights)
- [🛠️ Technology Stack](#️-technology-stack)
- [💻 Local Development Setup](#-local-development-setup)
  - [Option 1: Manual Virtualenv Run](#option-1-manual-virtualenv-run)
  - [Option 2: Docker Compose (Recommended)](#option-2-docker-compose-recommended)
- [📜 License](#-license)

---

## 🚀 Key Architecture & Highlights

- **⚡ Lightning-Fast Asynchronous Processing**: Built entirely around Python's `async/await` paradigm, utilizing `AsyncIO` and `Motor` to handle heavy parallel traffic without blocking the event loop.
- **👥 Flexible Dual-Role Onboarding**: Tailored sign-up paths and business logic constraints for both **Medical Professionals** and **Healthcare Institutes**.
- **🛡️ Premium Security & Sessions**: State-of-the-art JWT architecture featuring access and refresh token pairings with secure client authentication under FastAPI's `HTTPBearer` scheme. Secure password hashing is implemented using `passlib[bcrypt]`.
- **🌐 Seamless Google OAuth SSO**: Server-side verified single sign-on (SSO) and registration using Google Client tokens. Automatically registers new OAuth profiles while preventing duplication.
- **💰 Transactional Credits System (Ledger Model)**:
  - **Welcome Bonus**: Awards a default sign-up bonus of **2 credits** to new users.
  - **Daily & Social Caps**: Rolling 24-hour daily limits (default **20 credits** limit for `daily` tasks, **1 claim** per 24 hours for `socials` tasks) to block bot abuse.
  - **Atomic Integrity**: Credits spending is done atomically in MongoDB (`$gte` balance checks paired with `$inc` operations) to prevent race conditions or double-spending vulnerabilities.
- **🧹 Compliance-Ready Soft Deletion**: Provides secure soft-deletion workflows (`DELETE /me`). Rather than permanently wiping documents which breaks audit trails, it disables the profile, clears all historical transaction logs to protect user PII, and resets the credit balance to the initial signup state.
- **📈 Self-Optimizing Database**: Automatic startup scripts trigger creation of essential indexes (unique email constraints and descending timestamp logs) to keep query latencies low.

---

## 🛠️ Technology Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Language** | Python 3.12 | Modern, strongly-typed backend execution environment. |
| **Framework** | FastAPI | High-performance ASGI framework featuring automatic OpenAPI documentation. |
| **Database** | MongoDB 7.0+ | Scalable, high-throughput document store. |
| **DB Driver** | Motor | Asynchronous MongoDB driver wrapping PyMongo. |
| **Auth & Sessions**| PyJWT / jose | Session management, signature validation, and secure token claims. |
| **Passwords** | passlib[bcrypt] | Cryptographic password salting and hashing. |
| **OAuth 2.0** | google-auth | Secure identity verification directly via Google token endpoints. |
| **Config** | Pydantic Settings | Strongly-typed environment variables validation. |
| **Server** | Uvicorn | Lightweight, production-ready ASGI web server. |
| **Containers** | Docker & Compose | Multi-stage Docker builds and unified container orchestration. |

---

## 💻 Local Development Setup

### Option 1: Manual Virtualenv Run

Make sure you have **Python 3.12** and **MongoDB 7.0** running locally.

1. **Clone the repository and enter the directory:**
   ```bash
   git clone <repo-url> medhirepro-server
   cd medhirepro-server
   ```

2. **Initialize and activate a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Upgrade package managers and install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Verify environment setup:**
   Make sure you have created your `.env` from the `.env.example` blueprint.

5. **Fire up the ASGI development server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
   ```
   > [!TIP]
   > The `--reload` flag continuously monitors file changes and triggers instant reloading upon save.

### Option 2: Docker Compose (Recommended)

Requires only **Docker** and **Docker Compose** installed. This runs the app and a MongoDB instance inside an isolated virtual network with zero host dependencies.

1. **Build images and launch services:**
   ```bash
   docker-compose up --build
   ```

2. **Endpoints & Hot-Reload**:
   - The API will be active at `http://localhost:8080`.
   - Complete interactive OpenAPI documentation is generated instantly at `http://localhost:8080/docs`.
   - Workspace directories are mounted live; local file modifications trigger hot-reloading inside the running containers.
   - The database persists its data state inside a local Docker volume.

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for more information (if applicable).