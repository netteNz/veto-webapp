# 🎮 Halo Veto System – Veto WebApp

A modern web-based veto system for competitive Halo matchups. This tool streamlines the **map and gametype veto process** between two teams with a clear, structured, and audit-friendly design.

Built with:
- 🔧 Django REST Framework (backend)
- ⚛️ React + TailwindCSS + Vite (frontend)

---

## 🚀 Project Overview

This app allows teams to:

- Initialize a competitive series (Bo3, Bo5, etc.)
- Take turns vetoing map+mode combinations (Objective and Slayer)
- Track and visualize veto steps in real time
- Reset or undo actions during the veto phase
- Export final match layout

---

## 🧠 Design Philosophy

This project was built with the following principles:

- **Backend-first logic** – all game logic lives on the server, not in the UI.
- **Minimal transaction design** – atomic, RESTful endpoints drive every step.
- **Clear UX** – the user sees only what they need to act on.
- **Auditable steps** – full transparency for each veto action.

📖 Learn more: [docs/philosophy.md](docs/philosophy.md)

---

## 🧱 Architecture

```plaintext
veto-webapp/
├── server/             # Django backend
│   ├── api/            # DRF logic and views
│   └── veto/           # Models and business logic
├── docs/               # System documentation
│   ├── index.md
│   ├── philosophy.md
│   ├── architecture.md
│   └── api.md
└── README.md
```

📚 Full breakdown: docs/architecture.md

---

📦 Setup & Development

🔧 Backend

```bash
cd server/
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```
---

📬 REST API Overview

Each transaction is step-based and RESTful.

```plaintext
	•	POST /series/ – create a new series
	•	GET /series/:id/state/ – fetch current veto state
	•	POST /series/:id/veto/ – submit a veto
	•	POST /series/:id/undo/ – undo last action
	•	POST /series/:id/reset/ – reset entire flow
```

📘 Full API Reference: docs/api.md

---

🛣️ Roadmap
	•	Finalize frontend veto sequence flow
	•	Add Discord integration (modals for teams)
	•	Export series to image or embed
	•	Admin dashboard for tournament managers
	•	GitHub Pages docs deployment

---

🤝 Contributing

Pull requests and forks are welcome! Feel free to open issues or feature requests.

---

🪪 License

This project is licensed under the MIT License. See LICENSE for details.