# Prototype architecture

```text
Browser (index.html, app.js, style.css)
  │  same-origin HTTP / JSON
  ▼
Python stdlib ThreadingHTTPServer (server.py)
  ├── Public routes: intake, availability, appointment, status, demo document upload
  ├── Staff routes: login, matters, lawyer assignment, status, reports, outbox
  ├── SQLite: data/lingap.sqlite3
  └── Local demo files: uploads/*  [not encrypted]
```

There is **no Node toolchain**, no frontend framework, no external database, and no third-party runtime Python dependency. This simplifies first-run setup in VS Code. It is **not** a recommended production stack.

## Pages

- `#/` — public landing page.
- `#/screen` — screening wizard, browser-only local draft.
- `#/status` — reference/email status lookup and history.
- `#/appointments` — appointment request and demo document upload.
- `#/admin` — staff sign-in and overview.
- `#/admin/matters` — case list with status and lawyer assignment.
- `#/admin/lawyers`, `#/admin/notifications`, `#/admin/analytics` — management pages.

## API endpoints

| Method | Endpoint | Action |
| --- | --- | --- |
| GET | `/api/health` | Local health check |
| POST | `/api/intakes` | Submit pre-screening form; returns reference |
| GET | `/api/status?ref=...&email=...` | View status/timeline using submitted email |
| GET | `/api/slots?date=YYYY-MM-DD` | Available appointment times |
| POST | `/api/appointments` | Request a slot with reference and email |
| POST | `/api/documents` | Demo PDF/PNG/JPG upload as base64 JSON |
| POST | `/api/admin/login` | Staff session cookie |
| POST | `/api/admin/logout` | End local staff session |
| GET | `/api/admin/me` | Session status |
| GET | `/api/admin/summary` | Charts and counts |
| GET | `/api/admin/matters` | Staff view of matters |
| GET | `/api/admin/lawyers` | Synthetic roster / active load |
| GET | `/api/admin/notifications` | Demo outbox |
| GET | `/api/admin/export.csv` | Summary report export |
| POST | `/api/admin/matters/{id}/status` | Set workflow status |
| POST | `/api/admin/matters/{id}/assign` | Assign lawyer |

## Data model

`matters` holds receipt, screening responses, current status and assigned lawyer. `appointments` has a unique `(date,time)` constraint, blocking double booking even if two requests race. `documents` holds metadata and a random stored filename. `notifications` stores simulated message records. `events` keeps major events for the public timeline. SQLite foreign keys are enabled.

## Privacy / threat model gaps

- Uploaded documents stored in plaintext on disk.
- Admin credentials controlled by environment variables but demo default is documented; sessions are in memory and not hardened for production.
- HTTP on loopback only; no TLS.
- Status matching uses reference+email, not a cryptographically verified client identity. This is a weak access gate.
- No admin role separation, 2FA, comprehensive audit trail, CSRF token, request rate limits, antivirus scanning, encrypted backups, job queue, or retention automation.
- Browser `localStorage` draft is visible to other users of the same browser profile and must not be used with real client data.
- Notification queue contains fake messages only, and does not send email.
- Availability uses fixed demo office hours, not the actual OLA calendar.

## Recommended production direction

Use a maintained backend such as Django REST Framework or FastAPI with proper authentication, PostgreSQL, a private object storage service with server-side encryption and malware scanning, approved SMTP provider, a job scheduler, complete activity auditing, access-control and policy tests, robust i18n and accessibility testing, and a PWA/kiosk design that does **not** leave sensitive data on shared devices. Actual screening logic must be reviewed by OLA counsel.
