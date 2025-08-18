# API Reference – Veto System

This document describes the API endpoints available for interacting with the Veto System. All endpoints are served via REST and return JSON responses.

---

## Base URL

/api/

---

## Authentication

Currently, the API is publicly accessible for testing and development purposes. Authentication will be added in future versions.

---

## Endpoints

### 🔸 Create a New Series

**POST** `/api/series/`

Create a new veto series with two teams.

#### Request Body
```json
{
  "team_a": "Red Dragons",
  "team_b": "Blue Cobras"
}
```
Response
```json
{
  "id": 11,
  "team_a": "Red Dragons",
  "team_b": "Blue Cobras",
  "state": "idle",
  "created_at": "2025-08-17T02:53:49Z"
}

```

---

###🔸 Get Series Details

**GET** `/api/series/{id}/`

Returns the current state and transaction history of a series.


---

###🔸 Submit Action

**POST** `/api/series/{id}/action/`

Submit a veto or map/gametype selection.

Request Body
```json
{
  "type": "veto",
  "map": "Streets",
  "mode": "Oddball"
}
```

---

###🔸 Undo Last Action

**POST** `/api/series/{id}/undo/`

Undo the most recent action in the series.


---

###🔸 Reset Series

**POST** `/api/series/{id}/reset/`

Resets the entire series to its initial state.


---

###🔸 List Maps

**GET** `/api/maps/`

Returns a list of all available maps and supported gametypes.


---

###🔸 List Gametypes

**GET** `/api/gametypes/`

Returns a list of available game modes (e.g. Slayer, CTF, Strongholds).


---

### Status Codes

200 OK – Success

201 Created – Resource created

400 Bad Request – Invalid input

404 Not Found – Resource not found

422 Unprocessable Entity – Invalid state transition

500 Internal Server Error – Server error



---

Example Flow

1. POST /api/series/ → Create series


2. POST /api/series/{id}/action/ → Submit valid action


3. POST /api/series/{id}/undo/ → Undo previous action


4. POST /api/series/{id}/reset/ → Reset the series




---

Notes

All action requests are validated by the internal state machine and will return a 422 response if invalid for the current state.

Game modes are classified as is_objective: true/false in /gametypes/.



---

Last updated: August 17, 2025
