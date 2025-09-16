
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

The frontend ([**veto-tsd**](https://github.com/netteNz/veto-tsd)) consumes these endpoints to render the veto UI and final series layout.

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
* Legal map/mode combinations are provided by `/api/maps/combos/` and `/api/maps/combos/grouped/`.
* The **SeriesSerializer** merges bans, rounds, and actions for a complete veto history in one response.

---

## 📡 Key Endpoints

* `GET /api/health/` → API health & counts
* `GET /api/maps/` → list maps with supported modes
* `GET /api/maps/combos/` → flat list of allowed map × mode pairs
* `POST /api/series/` → create a new series
* `POST /api/series/{id}/assign_roles/` → assign team names
* `POST /api/series/{id}/confirm_tsd/` → lock series type (Bo3/Bo5/Bo7)
* `POST /api/series/{id}/ban_objective_combo/` → ban an objective mode/map
* `POST /api/series/{id}/ban_slayer_map/` → ban a Slayer map
* `POST /api/series/{id}/pick_objective_combo/` → pick objective mode/map
* `POST /api/series/{id}/pick_slayer_map/` → pick a Slayer map
* `POST /api/series/{id}/undo/` → undo last action
* `POST /api/series/{id}/reset/` → reset the series

---

## 🛠️ Tech Stack

* **Django + Django REST Framework** — API & admin
* **transitions** — finite state machine engine
* **SQLite/Postgres** — persistence
* **MkDocs Material** — documentation site

---

## 🌐 Related Projects

* [Frontend: veto-tsd](https://github.com/netteNz/veto-tsd) — React + Vite client