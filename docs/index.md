# Welcome to the Veto API Docs

A modular, scalable backend powering competitive match veto processes for Halo and beyond.

---

## 🚀 Overview

The **Veto API** is the backend source of truth for veto logic.  
It provides:

- ✅ **Series lifecycle management**: create, assign roles, confirm ruleset, reset/undo
- ⚙️ **TSDMachine state machine**: enforces strict turn order for bans and picks
- 🗺️ **Map & mode registry**: CRUD for maps, game modes, and legal combos
- 📊 **Action tracking**: every ban/pick is recorded and retrievable
- 🩺 **Health endpoint**: quick system status for monitoring

The frontend consumes these endpoints to render the veto UI and final series layout.

---

## 📁 Project Structure

```text
server/
├── veto/
│   ├── models.py       # Core models (Series, Map, GameMode, Round, Ban, Action)
│   ├── machine_tsd.py  # TSDMachine: enforces ban/pick sequencing
│   ├── views.py        # REST API viewsets & custom endpoints
│   ├── serializers.py  # DRF serializers (Series, Maps, Actions)
│   └── urls.py         # API routing
└── manage.py
```

---

## 🔗 How It Wires to the Frontend

* The **frontend never enforces rules** — it only calls API endpoints.
* State progression is handled by `TSDMachine` methods, exposed under `/api/series/{id}/...`.
* Every state update returns the current **Series state** (`state`, `turn`, `actions`) so the client can render the next step.
* Legal map/mode combinations are provided by `/api/maps/` and `/api/gamemodes/`.
* The **SeriesSerializer** merges bans, rounds, and actions for a complete veto history in one response.

---

## 📡 Key Endpoints

* `GET /api/health/` → API health & counts
* `GET /api/maps/` → list maps with supported modes
* `GET /api/combos/` → list available game modes
* `POST /api/series/` → create a new series
* `POST /api/series/{id}/action/` → submit ban/pick actions
* `POST /api/series/{id}/undo/` → undo last action
* `POST /api/series/{id}/reset/` → reset the series

---

## 🛠️ Tech Stack

* **Django + Django REST Framework** — API & admin
* **transitions** — finite state machine engine
* **SQLite/Postgres** — persistence
* **MkDocs Material** — documentation site

---

## 📚 Documentation

- **[API Reference](api.md)** — Complete endpoint documentation with examples
- **[Architecture](architecture.md)** — System design and state machine details

---

## 🚀 Quick Start

1. **Set up the backend**: Follow the installation guide in the project README
2. **Create test data**: Use the admin interface or API to add maps and game modes
3. **Start a series**: `POST /api/series/` with team names
4. **Execute veto**: Follow the ban/pick sequence using the action endpoint
5. **View results**: Get the complete series state with all actions

---

## 🔗 Related Projects

The Veto API is designed to work with modern frontend frameworks through its REST API interface.