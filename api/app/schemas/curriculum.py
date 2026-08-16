"""Curriculum schemas."""
from __future__ import annotations

from pydantic import BaseModel


class LearningAreaOut(BaseModel):
    code: str
    name: str
    level: str
    sort_order: int


class StrandOut(BaseModel):
    code: str
    learning_area_code: str
    name: str
    sort_order: int


class SubStrandOut(BaseModel):
    code: str
    strand_code: str
    name: str
    sort_order: int


class CurriculumCatalogue(BaseModel):
    learning_areas: list[LearningAreaOut]
    strands: list[StrandOut]
    sub_strands: list[SubStrandOut]
