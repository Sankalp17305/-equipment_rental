from datetime import date, timedelta
from urllib.parse import quote

from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from . import models, logic

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AV Room Rental Tracker")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/")
def home(request: Request, start: str | None = None, end: str | None = None,
          db: Session = Depends(get_db)):
    today = date.today()
    start_d = date.fromisoformat(start) if start else today
    end_d = date.fromisoformat(end) if end else today + timedelta(days=2)

    summary = logic.availability_summary(db, start_d, end_d)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "summary": summary,
        "start": start_d.isoformat(),
        "end": end_d.isoformat(),
    })


@app.get("/book")
def book_form(request: Request, type_id: int, start: str, end: str,
              db: Session = Depends(get_db)):
    equipment_type = db.get(models.EquipmentType, type_id)
    return templates.TemplateResponse("book.html", {
        "request": request,
        "type": equipment_type,
        "start": start,
        "end": end,
        "error": None,
    })


@app.post("/book")
def book_submit(
    request: Request,
    type_id: int = Form(...),
    start: str = Form(...),
    end: str = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    club: str = Form(""),
    db: Session = Depends(get_db),
):
    equipment_type = db.get(models.EquipmentType, type_id)
    try:
        borrower = logic.get_or_create_borrower(db, name, email, club)
        logic.create_booking(
            db, borrower, type_id,
            date.fromisoformat(start), date.fromisoformat(end),
        )
    except logic.BookingError as e:
        return templates.TemplateResponse("book.html", {
            "request": request,
            "type": equipment_type,
            "start": start,
            "end": end,
            "error": str(e),
        })
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    active = logic.get_active_bookings(db)
    active.sort(key=lambda b: b.due_date)
    overdue_ids = {b.id for b in logic.get_overdue_bookings(db)}

    reminder_links = {}
    for b in active:
        if b.id in overdue_ids:
            subject = quote(f"Please return the {b.unit.type.name} ({b.unit.unit_code})")
            body = quote(
                f"Hi {b.borrower.name},\n\n"
                f"The {b.unit.type.name} ({b.unit.unit_code}) you borrowed was due back on "
                f"{b.due_date.isoformat()} and is now {b.days_overdue} day(s) overdue.\n"
                f"A late fee of Rs.{b.unit.type.late_fee_per_day}/day applies, deducted from your "
                f"deposit.\n\nPlease return it to the AV room as soon as possible.\n\nThanks!"
            )
            reminder_links[b.id] = f"mailto:{b.borrower.email}?subject={subject}&body={body}"

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "active": active,
        "overdue_ids": overdue_ids,
        "reminder_links": reminder_links,
        "today": date.today(),
    })


@app.post("/return/{booking_id}")
def return_item(booking_id: int, db: Session = Depends(get_db)):
    try:
        logic.return_booking(db, booking_id)
    except logic.BookingError:
        pass
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/transfer/{booking_id}")
def transfer_form(request: Request, booking_id: int, db: Session = Depends(get_db)):
    booking = db.get(models.Booking, booking_id)
    return templates.TemplateResponse("transfer.html", {
        "request": request,
        "booking": booking,
        "error": None,
    })


@app.post("/transfer/{booking_id}")
def transfer_submit(
    request: Request,
    booking_id: int,
    name: str = Form(...),
    email: str = Form(...),
    club: str = Form(""),
    db: Session = Depends(get_db),
):
    booking = db.get(models.Booking, booking_id)
    try:
        new_borrower = logic.get_or_create_borrower(db, name, email, club)
        logic.transfer_booking(db, booking_id, new_borrower)
    except logic.BookingError as e:
        return templates.TemplateResponse("transfer.html", {
            "request": request,
            "booking": booking,
            "error": str(e),
        })
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/history")
def history(request: Request, db: Session = Depends(get_db)):
    returned = db.query(models.Booking).filter(
        models.Booking.status == "returned"
    ).order_by(models.Booking.returned_date.desc()).all()
    return templates.TemplateResponse("history.html", {
        "request": request,
        "returned": returned,
    })
