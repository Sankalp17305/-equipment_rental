Dear Students,
Welcome to the next level of Assessment of Auriga IT, the Round 2 — "Builder" Round.
You must ensure that you are sitting at the same spot where you sat in Round-1, today morning.
Round 2 is a hands-on "Builder" round that assesses how candidates approach an open-ended, real-world problem.
- Duration: The round is 2.5 hours long. Submissions will not be accepted after the 2.5-hour window closes.
- Problem statement: Each candidate will be given a short, real-world problem statement. No further explanation or specification will be provided beyond that statement.
- Deriving the solution: Candidates are expected to interpret the problem themselves and determine the features and specifications to be implemented. They are free to use any AI assistance or tools (for example, GitHub Copilot) to help infer the requirements and build their solution.
- Tech stack: Candidates may use any technology stack they are comfortable with.
- Environment: All coding is to be done online using GitHub Codespaces, accessed via the candidate's college email ID.
Problem Assignment:
equipment_rental
Submission Guidelines
The final solution must be a public GitHub repository, and its root folder must contain the following three files, which are required for evaluation:
- README.md — instructions for project setup, running, and debugging.
- REASONING.md — an explanation of the thought process behind the solution.
- AI_LOGS.md — a complete copy of the candidate's conversation with the AI tool (Copilot or any other). This log must be pasted as-is and not modified in any way; any alteration will lead to a deduction of marks.
Candidates must submit the public GitHub repository URL through the following form: https://forms.gle/eEJNPdbrtr7Stu497
Please note that the 2.5-hour limit is strict — any submission received after the window closes will not be entertained.
problem statement
The college AV room
The college AV room lends out gear — DSLR cameras, projectors, mics, tripods — and popular items have several units. Today it’s a paper register nobody keeps up to date, so kit goes missing and two clubs show up for the same projector. Students keep asking ‘is a DSLR free this weekend?’ and no one can say. Borrowers hang on to things far too long, so a sensible return date and a small per-day late fee would help, and a refundable deposit keeps people honest — returned minus any late fee. And one person shouldn’t be able to book out half the room at once.
Build something to track the gear and nudge people to return it.

Scaffolding project files and drafting availability logic.
This is a solid, well-scoped problem — I'll build you a complete, working solution fast since your clock is running. Let me scaffold it properly.

Created 16 files, ran 7 commands, shared files
Now the seed script and FastAPI app with routes:
Now the templates:
Now let's test it actually runs before handing it over:
All core rules verified end-to-end. Now cleaning the test DB and writing the three required root files.
Let's package it up so you can pull it straight into your Codespace:
It's tested and working — everything below is verified end-to-end (availability, booking, borrower cap, double-booking prevention, late-fee math).

What's in the zip: FastAPI + SQLite app covering every requirement in the brief — availability by date range, unit-level double-booking prevention, due dates with per-day late fees, deposits refunded minus fees, a 3-item cap per borrower, and a dashboard with overdue highlighting + one-click email nudges.

Do this in Codespaces:

Unzip into your Codespace, pip install -r requirements.txt, python -m app.seed, uvicorn app.main:app --reload.
git add . && git commit -m "AV room rental tracker", push to a new public repo.
README.md and REASONING.md are already written for you.
AI_LOGS.md you must fill in yourself — it currently just has instructions in an HTML comment. The rules say it has to be your actual, unedited conversation with the AI tool, so paste this whole conversation (and any other AI conversations you have before submitting) in there verbatim, replacing the comment.
One flag: I set the per-borrower cap at 3 items — that's a judgment call, not stated in the brief, so if you want to defend a different number, adjust MAX_ACTIVE_UNITS_PER_BORROWER in app/logic.py and say why in REASONING.md.


Equipment rental
ZIP 
updated The Twist
Your solution must also allow an active loan to be transferred from one borrower to another — the original due date carries over unchanged, and the item’s availability is unaffected by the transfer.

Adding a route to transfer a booking's borrower.
Adding a route to transfer a booking's borrower.
Good twist — let's add it cleanly. Since a transfer just swaps the borrower on the existing loan row (same unit, same due date), availability is untouched by construction — I just need the transfer logic + a UI for it.

Edited 6 files, ran 2 commands, and 3 more tools
Updated and re-tested. What changed:

app/models.py — Booking now tracks original_borrower_id and transfer_count for an audit trail (who first checked it out, how many hand-offs).
app/logic.py — new transfer_booking(): reassigns only borrower_id on the existing loan row. unit_id, start_date, due_date are never touched, which is what makes availability provably unaffected — the availability check only looks at overlapping bookings per unit, and a transfer doesn't touch any of that.
New route + page — /transfer/{booking_id}, reachable via a "Transfer" button on the dashboard.
Still enforces the 3-item cap on whoever's receiving the item, so transfers can't be used to dodge the anti-hoarding rule.
I wrote a test that snapshots availability for the same date range before and after a transfer and asserts they're byte-identical — confirmed passing, along with due-date/unit preservation and cap enforcement on the receiving borrower.

REASONING.md now has a "Transfers" section explaining these calls, including one I flagged as a judgment call rather than a spec requirement: I left the deposit itself un-reassigned on transfer, since the brief doesn't say how liability should move between borrowers — worth defending if asked.


Equipment rental
ZIP 
which files updated and which are same

Here's the diff since the first delivery:

Updated:

app/models.py — added original_borrower_id and transfer_count columns to Booking, plus the original_borrower relationship (and made the existing borrower/bookings relationships explicit about which foreign key they use, since there are now two FKs to Borrower)
app/logic.py — added the new transfer_booking() function
app/main.py — added the GET/POST /transfer/{booking_id} routes
app/templates/dashboard.html — added the "Transfer" button and the "transferred Nx (orig. ...)" note
README.md — added a "Transfer" step to the usage walkthrough
REASONING.md — added the "Transfers" section explaining the design calls
New file (didn't exist before):

app/templates/transfer.html
Unchanged:

app/database.py
app/seed.py
app/static/style.css
app/templates/base.html
app/templates/index.html
app/templates/book.html
app/templates/history.html
requirements.txt
.gitignore
AI_LOGS.md (still just the placeholder instructions — that one's on you to fill in with your real AI conversation)
One thing worth double-checking on your end: since models.py changed (new columns), if you'd already run the app once and generated av_rental.db from the previous zip, delete that file and re-run python -m app.seed — SQLite won't auto-migrate the schema.

