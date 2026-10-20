# Online Judge

This repository is a web-based Online Judge project built with a FastAPI backend and a static frontend. The project is currently focused on account authentication, role-based access, session management, and administrative account control. The problem/contest/judging modules are partially planned and scaffolded in the database layer, but the implemented work is centered on the user and admin flows that are already working in the codebase.

---

## Current project status

The project is not yet a full production-ready judge platform end-to-end. At the moment, the implemented and verified features are mainly:

- user registration
- login and logout
- session-based authentication
- account profile viewing and display-name updates
- email verification flow and password reset flow support in the backend
- role-based access with `USER`, `ADMIN`, and `SUPER_ADMIN`
- super-admin account management
- static frontend pages for login, register, account, and admin management

The codebase also includes phase-based database model files for future expansion:

- `backend/db/tables_phase1.py` for the core account/session/class model layer
- `backend/db/tables_phase2.py` for the problem/contest model layer

These models are intentionally separated to make the project easier to evolve without mixing the current working auth layer with future judge features.

---

## System architecture

The application currently consists of these main components:

```text
┌───────────────┐
│  Browser UI   │
│  Static HTML  │
│  + JS pages   │
└───────┬───────┘
        │
        │ HTTP + cookies
        ▼
┌───────────────────────┐
│       FastAPI         │
│      Backend API      │
└──────────┬────────────┘
           │
           ▼
┌───────────────────────┐
│  SQLAlchemy + DB      │
│  PostgreSQL / models  │
└───────────────────────┘
```

The current backend is responsible for:

- auth endpoints
- role validation
- admin account control
- session cookie handling
- database access through SQLAlchemy

Judge0 integration and full problem submission execution are part of the project vision, but they are not the main active implementation in the current codebase.

---

## Local development

Run the backend and frontend in two separate terminals.

### 1) Backend

```bash
cd backend
.venv/bin/python -m uvicorn src.app:app --host 0.0.0.0 --port 8000
```

### 2) Frontend

```bash
cd frontend
python3 -m http.server 5500
```

Open the app at:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5500`

The backend allows credentialed requests from the common local origins by default, including:

- `http://localhost:5500`
- `http://127.0.0.1:5500`
- `http://0.0.0.0:5500`

If the frontend is served from another origin, update `CORS_ORIGINS` in the backend environment with the exact origin list.

---

## Project structure

```text
online-judge-0/
├── README.md
├── backend/
│   ├── src/
│   │   └── app.py
│   ├── db/
│   │   ├── session.py
│   │   ├── schemas.py
│   │   ├── tables_phase1.py
│   │   ├── tables_phase2.py
│   │   ├── initialize_tables.py
│   │   ├── initialize_users.py
│   │   ├── migrate_admin_active.py
│   │   └── ...
│   ├── routers/
│   │   ├── login.py
│   │   ├── register.py
│   │   ├── authenticate.py
│   │   ├── logout.py
│   │   └── manage_accounts.py
│   ├── tests/
│   └── .venv/
├── frontend/
│   ├── index.html
│   ├── modules/
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── activate.html
│   │   ├── forgot-password.html
│   │   ├── index.html
│   │   └── manage_accounts.html
│   └── assets/
│       ├── css/styles.css
│       └── js/
└── .gitignore
```

---

## Database model status

### Phase 1: current working model layer

Implemented in `backend/db/tables_phase1.py`.

This includes the user and access layer such as:

- `Account`
- `AccountRole`
- `Session`
- `Admin`
- `Student`
- `AcademicClass`
- `ManageClass`
- `StudentClass`

This module is the active basis for authentication and account management.

### Phase 2: future model layer

Defined in `backend/db/tables_phase2.py`.

This includes the next planned entities:

- `Problem`
- `Contest`
- `AccessModifier`

This phase is designed to extend the project toward problem sets, contest operations, and judging workflows. It is currently a scaffold and should be integrated gradually as the project grows.

---

## Authentication and account features

The current app supports the following flows.

### Register

- user creates a name, email, and password
- password strength validation is enforced
- email uniqueness is checked
- a new account is created as a `USER` by default

### Login

- email and password are verified
- a server-side session is created
- a secure HTTP-only cookie is returned to the browser

### Session check

- the frontend and API check whether a valid session exists
- signed-in users are redirected appropriately
- anonymous users are kept on login/register pages

### Logout

- the session record is removed on the server
- the browser cookie is cleared

### Account page

- current user data is shown
- display name can be updated
- account role is visible
- logout is available

### Admin and super-admin management

- super admins can list all accounts
- super admins can update roles between `USER`, `ADMIN`, and `SUPER_ADMIN`
- the code prevents unsafe operations such as demoting the last remaining super admin or removing the own super-admin account

---

## Frontend pages

The current frontend includes:

- `frontend/modules/login.html`
- `frontend/modules/register.html`
- `frontend/modules/activate.html`
- `frontend/modules/forgot-password.html`
- `frontend/modules/index.html`
- `frontend/modules/manage_accounts.html`

The frontend assets are separated into:

- `frontend/assets/css/styles.css`
- `frontend/assets/js/api.js`
- `frontend/assets/js/*.js` per page functionality

---

## API highlights

The main backend routes currently cover:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/auth/register` | Create a new user account |
| `POST` | `/auth/login` | Authenticate and create a session |
| `GET` | `/auth/me` | Get the current logged-in user |
| `PATCH` | `/auth/me` | Update the current account name |
| `POST` | `/auth/logout` | Delete the current session |
| `GET` | `/admin/accounts` | List accounts for a super admin |
| `PATCH` | `/admin/accounts/{account_id}/role` | Change a user's role |

---

## Future roadmap

The project is designed to expand toward:

- problem creation and problem management
- test case support
- contest creation and management
- submission workflow
- Judge0-based compile and run execution
- standings and contest results
- richer admin tools for problem and contest operations

Those modules are planned but not yet the center of the active implementation.

---

## Documentation policy

Whenever the project behavior, setup, architecture, endpoints, database models, or user flows change, the documentation in this README must also be updated to match the current state of the code.

This helps keep the project description accurate and prevents the documentation from drifting away from the implementation.
