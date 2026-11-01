# Online Judge

This repository is a web-based Online Judge project built with a FastAPI backend and a static frontend. The project includes the working authentication and admin account flows, plus a newly added judge-management layer for admin-created problems, academic classes, and contests. The building approach keeps the earlier account system intact while extending the platform with a simplified Polygon-style workflow for educational classes and contest management.

---

## Current project status

The project is now extended beyond the original account-management layer. The verified features include:

- user registration
- login and logout
- session-based authentication
- account profile viewing and display-name updates
- email verification flow and password reset flow support in the backend
- role-based access with `USER`, `ADMIN`, and `SUPER_ADMIN`
- super-admin account management
- admin judge management for problems, academic classes, and contests
- creation and editing of admin-owned problems, including public/private visibility and test cases
- LaTeX problem statements with a live rendered preview while authoring
- assignment of public or admin-owned problems into academic classes and contest rounds
- academic class rosters with student enrollment/removal, exercises, and linked contests
- contest metadata and status tracking for upcoming/active/finished periods
- judge-admin frontend detail panels that query class and contest data directly from the backend
- testcase editor and class roster controls in the judge-admin frontend
- standings endpoint for contest performance tracking and out-of-contest interpretation
- static frontend pages for login, register, account, admin management, and judge administration

The codebase also includes phase-based database model files for future expansion:

- `backend/db/tables_phase1.py` for the core account/session/class model layer
- `backend/db/tables_phase2.py` for the problem, contest, solution, submission, and language model layer
- `backend/db/tables_phase3.py` as a compatibility export for the shared `Language` table definition

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
- judge admin endpoints for problem/class/contest management
- problem creation and editing workflows for admin users
- contest and class linkage between the model layer and admin UI
- class detail and contest detail APIs for problem and standings summaries
- database access through SQLAlchemy

Students use the classroom page to discover classes, request to join, view assigned problems, and submit source code. They can also practice public problems from the problem bank without joining a class. Administrators create problems in their own library from a separate editor; only the owner (or a super admin) can view and edit a problem's test cases. Public problems appear in the shared practice library, while private problems are only visible to students through classes where they have been assigned. Class administrators approve enrollment requests and manage class-specific administrator permissions. Class owners can search active administrator accounts by name or email and invite them to a class. Class ownership reuses the existing `manage_class` relation; the first administrator assigned to a class is its owner. Only administrators assigned to a class can access it, and only its owner (the primary administrator) can review student join requests. Requests remain pending until the owner approves or rejects them. A new `class_join_request` table records approval requests. Submissions are executed by the configured Judge0 service, never by the web server. The upgrade migration creates missing model tables and adds the contest and source-code fields to an existing `submission` table.

---

## Local development

Run the backend and frontend in two separate terminals.
See [database.md](./database.md) for the complete table, column, constraint, and relationship reference.

### 1) Backend

Before starting the app for the first time, or after changing the SQLAlchemy models, sync the database schema:

```bash
cd backend
PYTHONPATH=. .venv/bin/python db/initialize_tables.py
PYTHONPATH=. .venv/bin/python db/migrate_judge_admin.py
PYTHONPATH=. .venv/bin/python -m src.serve
```

For an existing database, run `migrate_judge_admin.py` before starting the backend. It is safe to run more than once; `initialize_tables.py` alone does not add columns to existing tables.
The migration also allows deleting accounts without losing judge history: authored problems, contests, and submissions are retained with the deleted account reference cleared.
Problems without an owner are marked “Ẩn danh” in judge management. Only super admins can delete problems; deletion also permanently removes their test cases, solutions, class/contest links, and submissions.
Super admins can also delete classes, contests, and individual submissions. Deleting a class removes its memberships and links while keeping shared problems and contests; deleting a contest removes its submissions and links while keeping its problems. No account can delete itself; the final super-admin account is also protected from deletion by another super admin.
To enable code submissions, run a Judge0 instance, set `JUDGE0_URL` in the backend environment, and sync its language list with `PYTHONPATH=. .venv/bin/python db/initialize_languages.py`. The UI reports a service error when Judge0 is not reachable; submitted source code is never executed in the FastAPI process.

### 2) Frontend

```bash
cd frontend
python3 -m http.server 5500 --bind ::
```

Open the app at:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5500`

Both servers listen on IPv4 and IPv6 so other devices can connect through the machine's LAN or Tailscale addresses.

The frontend uses the same hostname as the page to find the backend, including IPv6 addresses. The backend allows credentialed requests from private IPv4, Tailscale IPv4, and local IPv6 origins by default, including:

- `http://localhost:5500`
- `http://127.0.0.1:5500`
- `http://0.0.0.0:5500`
- `http://172.17.22.24:5500`
- `http://172.18.0.1:5500`
- `http://172.19.0.1:5500`
- `http://100.73.218.40:5500`
- `http://[fd7a:115c:a1e0::ee01:daa5]:5500`

The same applies to the frontend on port `5500` and backend API on port `8000`. A private or Docker bridge address such as `172.18.0.1` or `172.19.0.1` only works for other devices if their network can route to that interface; otherwise use the machine's LAN or Tailscale address. If the frontend is served from another public origin, update `CORS_ORIGINS` in the backend environment with the exact origin list.
When using a remote VS Code workspace, make sure the backend port `8000` is forwarded in the VS Code **Ports** panel as well as the frontend port `5500`. The browser may map the backend to a local port from `8001` through `8010`; on localhost, the frontend verifies those ports after `8000` is unavailable and remembers the verified port for the current tab. If VS Code assigns a port outside that range, forward the backend as local port `8000` or update the discovery range in `frontend/assets/js/api.js`. Restart an already-running backend with `PYTHONPATH=. .venv/bin/python -m src.serve` to enable both IPv4 and IPv6 listeners.

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
│   │   ├── manage_accounts.py
│   │   └── judge_admin.py
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
- `ClassJoinRequest`

