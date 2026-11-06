# LINGAP — Local Legal Intake & Matter Management Prototype

A complete **locally runnable proof of concept** inspired by the July 17, 2026 *LINGAP: Legal Intake Navigator for Guidance and Assistance Platform* proposal for the UP Office of Legal Aid. Maroon / gold design and workflows are inspired by the project deck, not copied from an official UP web property.

> **DEMONSTRATION ONLY — NOT AN OFFICIAL UP OLA WEBSITE.** Do not enter real client details, legal case facts, ID documents, passwords you use elsewhere, or any confidential information. This local prototype has not been approved, audited, deployed, or cleared for Philippine Data Privacy Act compliance. It does not provide legal advice or make final eligibility determinations.

## 1. Files

```text
lingap-local/
├── server.py                # Python HTTP server + SQLite JSON API
├── static/
│   ├── index.html           # Browser entry point
│   ├── style.css            # Responsive design / maroon-gold styling
│   ├── app.js               # Pages, interactions, EN/Filipino forms, admin UI
│   └── favicon.svg          # Project icon (not an official seal)
├── data/                    # SQLite database generated at first startup
├── uploads/                 # LOCAL demo uploads (not encrypted!)
├── docs/
│   ├── REQUIREMENTS.md      # Deck-to-prototype coverage and remaining work
│   ├── ARCHITECTURE.md      # API, data model and recommended production steps
│   └── TESTING.md           # Manual tests and caveats
├── .gitignore
├── start-mac-linux.sh      # Optional launch shortcut
├── start-windows.bat        # Optional Windows launch shortcut
├── requirements.txt        # Zero external Python packages
└── README.md
```

## 2. Run locally in VS Code

**Prerequisites:** Python 3.10 or newer, Visual Studio Code, a web browser. **Node/npm are not required.** Internet is optional; an external Google Fonts stylesheet may be unavailable offline, in which case system fonts are used.

1. Download and extract the ZIP file.
2. In VS Code, choose **File → Open Folder**, and select the extracted `lingap-local` folder (the folder with `server.py`).
3. Open **Terminal → New Terminal**.
4. Run:

   **macOS / Linux**
   ```bash
   python3 --version
   python3 server.py
   ```

   **Windows (PowerShell)**
   ```powershell
   py --version
   py server.py
   ```

5. Open **http://127.0.0.1:8000** in your browser.
6. For the staff portal, navigate to **http://127.0.0.1:8000/#/admin**.

   Local demo login (change if others will access this computer):
   ```text
   Username: admin
   Password: ChangeMe123!
   ```

7. To stop the server, press **Ctrl+C** in the VS Code terminal.

**IMPORTANT:** Do not open `static/index.html` directly using `file://` or VS Code Live Server. The interface calls the Python API, so start `server.py` first and use `http://127.0.0.1:8000`.

## 3. Optional: change credentials or port

Use environment variables **before** starting the server:

**macOS / Linux**
```bash
LINGAP_ADMIN_USER=myadmin LINGAP_ADMIN_PASSWORD='your-demo-password' LINGAP_PORT=8080 python3 server.py
```

**Windows (PowerShell)**
```powershell
$env:LINGAP_ADMIN_USER = 'myadmin'
$env:LINGAP_ADMIN_PASSWORD = 'your-demo-password'
$env:LINGAP_PORT = '8080'
py server.py
```

Then visit `http://127.0.0.1:8080`. Keep `LINGAP_HOST` at its default `127.0.0.1`; never expose this demonstration server to the public internet.

## 4. Try the workflow

1. At the public homepage, use the **EN / FIL** switch for bilingual UI.
2. Select **Start pre-screening**. Agree to the demo notice, enter *fake* contact details, answer the general questions, review, submit.
3. Copy the reference number (e.g. `OLA-2026-ABC123`). The confirmation and sample event are saved to SQLite.
4. Use **Track application** with the same fake email to see the status timeline.
5. Use **Appointments**, enter the reference and fake email, choose a weekday within 60 days, choose a vacant slot, and request it. This is **not** a real confirmed appointment.
6. Optionally upload a harmless sample PDF/PNG/JPG (maximum 3 MB) on the appointment page. The file is stored in `uploads/` in plaintext. Never upload real information.
7. Sign in to **Staff portal** and inspect **Overview**, **Matters**, **Lawyers**, **Notifications**, and **Analytics**. Click a case reference to change status or assign a lawyer. Download a summary CSV in Analytics.
8. Watch the public status update and the demo email outbox change accordingly.

