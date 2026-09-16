"""Run once to populate sample gear so the app isn't empty on first run.
    python -m app.seed
"""
from .database import Base, engine, SessionLocal
from . import models

Base.metadata.create_all(bind=engine)

SAMPLE_TYPES = [
    # name,              category,    deposit, late_fee_per_day, unit_count
    ("DSLR Camera",       "Camera",    2000, 100, 3),
    ("Projector",         "Projector", 1500, 75,  4),
    ("Wireless Mic",      "Audio",     500,  25,  5),
    ("Tripod",            "Support",   300,  15,  4),
]


def run():
    db = SessionLocal()
    if db.query(models.EquipmentType).count() > 0:
        print("Already seeded, skipping.")
        return

    for name, category, deposit, fee, count in SAMPLE_TYPES:
        et = models.EquipmentType(
            name=name, category=category,
            deposit_amount=deposit, late_fee_per_day=fee,
        )
        db.add(et)
        db.flush()  # get et.id
        for i in range(1, count + 1):
            code = f"{name.split()[0].upper()}-{i:02d}"
            db.add(models.EquipmentUnit(type_id=et.id, unit_code=code))
    db.commit()
    print("Seeded sample equipment.")


if __name__ == "__main__":
    run()
