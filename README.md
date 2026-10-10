# Online Judge

A web-based Online Judge system for programming practice and programming contests.

The system provides different levels of access for **students**, **admins**, and **super admins**. Students can solve problems and submit solutions, while admins manage programming content and contests. Super admins have higher-level control over the system and administrative accounts.

The project is designed as a modular backend application with a relational database and an external judging service powered by **Judge0**.

---

## 1. System Overview

The system consists of three main parts:

```text
┌───────────────┐
│    Student    │
└───────┬───────┘
        │
        │ Submit code / View results
        ▼
┌───────────────────────┐
│       FastAPI         │
│       Backend         │
└──────────┬────────────┘
           │
     ┌─────┴─────┐
     │           │
     ▼           ▼
┌──────────┐  ┌──────────┐
│PostgreSQL│  │  Judge0  │
│ Database │  │  Service │
└──────────┘  └────┬─────┘
                   │
                   ▼
             Compile & Run
                   │
                   ▼
             Judge Result
```

The backend is responsible for authentication, authorization, problem management, submissions, contests, and communication with the database.

**Judge0** is responsible for compiling and executing submitted source code and returning the execution result to the backend.

## Local frontend/backend development

The FastAPI backend allows credentialed requests from `http://100.73.218.40:5500`,
`http://localhost:5500`, and `http://127.0.0.1:5500` by default. If the frontend is
served from another origin, set `CORS_ORIGINS` in the backend environment to a
comma-separated list of exact origins, including the scheme and port (for example,
`http://localhost:3000,http://192.168.1.10:5500`).

