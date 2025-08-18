# Welcome to the Veto WebApp Docs

A modular, scalable, and API-driven application built to streamline competitive match veto processes for games like Halo and beyond.

---

## 🚀 Overview

Veto WebApp allows teams to interactively select game modes and maps through a structured, rule-based series system. It supports:

- ✅ RESTful API for series and game management
- ⚙️ State machine-based flow enforcement (TSD Machine)
- 🖥️ Admin interface for match oversight
- 🌐 React-based frontend for intuitive user interaction

---

## 📁 Project Structure

```text
.
├── client/         # Frontend (React, Tailwind, etc.)
├── server/         # Django backend
│   ├── api/        # API endpoints
│   └── veto/       # Core logic and state machine
├── docs/           # Documentation site (you're here!)
├── mkdocs.yml      # MkDocs config
└── requirements.txt
```