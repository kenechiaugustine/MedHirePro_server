# 🩺 MedHirePro Backend Server

[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.0%2B-47A248.svg)](https://www.mongodb.com/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Welcome to the backend repository of **MedHirePro**—a robust, modern staffing and hiring web application tailored specifically for the healthcare industry. Built on a cutting-edge asynchronous stack featuring **FastAPI**, **MongoDB (via Motor)**, and containerized with **Docker**, this API serves as the powerful engine driving seamless interactions between medical professionals and healthcare institutes.

---

## 🚀 Key Highlights & Architecture

- **Lightning-Fast Async Stack**: Engineered fully with Python's asynchronous features using `AsyncIO` and `Motor` to handle high concurrent loads.
- **Dual-Role Onboarding**: Tailored sign-up flows for **Medical Professionals** and **Healthcare Institutes**.
- **Secure JWT Session Flow**: State-of-the-art authentication using secure JWT Access and Refresh Tokens, plus secure password hashing via `passlib[bcrypt]`.
- **Google OAuth Integration**: Direct, server-side verified registration and single-sign-on using Google OAuth credentials.
- **Robust Transactional Credits System**: 
  - Dual welcome bonuses of credits upon registration.
  - Rolling 24-hour daily earning limits to prevent bot exploitation.
  - One-time-per-24h social claim verification.
  - Atomic transactions using MongoDB updates to guarantee balance consistency under race conditions.
- **Soft Account Deletion**: Strict privacy compliance. Soft deleting an account clears the user's credit transactions history while maintaining database integrity.
- **Auto-Configured DB Performance**: Collections index initialization executed automatically on system startup to guarantee high-performance query operations.

---

## 🛠️ Technology Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Language** | Python 3.12 | Modern, typed, fast backend environment |
| **Framework** | FastAPI | High-performance ASGI framework for building APIs |
| **Database** | MongoDB (7.0) | High-throughput, scalable Document DB |
| **DB Driver** | Motor | Asynchronous Python driver for MongoDB |
| **Auth & Security** | PyJWT/jose & bcrypt | Session management, password hashing, and token signatures |
| **OAuth** | google-auth | Secure identity verification directly via Google APIs |
| **Settings** | Pydantic-Settings | Strongly-typed environment configuration management |
| **Server** | Uvicorn | High-performance ASGI web server |
| **Containers** | Docker & Compose | Multi-stage production builds and zero-config local development |

---

## 💻 Local Development Setup

### Option 1: Manual Run
Ensure you have **Python 3.12** and **MongoDB** running locally.

1. **Clone and navigate to the repository:**
   ```bash
   git clone <repo-url> medhirepro-server
   cd medhirepro-server
   ```

2. **Initialize and activate virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Start the server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   > [!TIP]
   > The `--reload` flag watches the files in the codebase and restarts the server automatically whenever you save edits.

### Option 2: Docker Compose (Recommended)
You only need Docker installed. Run the command below to start the services in unified networks:

```bash
docker-compose up --build
```

- **Hot-Reload Support**: Code editing locally will automatically synchronize into the container.
- **Database Mapping**: Local MongoDB port is mapped to avoid port clashes with any local MongoDB instances already running on your machine.

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for more information (if applicable).