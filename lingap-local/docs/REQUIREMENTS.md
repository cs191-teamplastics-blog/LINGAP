# Requirements coverage — LINGAP proposal v3.0 (July 17, 2026)

This is a **prototype interpretation** of the supplied 21-page deck, not a production requirements specification.

| Deck feature / page | Prototype status | Description |
| --- | --- | --- |
| Public eligibility pre-screener with skip logic (pp. 4–5, 14–16) | **Partial / functional form** | Guided 5-stage intake, gating, basic conditional questions; **no real legal eligibility logic** because actual approved rules are not in the deck. |
| Filipino / English (pp. 4–5) | **Partial** | Public headings, controls and primary labels translated; some notices, option labels, status labels and admin UI still English. Full certified translation required. |
| Automated feedback (p. 4) | **Partial** | Application receipt and human-review guidance; no eligibility determination. |
| Online appointment scheduling (pp. 4–5) | **Working demo** | Weekday appointment requests within 60 days, unavailable/occupied slots removed, uniqueness guarded in SQLite; confirmation workflow incomplete. |
| Encrypted document portal (pp. 4–5) | **Demo storage only** | File validation and 3 MB limit; files are **not encrypted at rest**. Do not upload sensitive documents. |
| Analytics / KPIs (pp. 4–5, 9, 20) | **Partial** | Real counts in local DB, type/status distribution, CSV export; no authentic office productivity or uptime measurement. |
| Offline kiosk / staff-assisted entry (pp. 4–5, 10) | **Partial** | Browser draft via localStorage; no service worker, queued offline submissions, conflict resolution or controlled kiosk access. |
| Automated notifications (pp. 4–5, 18) | **Simulated** | SQLite outbox only, no emails actually transmitted. |
| Matter intake management (pp. 17–19) | **Working demo** | Dashboard, triage status, lawyer assignments, activity timeline via status endpoint, searchable matter list, synthetic lawyer roster. |
| RA 10173 / DPIA / privilege disclaimer (p. 10) | **Not completed** | Visible privacy warning / demo consent, minimal intake design; no legal sign-off, DPIA or compliance validation. |
| Data retention (p. 10) | **Not implemented** | The deck calls for deletion of ineligible data after 30 days; actual eligibility classification and a scheduler are not present. |
| Architecture, QA and documentation (p. 7) | **Partial** | README, API notes, test checklist; no security audit, UAT report, or formal DPIA. |
| Out of scope (p. 5) | **Respected** | No court-filing integrations, AI legal advice, or full historical-case digitization. |

## Decisions requiring OLA sign-off

- The deck does not give screening question text, actual financial thresholds, residency thresholds, conflict checks or formal eligibility policies. These **must not** be invented.
- The public application confirmation is a receipt, never an approval.
- Admin roster names are fictional. Replace with verified staff records.
- This prototype uses free local tooling; the actual deployment must go through OLA governance and UP IT/privacy/security approval.
