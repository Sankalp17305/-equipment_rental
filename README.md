# AV Room Rental Tracker

A small web app for the college AV room to replace the paper register: track
which DSLRs/projectors/mics/tripods exist, see real availability for any date
range, book gear with a due date + refundable deposit, and get nudged about
overdue returns.

## Tech stack
- **Backend:** Python 3 + FastAPI
- **DB:** SQLite via SQLAlchemy (single file, zero setup)
- **Frontend:** Server-rendered Jinja2 templates + plain CSS (no build step,
  keeps the whole thing runnable with one command)

## Setup & run

```bash
# 1. Create a virtual environment (optional but recommended)
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Seed sample equipment (3 DSLRs, 4 Projectors, 5 Mics, 4 Tripods)
python -m app.seed

# 4. Run the app
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open the forwarded port (Codespaces will prompt you, or visit
`http://localhost:8000`).

## Using it
1. **Check Availability** (`/`) — pick a date range, see how many of each
   item are free for *those* dates (not just "right now").
2. **Book** — click Book on an available item, fill in name/email/club. This
   auto-assigns a specific free unit and records the deposit.
3. **Dashboard** (`/dashboard`) — everything currently checked out, overdue
   items highlighted in red with days-overdue. "Nudge" opens a pre-filled
   email to the borrower. "Mark returned" closes the loan and computes the
   late fee automatically.
4. **Transfer** — on the dashboard, click "Transfer" next to any active loan
   to hand it to a different person (e.g. one clubmate takes over from
   another mid-weekend). The item, due date, start date and deposit record
   are untouched — only who's responsible for the return changes. The
   dashboard shows a small "transferred Nx (orig. ...)" note once a loan
   has changed hands.
5. **History** (`/history`) — past returns with late fee and refund amount.

## Debugging
- **"table not found" / weird DB errors:** delete `av_rental.db` and re-run
  `python -m app.seed`. The DB file is disposable — it's git-ignored.
- **Port already in use:** run with `--port 8001` (or any free port).
- **Changes not showing up:** confirm `--reload` is on and you saved the file;
  Jinja templates are read live so no restart is needed for template-only edits.
- **Dependency errors:** delete `.venv` and redo the setup steps — a stale
  virtualenv is the usual culprit.

## Design decisions
See `REASONING.md` for the thinking behind the data model and rules
(availability logic, borrower cap, late fee / deposit math).