This module is the active basis for authentication and account management.

### Phase 2: judge and contest model layer

Defined in `backend/db/tables_phase2.py`.

This includes the next planned entities:

- `Problem`
- `Testcase`
- `Contest`
- `ContestProblem`
- `AcademicClassProblem`
- `AcademicClassContest`
- `Solution`
- `Submission`
- `Language`
- `AccessModifier`

The `submission` table stores source code for new student submissions. The migration adds this nullable column for existing databases so previously stored submissions remain valid.

The refined design links the database as follows:

- `Account` 1 — N `Submission`
- `Problem` 1 — N `Submission`
- `Problem` 1 — N `Solution`
- `Language` 1 — N `Submission`
- `Language` 1 — N `Solution`
- `Contest` 1 — N `ContestProblem` N — 1 `Problem`
- `Problem` 1 — N `Testcase`
- `AcademicClass` N — N `Problem` through `AcademicClassProblem`
- `AcademicClass` N — N `Contest` through `AcademicClassContest`

These models are used by the current problem, testcase, submission, and contest administration routes. Automated code execution is not yet implemented.

### Phase 3: language registry

Defined in `backend/db/tables_phase3.py` and backed by the same `Language` model used by the judge layer.

This table stores the language entries synchronized from Judge0 so that `Submission` and `Solution` can point at a real programming-language record instead of using only a free-form label.

---

## Authentication and account features

The current app supports the following flows.

### Register

- user creates a name, email, and password
- password strength validation is enforced
- email uniqueness is checked
- a new account is created as a `USER` by default
- verification and password-reset emails are queued; the single-process queue sends at most five emails in a rolling minute and at most one email per address in three minutes
- six-digit codes expire two minutes after delivery

The email queue and its rate-limit state are held in backend process memory, so queued mail is lost on restart and limits are per process. Run a single backend worker to preserve these limits; multi-worker or multi-instance deployments need a shared queue and limiter.

### Login

- email and password are verified
- a server-side session is created
- a secure HTTP-only cookie is returned to the browser
- the cookie and server-side session both expire after one day
- set `SESSION_COOKIE_SECURE=true` when serving the app over HTTPS; keep it false for local HTTP development

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
- `frontend/modules/classroom.html`
- `frontend/modules/manage_accounts.html`
- `frontend/modules/judge_admin.html`

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
| `GET` | `/admin/judge/problems` | List problems |
| `GET` | `/admin/judge/problems/{problem_id}` | View an owned problem and its test cases |
| `POST` | `/admin/judge/problems` | Create a problem with optional test cases |
| `PATCH` | `/admin/judge/problems/{problem_id}` | Edit a problem and optionally replace its test cases |
| `GET`, `POST` | `/admin/judge/academic-classes` | List and create academic classes |
| `GET` | `/admin/judge/academic-classes/{class_id}` | View a class roster, problems, and contests |
| `POST` | `/admin/judge/academic-classes/{class_id}/problems/create` | Create a problem and attach it to a class atomically |
| `POST` | `/admin/judge/academic-classes/{class_id}/contests/create` | Create a timed contest with selected class problems |
| `POST` | `/admin/judge/academic-classes/{class_id}/claim` | Claim a legacy class with no administrator |
| `GET`, `POST`, `DELETE` | `/admin/judge/academic-classes/{class_id}/managers` | List and change class administrator permissions |
| `GET` | `/admin/judge/academic-classes/{class_id}/join-requests` | List pending student access requests |
| `PATCH` | `/admin/judge/academic-classes/{class_id}/join-requests/{request_id}` | Approve or reject a student request |
| `POST` | `/admin/judge/academic-classes/{class_id}/students` | Enroll a student account |
| `DELETE` | `/admin/judge/academic-classes/{class_id}/students/{account_id}` | Remove a student account |
| `POST` | `/admin/judge/academic-classes/{class_id}/problems` | Attach a problem to a class |
| `GET`, `POST` | `/admin/judge/contests` | List and create contests |
| `GET` | `/admin/judge/contests/{contest_id}` | View contest status and problems |
| `POST` | `/admin/judge/contests/{contest_id}/problems` | Add a problem to a contest |
| `POST` | `/admin/judge/academic-classes/{class_id}/contests` | Attach a contest to a class |
| `GET` | `/student/available-classes` | List classes and the student's access status |
| `GET` | `/student/problems` | List public problems for practice |
| `POST` | `/student/problems/{problem_id}/submissions` | Submit a solution to a public problem |
| `GET` | `/student/classes` | List classes the student has joined |
| `POST` | `/student/classes/{class_id}/join-requests` | Request access to a class |
| `GET` | `/student/classes/{class_id}` | View class problems and contests after approval |
| `GET` | `/student/classes/{class_id}/contests/{contest_id}` | View contest problems and eligibility window |
| `GET` | `/student/classes/{class_id}/contests/{contest_id}/standings` | View live standings |
| `GET` | `/student/classes/{class_id}/submissions` | View the student's submission history for a class |
| `GET` | `/student/languages` | List configured Judge0 languages |
| `POST` | `/student/classes/{class_id}/problems/{problem_id}/submissions` | Submit source code to Judge0 and save the result |

---

## Future roadmap

The project is designed to expand toward:

- submission workflow
- Judge0-based compile and run execution
- richer contest scheduling and management tools

Automated submission evaluation and execution remain future work.

---

## Documentation policy

Whenever the project behavior, setup, architecture, endpoints, database models, or user flows change, the documentation in this README must also be updated to match the current state of the code.

This helps keep the project description accurate and prevents the documentation from drifting away from the implementation.
