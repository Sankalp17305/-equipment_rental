"""
All the actual rental rules live here, kept separate from the web routes so
they're easy to read and to unit-test in isolation.
"""
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from . import models

# One borrower can't hold more than this many units checked out / reserved
# at the same time -- this is the "shouldn't book out half the room" rule.
MAX_ACTIVE_UNITS_PER_BORROWER = 3


def _overlaps(start_a, end_a, start_b, end_b) -> bool:
    """True if [start_a, end_a] and [start_b, end_b] share any day."""
    return start_a <= end_b and start_b <= end_a


def get_available_units(db: Session, type_id: int, start: date, end: date):
    """Units of this type that have no active booking overlapping [start, end]."""
    type_units = db.query(models.EquipmentUnit).filter(
        models.EquipmentUnit.type_id == type_id,
        models.EquipmentUnit.is_active == True,  # noqa: E712
    ).all()

    free = []
    for unit in type_units:
        clashing = [
            b for b in unit.bookings
            if b.status == "active" and _overlaps(b.start_date, b.due_date, start, end)
        ]
        if not clashing:
            free.append(unit)
    return free


def availability_summary(db: Session, start: date, end: date):
    """For every equipment type, how many units are free for that date range."""
    summary = []
    for et in db.query(models.EquipmentType).all():
        free_units = get_available_units(db, et.id, start, end)
        total = len(et.units)
        summary.append({
            "type": et,
            "free": len(free_units),
            "total": total,
        })
    return summary


class BookingError(Exception):
    pass


def create_booking(db: Session, borrower: models.Borrower, type_id: int,
                    start: date, end: date) -> models.Booking:
    if end < start:
        raise BookingError("Return date can't be before the pickup date.")

    active_count = db.query(models.Booking).filter(
        models.Booking.borrower_id == borrower.id,
        models.Booking.status == "active",
    ).count()
    if active_count >= MAX_ACTIVE_UNITS_PER_BORROWER:
        raise BookingError(
            f"{borrower.name} already has {active_count} item(s) checked out. "
            f"Max {MAX_ACTIVE_UNITS_PER_BORROWER} items per person at a time."
        )

    equipment_type = db.get(models.EquipmentType, type_id)
    if not equipment_type:
        raise BookingError("Unknown equipment type.")

    free_units = get_available_units(db, type_id, start, end)
    if not free_units:
        raise BookingError(
            f"No {equipment_type.name} is free for that date range."
        )

    chosen_unit = free_units[0]
    booking = models.Booking(
        unit_id=chosen_unit.id,
        borrower_id=borrower.id,
        start_date=start,
        due_date=end,
        deposit_collected=equipment_type.deposit_amount,
        status="active",
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def return_booking(db: Session, booking_id: int, return_date: date | None = None) -> models.Booking:
    booking = db.get(models.Booking, booking_id)
    if not booking:
        raise BookingError("Booking not found.")
    if booking.status == "returned":
        raise BookingError("This item was already marked returned.")

    return_date = return_date or date.today()
    late_days = max(0, (return_date - booking.due_date).days)
    per_day_fee = booking.unit.type.late_fee_per_day
    late_fee = round(late_days * per_day_fee, 2)
    # Late fee can never eat more than the deposit itself.
    late_fee = min(late_fee, booking.deposit_collected)

    booking.returned_date = return_date
    booking.late_fee_charged = late_fee
    booking.deposit_refunded = round(booking.deposit_collected - late_fee, 2)
    booking.status = "returned"

    db.commit()
    db.refresh(booking)
    return booking


def transfer_booking(db: Session, booking_id: int, new_borrower: models.Borrower) -> models.Booking:
    """Hand an active loan from its current borrower to someone else.

    The unit, start_date and due_date are untouched -- the loan itself
    doesn't change, only who's responsible for it. Because no row in the
    bookings/units tables changes except borrower_id, availability queries
    (which key off unit + date range) are completely unaffected: the unit
    was booked before the transfer and stays booked after it, same dates.
    """
    booking = db.get(models.Booking, booking_id)
    if not booking:
        raise BookingError("Booking not found.")
    if booking.status != "active":
        raise BookingError("Only an active (not yet returned) loan can be transferred.")
    if new_borrower.id == booking.borrower_id:
        raise BookingError(f"This item is already checked out to {new_borrower.name}.")

    # Still enforce the per-borrower cap on the *receiving* person, so a
    # transfer can't be used to sidestep the "no hoarding" rule.
    new_borrower_active_count = db.query(models.Booking).filter(
        models.Booking.borrower_id == new_borrower.id,
        models.Booking.status == "active",
    ).count()
    if new_borrower_active_count >= MAX_ACTIVE_UNITS_PER_BORROWER:
        raise BookingError(
            f"{new_borrower.name} already has {new_borrower_active_count} item(s) checked out. "
            f"Max {MAX_ACTIVE_UNITS_PER_BORROWER} items per person at a time -- can't transfer to them."
        )

    if booking.original_borrower_id is None:
        booking.original_borrower_id = booking.borrower_id

    booking.borrower_id = new_borrower.id
    booking.transfer_count += 1
    # due_date, start_date, unit_id are deliberately left untouched.

    db.commit()
    db.refresh(booking)
    return booking


def get_or_create_borrower(db: Session, name: str, email: str, club: str | None):
    borrower = db.query(models.Borrower).filter(models.Borrower.email == email).first()
    if borrower:
        return borrower
    borrower = models.Borrower(name=name, email=email, club_or_dept=club)
    db.add(borrower)
    db.commit()
    db.refresh(borrower)
    return borrower


def get_overdue_bookings(db: Session):
    today = date.today()
    return db.query(models.Booking).filter(
        models.Booking.status == "active",
        models.Booking.due_date < today,
    ).all()


def get_active_bookings(db: Session):
    return db.query(models.Booking).filter(models.Booking.status == "active").all()