The dashboard comes with eight **clearly synthetic** sample applications and five **fictional directory entries** to demonstrate charts and workload distribution. All additional submissions persist on the local computer.

## 5. Reset all sample data

Stop the server. Delete `data/lingap.sqlite3` to reset the database. Delete files in `uploads/` to clear demo documents. Start the server again to re-seed synthetic data.

## 6. What works and what is simulated

**Working locally:** public landing page, bilingual labels, multi-step basic intake, conditional progression (skip to relevant steps), consent gate, local draft saved in browser, reference generation, SQLite persistence, appointment availability and unique slot enforcement, appointment requests, status lookup, demo uploads, staff login, case list/search/filter, lawyer assignment, case status updates, charts, CSV reporting, and notification outbox logging.

**Simulated or incomplete:** email delivery (outbox only), actual OLA eligibility rules, final appointment approval, offline synchronization (browser draft only), encryption of local uploads, production identity/role management, signed privileged consent, data retention jobs, operational KPI baselines, staff real names, DPIA, penetration testing, accessibility audit, secure hosting, and production-grade authorization. The uploaded project deck does **not** specify the actual legal eligibility thresholds or approved questionnaires. Therefore this demo requires human review rather than inventing those rules.

## 7. Suggested next development steps

Do not put this server online as-is. For a real service: validate actual OLA questionnaire and skip logic with lawyers; perform DPIA and threat modeling; replace demo identities with verified OLA staff roles; move to a hardened web framework and PostgreSQL; use a private object store with key management, malware scanning, access controls and encrypted document storage; implement an audit log, rate limiting, session expiry, CSRF protections, file retrieval permissions, notifications via approved email provider, retention/deletion automation, offline kiosk workflow, backups and incident response; complete accessibility and security testing; and deploy behind TLS with UP IT approval.

More detail is in `docs/`.


## NEW: Client accounts and branded client dashboard

The interface now uses the supplied LINGAP visual direction: Roboto typography, dark maroon `#170000`, maroon `#76090C`, deep green `#0A4424`, gold `#FFBD3A`, light gray `#EDF2F4`, and gray-blue `#8D99AE`. The logo is a locally drawn placeholder wordmark/icon, not an official reproduction of the UP seals. Replace with institution-approved original SVG/PNG files before publication.

### Try the client workflow
1. Run `python3 server.py` (macOS) or `py server.py` (Windows).
2. Open `http://127.0.0.1:8000/#/login` and click **Create account**.
3. Register with a **fictional email and unique demo password** (10+ characters). The account is stored in `data/lingap.sqlite3` and the password is PBKDF2-hashed, not plaintext.
4. Visit **Pre-screening**, use the same account email, complete the sample intake, and submit.
5. Visit **My cases** (`/#/dashboard`). Your linked application appears with status, timeline and appointment information.
6. Log into the separate staff portal (`/#/admin`) and change the sample matter status. Return to the client dashboard and refresh to see the update.

**Existing anonymous/seed records:** historical anonymous cases and the built-in synthetic samples are deliberately **not** linked to newly created client accounts just because the email matches. This avoids unsafe account takeover without verifying email ownership. The old reference + email tracking page remains available for unlinked demo applications, but it is not secure enough for production use.

**Security limitations:** Client sessions are in-memory (restarting the server signs users out); no email verification, account recovery, CSRF protection, request throttling, MFA, hardened cookie HTTPS setting, true data encryption-at-rest, or real email notifications. The local-demo authentication is NOT production-ready. Never use genuine client records. Before real launch, use verified identity, production-grade session management, HTTPS, vetted authorization and a DPIA/security review.

## Troubleshooting: registration seems stuck on /#/dashboard

Version 2 fixes a route refresh bug: the login screen could remain displayed when successful registration tried to navigate to the same `#/dashboard` hash. The app now re-renders the dashboard in that situation. Registration errors also remain visible under the form. If you installed the older version, stop the server with Ctrl+C, replace the project with this ZIP, and run `python3 server.py` again. Existing demo accounts may be kept by copying your `data/lingap.sqlite3` file into the new project's `data/` directory while the server is stopped.
