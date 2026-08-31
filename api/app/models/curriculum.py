"""Curriculum models: LearningArea -> Strand -> SubStrand."""
from __future__ import annotations

from enum import Enum as PyEnum

from sqlalchemy import Enum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPK


class CurriculumLevel(str, PyEnum):
    """CBC/CBE educational levels per Kenya's 2-6-3-3-3 structure.

    Early Years Education:
      - Pre-Primary (PP1, PP2): Ages 4-5
      - Lower Primary (Grades 1-3): Ages 6-8

    Middle School Education:
      - Upper Primary (Grades 4-6): Ages 9-11
      - Junior School / JSS (Grades 7-9): Ages 12-15

    Senior School Education:
      - Senior School (Grades 10-12): Ages 15-18
        (STEM, Social Sciences, Arts and Sports Science pathways)
    """
    pre_primary = "pre_primary"
    lower_primary = "lower_primary"
    upper_primary = "upper_primary"
    jss = "jss"
    senior_school = "senior_school"


class LearningArea(UUIDPK, Timestamped, Base):
    __tablename__ = "learning_areas"

    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[CurriculumLevel] = mapped_column(
        Enum(CurriculumLevel, name="curriculum_level", native_enum=False), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Strand(UUIDPK, Timestamped, Base):
    __tablename__ = "strands"

    learning_area_id: Mapped["__import__('uuid').UUID"] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("learning_areas.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class SubStrand(UUIDPK, Timestamped, Base):
    __tablename__ = "sub_strands"

    strand_id: Mapped["__import__('uuid').UUID"] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("strands.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
