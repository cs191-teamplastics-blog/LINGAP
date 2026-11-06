# Manual test guide

**Use fake information only.** Start `python3 server.py` / `py server.py` from the project root.

1. **Homepage and mobile:** Open `http://127.0.0.1:8000`; resize to phone width; open menu; switch English/Filipino.
2. **Screening validation:** In `#/screen`, try continuing without consent; should be blocked. Enter invalid email; should be blocked. Finish form with fictitious details; record reference.
3. **Draft:** Enter a few values and click Save Draft. Refresh and reopen screening; values should persist locally. Clear Draft resets.
4. **Tracking:** In `#/status`, use reference and exact email. Correct pair displays record; wrong email displays 404-style message.
5. **Appointments:** Pick a weekday within 60 days. Submit an appointment request. Use a different demo intake to try the same slot; it should be unavailable. A second appointment on the same intake is blocked.
6. **Demo file:** On `#/appointments`, use the reference and email and upload a harmless generated PDF or image under 3 MB. Check a file appears in `uploads/`. Do not upload real IDs.
7. **Staff login:** Open `#/admin` with default demo credentials. Invalid credentials should fail.
8. **Staff matters:** Go to Matters; search, filter, open a reference; update status and assignment.
9. **Public status:** Revisit `#/status` and confirm the status and timeline changed.
10. **Notifications:** Staff Notifications should show messages for intake, appointment and status changes, marked not sent.
11. **Analytics:** Counts/bars should update; CSV download should work.
12. **Reset:** Stop server, delete `data/lingap.sqlite3`, restart to recreate eight synthetic sample matters.

## Known limitations

- The local server is for one trusted developer; it is not security tested.
- Only partial bilingual support; the admin dashboard remains English.
- No real outbound emails, no appointment approval messaging, no true offline sync.
- Does not compute six-month or real-world performance targets from the deck.
- Uses browser fonts if Google Fonts are unreachable.
