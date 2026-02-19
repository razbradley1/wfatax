"""SQLAlchemy models for the tax planning application."""

import json
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, DateTime,
    ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from .database import Base


class Household(Base):
    __tablename__ = "households"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    primary_name = Column(String(255))
    primary_dob = Column(String(10))  # YYYY-MM-DD
    primary_ssn_last4 = Column(String(4))
    secondary_name = Column(String(255))
    secondary_dob = Column(String(10))
    filing_status = Column(String(10), default="single")
    state = Column(String(2))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tax_returns = relationship("TaxReturn", back_populates="household", cascade="all, delete-orphan")
    scenarios = relationship("Scenario", back_populates="household", cascade="all, delete-orphan")
    tax_letters = relationship("TaxLetter", back_populates="household", cascade="all, delete-orphan")


class TaxReturn(Base):
    __tablename__ = "tax_returns"

    id = Column(Integer, primary_key=True, index=True)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    tax_year = Column(Integer, nullable=False)
    filing_status = Column(String(10))
    raw_pdf_path = Column(String(512))
    extracted_data = Column(JSON, default=dict)
    needs_review_fields = Column(JSON, default=list)  # Fields flagged during extraction
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    household = relationship("Household", back_populates="tax_returns")


class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    tax_year = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    source_return_id = Column(Integer, ForeignKey("tax_returns.id"), nullable=True)
    is_readonly = Column(Boolean, default=False)
    inputs = Column(JSON, default=dict)
    calculated_outputs = Column(JSON, default=dict)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    household = relationship("Household", back_populates="scenarios")
    source_return = relationship("TaxReturn", foreign_keys=[source_return_id])


class TaxLetter(Base):
    __tablename__ = "tax_letters"

    id = Column(Integer, primary_key=True, index=True)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    tax_year = Column(Integer, nullable=False)
    sections = Column(JSON, default=list)
    status = Column(String(20), default="draft")  # draft | in_review | complete
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    household = relationship("Household", back_populates="tax_letters")


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(Text)
