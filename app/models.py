from datetime import date
from sqlalchemy import (
    Column, Integer, String, Float, Date, ForeignKey, Boolean
)
from sqlalchemy.orm import relationship
from .database import Base


class EquipmentType(Base):
    """A kind of gear, e.g. 'DSLR Camera'. Holds how many physical units exist
    and the money rules (deposit + late fee) for that kind of gear."""
    __tablename__ = "equipment_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    category = Column(String, nullable=False)  # Camera / Projector / Audio / Support
    deposit_amount = Column(Float, nullable=False, default=0)
    late_fee_per_day = Column(Float, nullable=False, default=0)

    units = relationship("EquipmentUnit", back_populates="type", cascade="all, delete-orphan")


class EquipmentUnit(Base):
    """One physical, trackable unit of a type, e.g. 'DSLR-01'. Popular items
    have several of these rows under the same EquipmentType."""
    __tablename__ = "equipment_units"

    id = Column(Integer, primary_key=True, index=True)
    type_id = Column(Integer, ForeignKey("equipment_types.id"), nullable=False)
    unit_code = Column(String, nullable=False)  # DSLR-01, DSLR-02...
    is_active = Column(Boolean, default=True)   # False = retired / lost / broken

    type = relationship("EquipmentType", back_populates="units")
    bookings = relationship("Booking", back_populates="unit")


class Borrower(Base):
    """A student / club representative who borrows gear."""
    __tablename__ = "borrowers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    club_or_dept = Column(String, nullable=True)

    bookings = relationship("Booking", back_populates="borrower", foreign_keys="Booking.borrower_id")


class Booking(Base):
    """One loan of one specific unit to one borrower for a date window.
    status flows: active -> returned. 'overdue' is computed, not stored,
    so it's always correct even if nobody visits the app for a week."""
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("equipment_units.id"), nullable=False)
    borrower_id = Column(Integer, ForeignKey("borrowers.id"), nullable=False)

    start_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    returned_date = Column(Date, nullable=True)

    deposit_collected = Column(Float, nullable=False, default=0)
    late_fee_charged = Column(Float, nullable=False, default=0)
    deposit_refunded = Column(Float, nullable=True)

    status = Column(String, nullable=False, default="active")  # active | returned

    # Audit trail for transfers: who originally checked it out, and how many
    # times custody has changed hands. borrower_id above always reflects the
    # *current* holder -- the one responsible for returning it / due the fee.
    original_borrower_id = Column(Integer, ForeignKey("borrowers.id"), nullable=True)
    transfer_count = Column(Integer, nullable=False, default=0)

    unit = relationship("EquipmentUnit", back_populates="bookings")
    borrower = relationship("Borrower", back_populates="bookings", foreign_keys=[borrower_id])
    original_borrower = relationship("Borrower", foreign_keys=[original_borrower_id])

    @property
    def is_overdue(self) -> bool:
        return self.status == "active" and self.due_date < date.today()

    @property
    def days_overdue(self) -> int:
        if not self.is_overdue:
            return 0
        return (date.today() - self.due_date).days
