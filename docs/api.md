# API Reference – Veto System

This document describes the REST API endpoints for the HCS-style veto system. The API enforces proper ban/pick sequences through a finite state machine and validates all actions server-side.

---

## 📋 Table of Contents

- [Base Configuration](#-base-configuration)
- [Authentication](#-authentication)
- [Response Format](#-response-format)
- [Series Management](#-series-management)
- [Veto Actions](#-veto-actions)
- [Administrative Actions](#-administrative-actions)
- [Resource Endpoints](#-resource-endpoints)
- [Error Handling](#-error-handling)
- [Workflow Examples](#-workflow-examples)

---

## 🔧 Base Configuration

**Base URL:** `/api/`

**Content-Type:** `application/json`

**Rate Limiting:** None (development)

**API Version:** v1

---

## 🔐 Authentication

Currently, the API is publicly accessible for testing and development purposes. 

**Future Implementation:**
- Token-based authentication
- Team-based permissions
- Role-based access control

---

## 📨 Response Format

### Success Response Structure
```json
{
  "id": 123,
  "data": { /* resource data */ },
  "meta": {
    "timestamp": "2025-09-16T14:30:00Z",
    "api_version": "v1"
  }
}
```

### Error Response Structure
```json
{
  "error": {
    "code": "INVALID_TRANSITION",
    "message": "Cannot ban during PICK_WINDOW phase",
    "details": {
      "current_state": "PICK_WINDOW",
      "expected_action": "pick",
      "provided_action": "ban"
    }
  },
  "meta": {
    "timestamp": "2025-09-16T14:30:00Z",
    "request_id": "req_abc123"
  }
}
```

---

## 🎮 Series Management

### Create New Series

**POST** `/api/series/`

Creates a new veto series and initializes the state machine.

#### Request Body
```json
{
  "team_a": "Red Dragons",
  "team_b": "Blue Cobras",
  "series_type": "Bo5"  // Optional: "Bo3", "Bo5", "Bo7"
}
```

#### Response (201 Created)
```json
{
  "id": 42,
  "team_a": "Red Dragons",
  "team_b": "Blue Cobras",
  "state": "IDLE",
  "series_type": null,
  "current_turn": null,
  "ban_index": 0,
  "round_index": 0,
  "created_at": "2025-09-16T14:30:00Z",
  "actions": [],
  "bans": [],
  "rounds": []
}
```

---

### Get Series Details

**GET** `/api/series/{id}/`

Returns the complete state of a series including all actions, bans, and rounds.

#### Response (200 OK)
```json
{
  "id": 42,
  "team_a": "Red Dragons",
  "team_b": "Blue Cobras",
  "state": "BAN_PHASE",
  "series_type": "Bo5",
  "current_turn": {
    "team": "A",
    "action": "BAN",
    "kind": "OBJECTIVE_COMBO"
  },
  "ban_index": 2,
  "round_index": 0,
  "created_at": "2025-09-16T14:30:00Z",
  "updated_at": "2025-09-16T14:35:00Z",
  "actions": [
    {
      "id": 1,
      "step": 1,
      "action_type": "ban",
      "team": "A",
      "map": 5,
      "mode": 2,
      "created_at": "2025-09-16T14:31:00Z"
    }
  ],
  "bans": [
    {
      "id": 1,
      "order": 1,
      "kind": "OBJECTIVE_COMBO",
      "team": "A",
      "map": "Guardian",
      "mode": "King of the Hill"
    }
  ],
  "rounds": [
    {
      "id": 1,
      "order": 1,
      "slot_type": "OBJECTIVE",
      "picked_by": null,
      "map": null,
      "mode": null
    }
  ]
}
```

---

### List All Series

**GET** `/api/series/`

Returns paginated list of all series.

#### Query Parameters
- `page` (int): Page number (default: 1)
- `page_size` (int): Items per page (default: 20, max: 100)
- `state` (string): Filter by state (`IDLE`, `BAN_PHASE`, etc.)
- `team` (string): Filter by team name

#### Response (200 OK)
```json
{
  "count": 150,
  "next": "/api/series/?page=2",
  "previous": null,
  "results": [
    {
      "id": 42,
      "team_a": "Red Dragons",
      "team_b": "Blue Cobras",
      "state": "BAN_PHASE",
      "created_at": "2025-09-16T14:30:00Z"
    }
  ]
}
```

---

## ⚔️ Veto Actions

### Submit Action

**POST** `/api/series/{id}/action/`

Submit a veto or map/gametype selection.

#### Request Body
```json
{
  "type": "veto",
  "map": "Streets",
  "mode": "Oddball"
}
```

---

### Undo Last Action

**POST** `/api/series/{id}/undo/`

Undo the most recent action in the series.


### Reset Series

**POST** `/api/series/{id}/reset/`

Resets the entire series to its initial state.


### List Maps

**GET** `/api/maps/`

Returns a list of all available maps and supported gametypes.


### List Gametypes

**GET** `/api/gametypes/`

Returns a list of available game modes (e.g. Slayer, CTF, Strongholds).


---

## 🛠 Administrative Actions

### Force Transition

**POST** `/api/series/{id}/transition/`

Force a state transition (admin use only).

#### Request Body
```json
{
  "state": "PICK_WINDOW"
}
```

---

## ❌ Error Handling

### Client Errors

- **400 Bad Request**: Invalid input or request format.
- **401 Unauthorized**: Authentication required.
- **403 Forbidden**: Insufficient permissions.
- **404 Not Found**: Resource not found.
- **409 Conflict**: Request conflicts with the current state.
- **422 Unprocessable Entity**: Invalid state transition.

### Server Errors

- **500 Internal Server Error**: Unexpected server error.
- **503 Service Unavailable**: API temporarily unavailable.

---

## 🔄 Workflow Examples

1. **Create a Series**: `POST /api/series/`
2. **Submit Action**: `POST /api/series/{id}/action/`
3. **Undo Action**: `POST /api/series/{id}/undo/`
4. **Reset Series**: `POST /api/series/{id}/reset/`

---

### Notes

All action requests are validated by the internal state machine and will return a 422 response if invalid for the current state.

Game modes are classified as is_objective: true/false in /gametypes/.



---

Last updated: September 16, 2025