Before using authentication with a new database, create the schema from the
`backend` directory with `.venv/bin/python -m db.initialize_tables`, then start
the backend. Open the frontend through a local web server (for example,
[`http://100.73.218.40:5500`](http://100.73.218.40:5500) rather than as a `file://` URL. Create an account
from the registration page before signing in.

For an existing database, apply the admin-status migration from the `backend`
directory with `.venv/bin/python -m db.migrate_admin_active` before restarting
the backend. This adds `admin.is_active` and synchronizes admin records with
accounts whose role is `ADMIN` or `SUPER_ADMIN`.

### Authentication pages and API

- Shared frontend assets are kept separate from page markup:
  - `frontend/assets/css/styles.css` contains the shared page styles.
  - `frontend/assets/js/api.js` centralizes the backend URL and credentialed
    fetch helper.
  - `frontend/assets/js/` contains one JavaScript module per page.
- `frontend/modules/login.html` is the login page. It checks the current session
  when opened and redirects an already signed-in user to the account page.
- `frontend/modules/register.html` creates an account using a display name,
  email address, and password. The password must be at least 8 characters; the
  display name must be at least 3 characters. The form asks the user to confirm
  the password before submitting.
- `frontend/modules/index.html` displays the signed-in account, provides the
  account ID, name, email, account code, role, and creation date. The display
  name can be edited from this page. It also provides the logout button and
  links super admins to account management.
- `frontend/modules/manage_accounts.html` lists accounts and lets super admins
  change account roles and see whether admin mode is active. Users without a
  session are redirected to login; signed-in users without the super-admin role
  are returned to the account page.

The frontend uses these FastAPI endpoints:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/auth/register` | Create an account; returns `409` if the email is already registered. |
| `POST` | `/auth/login` | Verify email and password, then set the `session_id` cookie. |
| `GET` | `/auth/me` | Return the current account when the session is valid; otherwise returns `401`. |
| `PATCH` | `/auth/me` | Update the signed-in account's display name. |
| `POST` | `/auth/logout` | Delete the current server-side session and clear the `session_id` cookie. |
| `GET` | `/admin/accounts` | List accounts; requires a valid super-admin session. |
| `PATCH` | `/admin/accounts/{account_id}/role` | Change an account role to `USER`, `ADMIN`, or `SUPER_ADMIN`; requires a valid super-admin session. |

Authentication uses an HTTP-only session cookie. Frontend API requests include
credentials so the browser sends and receives that cookie. Logging out invalidates
the session immediately; opening the login page while the session is still valid
redirects back to the account page. The account-management API also prevents a super admin from demoting their own
account or removing the last super admin. Promoting an account to `ADMIN` or
`SUPER_ADMIN` creates or activates its `admin` row; demoting it marks that row
inactive without deleting its admin record or class assignments.

---

# 2. User Roles

The system has three main roles.

## Student

Students are regular users of the Online Judge.

They can:

- Register and log in
- View available problems
- View problem details
- Submit solutions
- View their submissions
- View judging results
- Participate in contests
- View contest standings

Students cannot modify problems, test cases, contests, or other users.

---

## Admin

Admins are responsible for managing programming content and contests.

They can:

- Create and edit problems
- Manage problem test cases
- Publish or unpublish problems
- Create and manage contests
- Manage contest problems
- View submissions related to their managed content
- Monitor contest results

Admins cannot manage the highest-level system configuration or super admin accounts.

---

## Super Admin

Super admins have the highest level of privileges.

In addition to admin capabilities, they can:

- Manage admin accounts
- Manage user accounts
- Assign or change user roles
- Manage system-level configuration
- Access administrative functions across the entire system

The super admin role is intended for system-level administration rather than everyday problem management.

---

# 3. Main Application Flow

## 3.1 Authentication Flow

```text
User
 │
 │ Email + Password
 ▼
FastAPI
 │
 ├── Find account
 │
 ├── Verify password
 │
 └── Create session
 │
 ▼
Authenticated User
```

The system uses the user's **email address as the login identifier**.

The `account_name` field is used as the user's display name and is not used for authentication.

Passwords are hashed before being stored in the database.

---

# 4. Student Flow

A typical student workflow is:

```text
Register / Login
       │
       ▼
Browse Problems
       │
       ▼
Select Problem
       │
       ▼
Read Statement
       │
       ▼
Write Solution
       │
       ▼
Submit Code
       │
       ▼
Create Submission
       │
       ▼
Send to Judge0
       │
       ▼
Judge0 Compiles & Executes
       │
       ▼
Receive Result
       │
       ▼
Store Submission Result
       │
       ▼
Student Views Result
```

For example, when a student submits a C++ solution:

1. The backend receives the source code.
2. A `Submission` record is created.
3. The backend sends the source code and required parameters to Judge0.
4. Judge0 compiles and executes the program.
5. Judge0 returns the execution result.
6. The backend updates the corresponding `Submission`.
7. The student can view the result.

---

# 5. Admin Flow

The admin is mainly responsible for creating and maintaining programming content.

### Problem Management

```text
Admin Login
    │
    ▼
Create Problem
    │
    ├── Problem Statement
    ├── Constraints
    ├── Time Limit
    ├── Memory Limit
    └── Test Cases
    │
    ▼
Publish Problem
    │
    ▼
Students Can Submit
```

An admin can modify a problem before it is published and manage its associated test cases.

### Contest Management

```text
Admin
  │
  ▼
Create Contest
  │
  ├── Contest Information
  ├── Start / End Time
  └── Select Problems
  │
  ▼
Publish Contest
  │
  ▼
Students Participate
  │
  ▼
Submissions
  │
  ▼
Contest Results / Standings
```

---

# 6. Super Admin Flow

The super admin operates at the system level.

```text
Super Admin
     │
     ├───────────────┐
     ▼               ▼
Manage Users      Manage Admins
     │               │
     ├── View        ├── Create
     ├── Disable     ├── Disable
     └── Change Role └── Manage Role
```

The separation between `admin` and `super_admin` prevents normal content administrators from obtaining system-level privileges.

---

# 7. Database Design

The database is designed around several main entities.

```text
Account
   │
   ├────────── Session
   │
   └────────── Submission
                    │
                    ▼
                  Problem
                    │
                    ▼
                 TestCase

Contest
   │
   ├────────── Problem
   │
   └────────── ContestParticipation
```

The exact schema may evolve as the project develops.

---

## 7.1 Account

Represents a user of the system.

Main information includes:

```text
Account
---------
account_id
account_email
account_name
password_hash
role
created_at
```

`account_email` is unique and is used for authentication.

`account_name` is the display name shown to other users.

The `role` determines the user's permissions:

```text
STUDENT
ADMIN
SUPER_ADMIN
```

---

## 7.2 Session

A `Session` represents an authenticated login session.

```text
Session
---------
session_id
account_id
created_at
expires_at
```

Relationship:

```text
Account 1 ──────── N Session
```

One account can have multiple sessions, for example when the user logs in from multiple devices.

---

## 7.3 Problem

Represents a programming problem.

```text
Problem
---------
problem_id
title
statement
time_limit
memory_limit
created_at
updated_at
...
```

A problem may be created and managed by an admin.

A problem contains multiple test cases.

```text
Problem 1 ──────── N TestCase
```

---

## 7.4 TestCase

Represents an input/output test case for a problem.

```text
TestCase
---------
testcase_id
problem_id
input_data
expected_output
```

Test cases are used by the judging system to determine whether a submitted program produces the expected result.

---

## 7.5 Submission

A `Submission` represents one attempt by a student to solve a problem.

```text
Submission
------------
submission_id
account_id
problem_id
source_code
language
status
score
created_at
...
```

Relationships:

```text
Account  1 ──────── N Submission
Problem  1 ──────── N Submission
```

Therefore:

```text
Student
   │
   ├── Submission 1 ── Problem A
   ├── Submission 2 ── Problem B
   └── Submission 3 ── Problem A
```

A student can submit multiple times for the same problem.

---

# 8. Contest

A contest represents a programming competition.

```text
Contest
---------
contest_id
title
description
start_time
end_time
created_by
```

A contest contains multiple problems, while a problem may potentially appear in multiple contests.

Therefore, the relationship is conceptually:

```text
Contest N ──────── N Problem
```

This can be implemented using an association table such as:

```text
ContestProblem
---------------
contest_id
problem_id
```

---

# 9. Contest Participation

The system can track which students participate in a contest.

```text
ContestParticipation
---------------------
contest_id
account_id
registered_at
```

Relationship:

```text
Account N ──────── N Contest
```

This allows the system to maintain information about contest participants and generate standings.

---

# 10. Submission and Judge0

The Online Judge does not directly compile and execute source code itself.

Instead, it uses **Judge0** as the execution and judging service.

The flow is:

```text
             Backend
                │
                │ Source Code
                │ Language
                │ Input
                ▼
             Judge0
                │
         ┌──────┴──────┐
         │             │
      Compile        Execute
         │             │
         └──────┬──────┘
                │
                ▼
           Judge Result
                │
                ▼
             Backend
                │
                ▼
            Submission
```

The backend sends the necessary information to Judge0, such as:

- Source code
- Programming language
- Standard input
- Time limit
- Memory limit

Judge0 returns information such as:

- Compilation result
- Program output
- Standard error
- Execution time
- Memory usage
- Status

The backend then converts the result into the corresponding submission status and stores it in the database.

---

# 11. Submission Lifecycle

A submission can be viewed as moving through several states:

```text
Created
   │
   ▼
Queued
   │
   ▼
Sent to Judge0
   │
   ▼
Running
   │
   ├───────────────┐
   ▼               ▼
Accepted        Failed
                   │
          ┌────────┼─────────┐
          ▼        ▼         ▼
       Wrong     Runtime   Compile
       Answer     Error     Error
```

The exact status model can be extended depending on the requirements of the judging system.

---

# 12. Application Architecture

The backend follows a layered structure to separate different responsibilities.

```text
Request
   │
   ▼
Router / API
   │
   ▼
Service
   │
   ├── Authentication
   ├── Problem Management
   ├── Submission
   └── Contest Management
   │
   ▼
SQLAlchemy Models
   │
   ▼
PostgreSQL
```

The main responsibilities are separated as follows:

### Models

Define database entities and relationships.

Examples:

```text
Account
Session
Problem
TestCase
Submission
Contest
ContestParticipation
```

### Schemas

Define the data exchanged through the API.

They are used to validate incoming requests and structure outgoing responses.

### Routers

Define API endpoints and handle HTTP requests.

For example:

```text
/auth
/problems
/submissions
/contests
/admin
```

### Services

Contain application logic that should not be tightly coupled to HTTP endpoints.

Examples:

```text
authenticate()
create_problem()
submit_solution()
judge_submission()
create_contest()
```

### Database Layer

Responsible for creating database sessions and communicating with PostgreSQL through SQLAlchemy.

---

# 13. High-Level Project Architecture

```text
                    ┌─────────────────┐
                    │     Client      │
                    │  Web Interface  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │     FastAPI     │
                    │     Routers     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    Services     │
                    └──────┬─────┬────┘
                           │     │
                ┌──────────┘     └──────────┐
                ▼                           ▼
       ┌─────────────────┐         ┌─────────────────┐
       │   PostgreSQL    │         │     Judge0      │
       │     Database    │         │ Judge Service   │
       └─────────────────┘         └─────────────────┘
```

The application backend acts as the central component connecting users, persistent data, and the external judging service.

---

# 14. Project Goals

The main goals of the project are:

- Build a functional Online Judge system.
- Practice backend development with FastAPI.
- Design a relational database for a real-world application.
- Implement authentication and role-based authorization.
- Understand relationships between users, problems, submissions, and contests.
- Integrate an external code execution service using Judge0.
- Develop a system that can later be extended with a dedicated frontend and more advanced contest features.

The project is primarily intended as an educational and software engineering project, with the architecture designed to remain simple enough to understand while allowing future expansion.
