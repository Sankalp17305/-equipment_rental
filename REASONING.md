# Reasoning

## Reading the problem
Stripping the story down, the pain points are:
1. No one knows what exists or how many units of it. (paper register)
2. No one can answer "is X free on date Y" — a *point-in-time* status isn't
   enough, since bookings are for date ranges, not just "right now."
3. Two clubs collide on the same item — needs a hard double-booking guard,
   not just a warning.
4. People hoard gear too long — needs a due date + an incentive to return
   on time (late fee) and a way to see who's overdue.
5. A deposit that's "returned minus any late fee" — so the fee is deducted
   from money already held, not billed separately.
6. One person shouldn't book out half the room — needs a per-borrower cap
   on how much they can hold *at once*.
7. "Nudge people to return it" — some kind of visible/actionable reminder,
   not just silent tracking.

## Data model
- **EquipmentType** (e.g. "DSLR Camera") holds the money rules (deposit,
  late fee/day) and category — these are per-*kind* of gear, not per unit.
- **EquipmentUnit** (e.g. "DSLR-01") is the physically trackable thing.
  Splitting type from unit is what lets "3 DSLRs, 4 projectors" exist
  naturally and lets availability be counted per type while double-booking
  is prevented per unit.
- **Borrower** is keyed by college email so the same person booking twice
  doesn't create duplicate identities (needed for the per-borrower cap to work).
- **Booking** links one unit to one borrower for one date range, and carries
  the money fields (deposit collected, late fee charged, deposit refunded)
  so the financial history is auditable after the fact.

I deliberately did **not** add a "reserved" vs "active" distinction — the
problem describes walk-up lending ("is a DSLR free this weekend"), not an
advance-approval workflow, so a booking is active from the moment it's made
until it's returned. That's a simplification I'd revisit if this needed to
support advance reservations made far ahead of pickup.

## Availability logic
"Free" is calculated per date range, not as a static flag: for a given type
and [start, end], a unit counts as free only if none of its existing active
bookings overlap that range. This directly answers the actual question
students ask ("is a DSLR free *this weekend*"), rather than only "is
something free right now," which the paper register already sort of failed
at.

## Preventing double-booking
When a booking is created, the system searches for a specific unit of that
type with no overlapping active booking and assigns it atomically in the
same request. If none exists, the booking is rejected with a clear reason.
This is enforced at the data layer (checking real overlapping rows) rather
than trusting a "quantity available" counter that could drift out of sync.

## Late fee & deposit
- Late fee = late days × per-day rate for that equipment type, capped at the
  deposit amount (so a fee can never exceed what was actually collected —
  the club shouldn't end up owing *more* than their deposit for a slow return).
- Refund = deposit − late fee. If returned on time, late fee is 0 and the
  full deposit is refunded. This matches the problem statement's wording
  exactly ("returned minus any late fee").

## Borrower cap ("shouldn't book out half the room")
Rather than guessing at a percentage of total inventory (which changes as
inventory changes), I used a flat cap of **3 active items per borrower**
(`MAX_ACTIVE_UNITS_PER_BORROWER` in `app/logic.py`) — easy for a real AV
desk to reason about and to tune. It's checked at booking time against the
borrower's *currently active* bookings, not their lifetime history.

## Nudging returns
The dashboard highlights overdue items in red with a day count, and gives a
one-click "Nudge" button that opens a pre-filled email to the borrower
(via a `mailto:` link) explaining what's overdue and what fee is accruing.
I chose `mailto:` over building real email delivery because standing up
SMTP/auth for a 2.5-hour build adds infrastructure risk for no real gain in
a single-room, low-volume tool — the AV room desk person can just click and
send from their own inbox. A natural next step would be a scheduled job that
auto-sends these daily.

## Transfers
The twist requirement: an active loan can move from one borrower to another,
with the due date unchanged and availability unaffected.

I implemented this as a pure `borrower_id` reassignment on the existing
`Booking` row — `unit_id`, `start_date`, and `due_date` are never touched.
This is what makes "availability unaffected" true *by construction* rather
than something I have to special-case: `get_available_units` only ever
looks at a unit's overlapping bookings, and a transfer doesn't add, remove,
or change any booking's unit/dates — it's still the same one row, occupying
the same unit for the same window, just pointing at a different borrower.
I verified this with a test that snapshots `availability_summary()` before
and after a transfer for the same date range and asserts they're identical.

Two judgment calls I made beyond the literal ask:
- **The per-borrower cap still applies to the receiving borrower.**
  Otherwise a transfer would be a loophole around the "can't hoard the room"
  rule — someone at their limit could just have a friend "hold" a booking
  and transfer it to them. A transfer is rejected if it would push the new
  borrower over the cap.
- **Audit trail:** I added `original_borrower_id` and `transfer_count` on
  the booking so the dashboard can show "transferred 2x (orig. X)" — useful
  for the desk to know who to actually chase if something goes wrong, since
  the deposit was originally collected from the first borrower, not
  necessarily the current holder. The brief doesn't ask for this, but
  losing that history on transfer felt like it would reintroduce the exact
  kind of accountability gap (paper register style) the whole app exists
  to fix.
- **What I did *not* change on transfer:** the deposit amount and who
  "owns" it. I left `deposit_collected` as-is on the booking rather than
  trying to move money between borrower records — the brief doesn't specify
  deposit handling on transfer, and reassigning financial liability
  automatically felt like a bigger policy decision than the problem
  statement asked me to make. A real deployment would want the desk staff
  to explicitly confirm the deposit handoff between the two people.

## What I explicitly left out (and why)
- **User accounts / login** — the problem is about tracking gear, not
  authentication; the desk operator is trusted to run the app.
- **Photo/condition logging on checkout** — nice-to-have, but not part of
  the stated pain points (missing gear, double-booking, overdue, hoarding).
- **Editing equipment inventory via the UI** — handled via `app/seed.py` for
  this build; a real deployment would add an admin form, but it wasn't core
  to the problem in the time available.
