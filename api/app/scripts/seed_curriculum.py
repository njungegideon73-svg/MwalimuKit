"""Seed the curriculum catalogue and a demo school.

The canonical curriculum content lives as JSON in
``packages/shared/curriculum/data/`` (lower-primary.json, upper-primary.json,
grade-7.json).  This script loads those files so the seed logic and the
frontend catalogue share a single source of truth.  If the JSON files are
unavailable, the embedded ``CATALOGUE`` dict serves as a fallback.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import invalidate_catalogue_cache
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.curriculum import CurriculumLevel, LearningArea, Strand, SubStrand
from app.models.school import School
from app.models.user import User, UserRole

_CURRICULUM_DATA_DIR = Path(__file__).resolve().parents[3] / "packages/shared/curriculum/data"


CATALOGUE: dict = {
    "learning_areas": [
        {"code": "LP-MATH",  "name": "Mathematics",                  "level": "lower_primary", "sort_order": 10},
        {"code": "LP-ENG",   "name": "English",                      "level": "lower_primary", "sort_order": 20},
        {"code": "LP-KIS",   "name": "Kiswahili",                    "level": "lower_primary", "sort_order": 30},
        {"code": "LP-SCI",   "name": "Science and Technology",       "level": "lower_primary", "sort_order": 40},
        {"code": "LP-SST",   "name": "Social Studies",               "level": "lower_primary", "sort_order": 50},
        {"code": "LP-AGR",   "name": "Agriculture and Nutrition",    "level": "lower_primary", "sort_order": 60},
        {"code": "LP-CRE",   "name": "Christian Religious Education","level": "lower_primary", "sort_order": 70},
        {"code": "LP-ART",   "name": "Creative Arts",                "level": "lower_primary", "sort_order": 80},
        {"code": "LP-PE",    "name": "Physical and Health Education","level": "lower_primary", "sort_order": 90},
        {"code": "UP-MATH",  "name": "Mathematics",                  "level": "upper_primary", "sort_order": 110},
        {"code": "UP-ENG",   "name": "English",                      "level": "upper_primary", "sort_order": 120},
        {"code": "UP-KIS",   "name": "Kiswahili",                    "level": "upper_primary", "sort_order": 130},
        {"code": "UP-SCI",   "name": "Science and Technology",       "level": "upper_primary", "sort_order": 140},
        {"code": "UP-SST",   "name": "Social Studies",               "level": "upper_primary", "sort_order": 150},
        {"code": "UP-AGR",   "name": "Agriculture and Nutrition",    "level": "upper_primary", "sort_order": 160},
        {"code": "UP-CRE",   "name": "Christian Religious Education","level": "upper_primary", "sort_order": 170},
        {"code": "UP-ART",   "name": "Creative Arts",                "level": "upper_primary", "sort_order": 180},
        {"code": "UP-PE",    "name": "Physical and Health Education","level": "upper_primary", "sort_order": 190},
         {"code": "JSS-ENG",  "name": "English",                      "level": "jss", "sort_order": 210},
         {"code": "JSS-MATH", "name": "Mathematics",                  "level": "jss", "sort_order": 220},
         {"code": "JSS-SCI",  "name": "Integrated Science",           "level": "jss", "sort_order": 230},
         {"code": "JSS-KIS",  "name": "Kiswahili",                    "level": "jss", "sort_order": 240},
         {"code": "JSS-SST",  "name": "Social Studies",               "level": "jss", "sort_order": 250},
         {"code": "JSS-AGR",  "name": "Agriculture and Nutrition",    "level": "jss", "sort_order": 260},
         # Senior School (Grades 10-12)
         {"code": "SS-STEM-MATH", "name": "Mathematics (STEM)",        "level": "senior_school", "sort_order": 310},
         {"code": "SS-STEM-PHY", "name": "Physics (STEM)",            "level": "senior_school", "sort_order": 311},
         {"code": "SS-STM-CHM", "name": "Chemistry (STEM)",           "level": "senior_school", "sort_order": 312},
         {"code": "SS-STM-BIO", "name": "Biology (STEM)",             "level": "senior_school", "sort_order": 313},
         {"code": "SS-STM-CSC", "name": "Computer Science (STEM)",    "level": "senior_school", "sort_order": 314},
         {"code": "SS-STM-ENG", "name": "Engineering (STEM)",         "level": "senior_school", "sort_order": 315},
         {"code": "SS-SCI-ENG",  "name": "English (Social Sciences)", "level": "senior_school", "sort_order": 320},
         {"code": "SS-SCI-KIS",  "name": "Kiswahili (Social Sciences)","level": "senior_school", "sort_order": 321},
         {"code": "SS-SCI-HIS",  "name": "History (Social Sciences)", "level": "senior_school", "sort_order": 322},
         {"code": "SS-SCI-GEO",  "name": "Geography (Social Sciences)","level": "senior_school", "sort_order": 323},
         {"code": "SS-SCI-CRE",  "name": "CRE (Social Sciences)",     "level": "senior_school", "sort_order": 324},
         {"code": "SS-SCI-BAM",  "name": "Business Studies (Social Sciences)","level": "senior_school", "sort_order": 325},
         {"code": "SS-ART-ENG",  "name": "English (Arts)",            "level": "senior_school", "sort_order": 330},
         {"code": "SS-ART-LIT",  "name": "Literature (Arts)",         "level": "senior_school", "sort_order": 331},
         {"code": "SS-ART-FRK",  "name": "French (Arts)",             "level": "senior_school", "sort_order": 332},
         {"code": "SS-ART-GRM",  "name": "German (Arts)",             "level": "senior_school", "sort_order": 333},
         {"code": "SS-ART-KIS",  "name": "Kiswahili (Arts)",          "level": "senior_school", "sort_order": 334},
         {"code": "SS-ART-MUS",  "name": "Music (Arts & Sports)",     "level": "senior_school", "sort_order": 335},
         {"code": "SS-ART-ART",  "name": "Art and Design (Arts & Sports)","level": "senior_school", "sort_order": 336},
         {"code": "SS-SPT-PE",   "name": "Physical Education (Sports)","level": "senior_school", "sort_order": 340},
         {"code": "SS-SPT-SPT",  "name": "Sports Science (Sports)",   "level": "senior_school", "sort_order": 341},
    ],
    "strands": [
        # Lower Primary
        {"code": "LP-MATH-NUM", "learning_area_code": "LP-MATH", "name": "Numbers", "sort_order": 1},
        {"code": "LP-MATH-MEA", "learning_area_code": "LP-MATH", "name": "Measurement", "sort_order": 2},
        {"code": "LP-MATH-GEO", "learning_area_code": "LP-MATH", "name": "Geometry", "sort_order": 3},
        {"code": "LP-MATH-DAT", "learning_area_code": "LP-MATH", "name": "Data Handling", "sort_order": 4},
        {"code": "LP-ENG-LIS",  "learning_area_code": "LP-ENG",  "name": "Listening and Speaking", "sort_order": 1},
        {"code": "LP-ENG-READ", "learning_area_code": "LP-ENG",  "name": "Reading", "sort_order": 2},
        {"code": "LP-ENG-WRIT", "learning_area_code": "LP-ENG",  "name": "Writing", "sort_order": 3},
        {"code": "LP-ENG-GRAM", "learning_area_code": "LP-ENG",  "name": "Grammar Usage", "sort_order": 4},
        {"code": "LP-KIS-KUS",  "learning_area_code": "LP-KIS",  "name": "Kusikiliza na Kuzungumza", "sort_order": 1},
        {"code": "LP-KIS-KUSO", "learning_area_code": "LP-KIS",  "name": "Kusoma", "sort_order": 2},
        {"code": "LP-KIS-KUAN", "learning_area_code": "LP-KIS",  "name": "Kuandika", "sort_order": 3},
        {"code": "LP-SCI-LIV",  "learning_area_code": "LP-SCI",  "name": "Living Things and Their Environment", "sort_order": 1},
        {"code": "LP-SCI-ENE",  "learning_area_code": "LP-SCI",  "name": "Energy", "sort_order": 2},
        {"code": "LP-SCI-EAR",  "learning_area_code": "LP-SCI",  "name": "Earth and Space", "sort_order": 3},
        {"code": "LP-SST-HER",  "learning_area_code": "LP-SST",  "name": "Heritage", "sort_order": 1},
        {"code": "LP-SST-CIT",  "learning_area_code": "LP-SST",  "name": "Citizenship", "sort_order": 2},
        {"code": "LP-SST-RES",  "learning_area_code": "LP-SST",  "name": "Resources and Economic Activities", "sort_order": 3},
        {"code": "LP-AGR-CRP",  "learning_area_code": "LP-AGR",  "name": "Crop Production", "sort_order": 1},
        {"code": "LP-AGR-NUT",  "learning_area_code": "LP-AGR",  "name": "Nutrition and Hygiene", "sort_order": 2},
        {"code": "LP-CRE-BIB",  "learning_area_code": "LP-CRE",  "name": "The Bible", "sort_order": 1},
        {"code": "LP-CRE-CRE",  "learning_area_code": "LP-CRE",  "name": "Christian Values", "sort_order": 2},
        {"code": "LP-ART-MUS",  "learning_area_code": "LP-ART",  "name": "Music", "sort_order": 1},
        {"code": "LP-ART-ART",  "learning_area_code": "LP-ART",  "name": "Art and Craft", "sort_order": 2},
        {"code": "LP-PE-MOV",   "learning_area_code": "LP-PE",   "name": "Movement", "sort_order": 1},
        {"code": "LP-PE-HEAL",  "learning_area_code": "LP-PE",   "name": "Health and Hygiene", "sort_order": 2},
        # Upper Primary
        {"code": "UP-MATH-NUM", "learning_area_code": "UP-MATH", "name": "Whole Numbers", "sort_order": 1},
        {"code": "UP-MATH-FRA", "learning_area_code": "UP-MATH", "name": "Fractions", "sort_order": 2},
        {"code": "UP-MATH-DEC", "learning_area_code": "UP-MATH", "name": "Decimals and Percentages", "sort_order": 3},
        {"code": "UP-MATH-MEA", "learning_area_code": "UP-MATH", "name": "Measurement", "sort_order": 4},
        {"code": "UP-MATH-GEO", "learning_area_code": "UP-MATH", "name": "Geometry", "sort_order": 5},
        {"code": "UP-MATH-DAT", "learning_area_code": "UP-MATH", "name": "Data Handling", "sort_order": 6},
        {"code": "UP-ENG-READ", "learning_area_code": "UP-ENG",  "name": "Reading comprehension", "sort_order": 1},
        {"code": "UP-ENG-WRIT", "learning_area_code": "UP-ENG",  "name": "Writing composition", "sort_order": 2},
        {"code": "UP-ENG-GRAM", "learning_area_code": "UP-ENG",  "name": "Grammar in context", "sort_order": 3},
        {"code": "UP-ENG-LIT",  "learning_area_code": "UP-ENG",  "name": "Literature appreciation", "sort_order": 4},
        {"code": "UP-KIS-USH",  "learning_area_code": "UP-KIS",  "name": "Ushairi", "sort_order": 1},
        {"code": "UP-KIS-FUP",  "learning_area_code": "UP-KIS",  "name": "Fasihi Simulizi", "sort_order": 2},
        {"code": "UP-KIS-SRN",  "learning_area_code": "UP-KIS",  "name": "Sarufi na Ufundi wa Kiswahili", "sort_order": 3},
        {"code": "UP-SCI-LIV",  "learning_area_code": "UP-SCI",  "name": "Living Things", "sort_order": 1},
        {"code": "UP-SCI-PHY",  "learning_area_code": "UP-SCI",  "name": "Physical Sciences", "sort_order": 2},
        {"code": "UP-SCI-ENE",  "learning_area_code": "UP-SCI",  "name": "Energy and Change", "sort_order": 3},
        {"code": "UP-SST-GEO",  "learning_area_code": "UP-SST",  "name": "Geography", "sort_order": 1},
        {"code": "UP-SST-HIS",  "learning_area_code": "UP-SST",  "name": "History", "sort_order": 2},
        {"code": "UP-SST-CIT",  "learning_area_code": "UP-SST",  "name": "Citizenship", "sort_order": 3},
        {"code": "UP-AGR-CRP",  "learning_area_code": "UP-AGR",  "name": "Crop husbandry", "sort_order": 1},
        {"code": "UP-AGR-LIV",  "learning_area_code": "UP-AGR",  "name": "Livestock keeping", "sort_order": 2},
        {"code": "UP-CRE-BIB",  "learning_area_code": "UP-CRE",  "name": "Biblical teachings", "sort_order": 1},
        {"code": "UP-ART-MUS",  "learning_area_code": "UP-ART",  "name": "Music performance", "sort_order": 1},
        {"code": "UP-ART-ART",  "learning_area_code": "UP-ART",  "name": "Visual arts", "sort_order": 2},
        {"code": "UP-PE-FIT",   "learning_area_code": "UP-PE",   "name": "Physical fitness", "sort_order": 1},
        {"code": "UP-PE-HEAL",  "learning_area_code": "UP-PE",   "name": "Health education", "sort_order": 2},
        # JSS
        {"code": "JSS-ENG-LIS",  "learning_area_code": "JSS-ENG",  "name": "Listening and Speaking", "sort_order": 1},
        {"code": "JSS-ENG-READ", "learning_area_code": "JSS-ENG",  "name": "Reading", "sort_order": 2},
        {"code": "JSS-ENG-WRIT", "learning_area_code": "JSS-ENG",  "name": "Writing", "sort_order": 3},
        {"code": "JSS-MATH-NUM", "learning_area_code": "JSS-MATH", "name": "Numbers and Algebra", "sort_order": 1},
        {"code": "JSS-MATH-MEA", "learning_area_code": "JSS-MATH", "name": "Measurement", "sort_order": 2},
        {"code": "JSS-MATH-GEO", "learning_area_code": "JSS-MATH", "name": "Geometry", "sort_order": 3},
        {"code": "JSS-MATH-DAT", "learning_area_code": "JSS-MATH", "name": "Statistics and Probability", "sort_order": 4},
        {"code": "JSS-SCI-LIV",  "learning_area_code": "JSS-SCI",  "name": "Living Things", "sort_order": 1},
        {"code": "JSS-SCI-CHM",  "learning_area_code": "JSS-SCI",  "name": "Chemistry", "sort_order": 2},
        {"code": "JSS-SCI-PHY",  "learning_area_code": "JSS-SCI",  "name": "Physics", "sort_order": 3},
        {"code": "JSS-SCI-ECO",  "learning_area_code": "JSS-SCI",  "name": "Ecology", "sort_order": 4},
        {"code": "JSS-KIS-USH",  "learning_area_code": "JSS-KIS",  "name": "Ushairi", "sort_order": 1},
        {"code": "JSS-KIS-FUP",  "learning_area_code": "JSS-KIS",  "name": "Fasihi Simulizi", "sort_order": 2},
        {"code": "JSS-KIS-SAR",  "learning_area_code": "JSS-KIS",  "name": "Sarufi", "sort_order": 3},
        {"code": "JSS-SST-GEO",  "learning_area_code": "JSS-SST",  "name": "Geography", "sort_order": 1},
        {"code": "JSS-SST-HIS",  "learning_area_code": "JSS-SST",  "name": "History and Civics", "sort_order": 2},
        {"code": "JSS-AGR-CRP",  "learning_area_code": "JSS-AGR",  "name": "Crop production", "sort_order": 1},
        {"code": "JSS-AGR-LIV",  "learning_area_code": "JSS-AGR",  "name": "Livestock production", "sort_order": 2},
    ],
    "sub_strands": [
        {"code": "LP-MATH-NUM-1.1", "strand_code": "LP-MATH-NUM", "name": "Counting 0 to 20", "sort_order": 1},
        {"code": "LP-MATH-NUM-1.2", "strand_code": "LP-MATH-NUM", "name": "Place value 0 to 20", "sort_order": 2},
        {"code": "LP-MATH-NUM-2.1", "strand_code": "LP-MATH-NUM", "name": "Counting 0 to 100", "sort_order": 3},
        {"code": "LP-MATH-NUM-2.2", "strand_code": "LP-MATH-NUM", "name": "Addition within 20", "sort_order": 4},
        {"code": "LP-MATH-NUM-2.3", "strand_code": "LP-MATH-NUM", "name": "Subtraction within 20", "sort_order": 5},
        {"code": "LP-MATH-NUM-3.1", "strand_code": "LP-MATH-NUM", "name": "Counting in 2s, 5s and 10s", "sort_order": 6},
        {"code": "LP-MATH-MEA-1.1", "strand_code": "LP-MATH-MEA", "name": "Comparing length", "sort_order": 1},
        {"code": "LP-MATH-MEA-2.1", "strand_code": "LP-MATH-MEA", "name": "Measuring length in centimetres", "sort_order": 2},
        {"code": "LP-MATH-MEA-2.2", "strand_code": "LP-MATH-MEA", "name": "Mass (heavier/lighter)", "sort_order": 3},
        {"code": "LP-MATH-MEA-3.1", "strand_code": "LP-MATH-MEA", "name": "Telling the time (o'clock)", "sort_order": 4},
        {"code": "LP-MATH-GEO-1.1", "strand_code": "LP-MATH-GEO", "name": "Shapes in the environment", "sort_order": 1},
        {"code": "LP-MATH-GEO-2.1", "strand_code": "LP-MATH-GEO", "name": "Sorting 2D shapes", "sort_order": 2},
        {"code": "LP-MATH-GEO-3.1", "strand_code": "LP-MATH-GEO", "name": "Patterns with shapes", "sort_order": 3},
        {"code": "LP-MATH-DAT-2.1", "strand_code": "LP-MATH-DAT", "name": "Sorting objects into groups", "sort_order": 1},
        {"code": "LP-MATH-DAT-3.1", "strand_code": "LP-MATH-DAT", "name": "Pictographs", "sort_order": 2},
        {"code": "LP-ENG-LIS-1.1", "strand_code": "LP-ENG-LIS",  "name": "Greetings and courtesy words", "sort_order": 1},
        {"code": "LP-ENG-LIS-2.1", "strand_code": "LP-ENG-LIS",  "name": "Listening to short stories", "sort_order": 2},
        {"code": "LP-ENG-LIS-3.1", "strand_code": "LP-ENG-LIS",  "name": "Pronunciation and rhymes", "sort_order": 3},
        {"code": "LP-ENG-READ-1.1", "strand_code": "LP-ENG-READ", "name": "Letter recognition", "sort_order": 1},
        {"code": "LP-ENG-READ-2.1", "strand_code": "LP-ENG-READ", "name": "Reading simple words", "sort_order": 2},
        {"code": "LP-ENG-READ-3.1", "strand_code": "LP-ENG-READ", "name": "Reading short passages and answering questions", "sort_order": 3},
        {"code": "LP-ENG-WRIT-1.1", "strand_code": "LP-ENG-WRIT", "name": "Tracing and copying letters", "sort_order": 1},
        {"code": "LP-ENG-WRIT-2.1", "strand_code": "LP-ENG-WRIT", "name": "Writing simple sentences", "sort_order": 2},
        {"code": "LP-ENG-WRIT-3.1", "strand_code": "LP-ENG-WRIT", "name": "Composing short paragraphs", "sort_order": 3},
        {"code": "LP-ENG-GRAM-1.1", "strand_code": "LP-ENG-GRAM", "name": "Nouns (people, places, things)", "sort_order": 1},
        {"code": "LP-ENG-GRAM-2.1", "strand_code": "LP-ENG-GRAM", "name": "Verbs (action words)", "sort_order": 2},
        {"code": "LP-ENG-GRAM-3.1", "strand_code": "LP-ENG-GRAM", "name": "Punctuation (. ? !)", "sort_order": 3},
        {"code": "LP-KIS-KUS-1.1",  "strand_code": "LP-KIS-KUS",  "name": "Salamu na maneno ya heshima", "sort_order": 1},
        {"code": "LP-KIS-KUS-2.1",  "strand_code": "LP-KIS-KUS",  "name": "Kusikiliza hadithi fupi", "sort_order": 2},
        {"code": "LP-KIS-KUSO-1.1", "strand_code": "LP-KIS-KUSO", "name": "Kutambua herufi", "sort_order": 1},
        {"code": "LP-KIS-KUSO-2.1", "strand_code": "LP-KIS-KUSO", "name": "Kusoma maneno mafupi", "sort_order": 2},
        {"code": "LP-KIS-KUAN-1.1", "strand_code": "LP-KIS-KUAN", "name": "Kunakili herufi", "sort_order": 1},
        {"code": "LP-KIS-KUAN-2.1", "strand_code": "LP-KIS-KUAN", "name": "Kuandika sentensi fupi", "sort_order": 2},
        {"code": "LP-SCI-LIV-2.1", "strand_code": "LP-SCI-LIV", "name": "Parts of a plant", "sort_order": 1},
        {"code": "LP-SCI-LIV-2.2", "strand_code": "LP-SCI-LIV", "name": "Animals around the home", "sort_order": 2},
        {"code": "LP-SCI-ENE-2.1", "strand_code": "LP-SCI-ENE", "name": "Sources of energy (sun, fire, charcoal)", "sort_order": 1},
        {"code": "LP-SCI-EAR-2.1", "strand_code": "LP-SCI-EAR", "name": "Weather and seasons", "sort_order": 1},
        {"code": "LP-SST-HER-2.1", "strand_code": "LP-SST-HER", "name": "My family and community", "sort_order": 1},
        {"code": "LP-SST-CIT-2.1", "strand_code": "LP-SST-CIT", "name": "Rules at home and school", "sort_order": 1},
        {"code": "LP-SST-RES-2.1", "strand_code": "LP-SST-RES", "name": "Goods and services in my county", "sort_order": 1},
        {"code": "LP-AGR-CRP-2.1", "strand_code": "LP-AGR-CRP", "name": "Planting and caring for crops", "sort_order": 1},
        {"code": "LP-AGR-NUT-2.1", "strand_code": "LP-AGR-NUT", "name": "Food groups and balanced diet", "sort_order": 1},
        {"code": "LP-CRE-BIB-2.1", "strand_code": "LP-CRE-BIB", "name": "Stories of creation", "sort_order": 1},
        {"code": "LP-CRE-CRE-2.1", "strand_code": "LP-CRE-CRE", "name": "Love, honesty and respect", "sort_order": 1},
        {"code": "LP-ART-MUS-2.1", "strand_code": "LP-ART-MUS", "name": "Singing Kenyan songs", "sort_order": 1},
        {"code": "LP-ART-ART-2.1", "strand_code": "LP-ART-ART", "name": "Drawing familiar objects", "sort_order": 1},
        {"code": "LP-PE-MOV-1.1",  "strand_code": "LP-PE-MOV",  "name": "Locomotor movements", "sort_order": 1},
        {"code": "LP-PE-HEAL-2.1", "strand_code": "LP-PE-HEAL", "name": "Personal hygiene habits", "sort_order": 1},
        # Upper Primary sub-strands
        {"code": "UP-MATH-NUM-1.1", "strand_code": "UP-MATH-NUM", "name": "Place value (millions)", "sort_order": 1},
        {"code": "UP-MATH-NUM-1.2", "strand_code": "UP-MATH-NUM", "name": "Operations on whole numbers", "sort_order": 2},
        {"code": "UP-MATH-FRA-1.1", "strand_code": "UP-MATH-FRA", "name": "Proper and improper fractions", "sort_order": 1},
        {"code": "UP-MATH-FRA-1.2", "strand_code": "UP-MATH-FRA", "name": "Operations with fractions", "sort_order": 2},
        {"code": "UP-MATH-DEC-1.1", "strand_code": "UP-MATH-DEC", "name": "Decimal notation", "sort_order": 1},
        {"code": "UP-MATH-DEC-1.2", "strand_code": "UP-MATH-DEC", "name": "Percentages", "sort_order": 2},
        {"code": "UP-MATH-MEA-1.1", "strand_code": "UP-MATH-MEA", "name": "Length and perimeter", "sort_order": 1},
        {"code": "UP-MATH-MEA-1.2", "strand_code": "UP-MATH-MEA", "name": "Area and volume", "sort_order": 2},
        {"code": "UP-MATH-MEA-1.3", "strand_code": "UP-MATH-MEA", "name": "Mass and capacity", "sort_order": 3},
        {"code": "UP-MATH-GEO-1.1", "strand_code": "UP-MATH-GEO", "name": "2D shapes and properties", "sort_order": 1},
        {"code": "UP-MATH-GEO-1.2", "strand_code": "UP-MATH-GEO", "name": "3D objects", "sort_order": 2},
        {"code": "UP-MATH-DAT-1.1", "strand_code": "UP-MATH-DAT", "name": "Collecting and organising data", "sort_order": 1},
        {"code": "UP-MATH-DAT-1.2", "strand_code": "UP-MATH-DAT", "name": "Bar graphs and tables", "sort_order": 2},
        {"code": "UP-ENG-READ-1.1", "strand_code": "UP-ENG-READ", "name": "Reading comprehension strategies", "sort_order": 1},
        {"code": "UP-ENG-READ-1.2", "strand_code": "UP-ENG-READ", "name": "Summary and main idea", "sort_order": 2},
        {"code": "UP-ENG-WRIT-1.1", "strand_code": "UP-ENG-WRIT", "name": "Narrative writing", "sort_order": 1},
        {"code": "UP-ENG-WRIT-1.2", "strand_code": "UP-ENG-WRIT", "name": "Expository writing", "sort_order": 2},
        {"code": "UP-ENG-GRAM-1.1", "strand_code": "UP-ENG-GRAM", "name": "Tenses (past, present, future)", "sort_order": 1},
        {"code": "UP-ENG-GRAM-1.2", "strand_code": "UP-ENG-GRAM", "name": "Active and passive voice", "sort_order": 2},
        {"code": "UP-ENG-LIT-1.1",  "strand_code": "UP-ENG-LIT",  "name": "Elements of a story", "sort_order": 1},
        {"code": "UP-KIS-USH-1.1",  "strand_code": "UP-KIS-USH",  "name": "Mizizi na aina za ushairi", "sort_order": 1},
        {"code": "UP-KIS-FUP-1.1",  "strand_code": "UP-KIS-FUP",  "name": "Hadithi na tamthilia", "sort_order": 1},
        {"code": "UP-KIS-SRN-1.1",  "strand_code": "UP-KIS-SRN",  "name": "Viungo na aina za maneno", "sort_order": 1},
        {"code": "UP-SCI-LIV-1.1",  "strand_code": "UP-SCI-LIV",  "name": "Classification of living things", "sort_order": 1},
        {"code": "UP-SCI-LIV-1.2",  "strand_code": "UP-SCI-LIV",  "name": "Human body systems", "sort_order": 2},
        {"code": "UP-SCI-PHY-1.1",  "strand_code": "UP-SCI-PHY",  "name": "Properties of matter", "sort_order": 1},
        {"code": "UP-SCI-ENE-1.1",  "strand_code": "UP-SCI-ENE",  "name": "Forms of energy", "sort_order": 1},
        {"code": "UP-SST-GEO-1.1",  "strand_code": "UP-SST-GEO",  "name": "Map reading skills", "sort_order": 1},
        {"code": "UP-SST-HIS-1.1",  "strand_code": "UP-SST-HIS",  "name": "Early human communities", "sort_order": 1},
        {"code": "UP-SST-CIT-1.1",  "strand_code": "UP-SST-CIT",  "name": "Government and leadership", "sort_order": 1},
        {"code": "UP-AGR-CRP-1.1",  "strand_code": "UP-AGR-CRP",  "name": "Soil preparation and planting", "sort_order": 1},
        {"code": "UP-AGR-LIV-1.1",  "strand_code": "UP-AGR-LIV",  "name": "Types of livestock", "sort_order": 1},
        {"code": "UP-CRE-BIB-1.1",  "strand_code": "UP-CRE-BIB",  "name": "Old Testament stories", "sort_order": 1},
        {"code": "UP-ART-MUS-1.1",  "strand_code": "UP-ART-MUS",  "name": "Rhythm and melody", "sort_order": 1},
        {"code": "UP-ART-ART-1.1",  "strand_code": "UP-ART-ART",  "name": "Colour mixing and texture", "sort_order": 1},
        {"code": "UP-PE-FIT-1.1",   "strand_code": "UP-PE-FIT",   "name": "Warm-up and cool-down exercises", "sort_order": 1},
        {"code": "UP-PE-HEAL-1.1",  "strand_code": "UP-PE-HEAL",  "name": "Nutrition and disease prevention", "sort_order": 1},
        # Expanded JSS sub-strands
        {"code": "JSS-ENG-LIS-1.1",  "strand_code": "JSS-ENG-LIS",  "name": "Listening for gist and detail", "sort_order": 1},
        {"code": "JSS-ENG-LIS-1.2",  "strand_code": "JSS-ENG-LIS",  "name": "Formal and informal conversations", "sort_order": 2},
        {"code": "JSS-ENG-READ-1.1", "strand_code": "JSS-ENG-READ", "name": "Reading comprehension", "sort_order": 1},
        {"code": "JSS-ENG-READ-1.2", "strand_code": "JSS-ENG-READ", "name": "Poetry appreciation", "sort_order": 2},
        {"code": "JSS-ENG-WRIT-1.1", "strand_code": "JSS-ENG-WRIT", "name": "Paragraph writing", "sort_order": 1},
        {"code": "JSS-ENG-WRIT-1.2", "strand_code": "JSS-ENG-WRIT", "name": "Essay writing", "sort_order": 2},
        {"code": "JSS-MATH-NUM-1.1", "strand_code": "JSS-MATH-NUM", "name": "Integers and operations", "sort_order": 1},
        {"code": "JSS-MATH-NUM-1.2", "strand_code": "JSS-MATH-NUM", "name": "Algebraic expressions", "sort_order": 2},
        {"code": "JSS-MATH-NUM-1.3", "strand_code": "JSS-MATH-NUM", "name": "Linear equations", "sort_order": 3},
        {"code": "JSS-MATH-MEA-1.1", "strand_code": "JSS-MATH-MEA", "name": "Perimeter and area", "sort_order": 1},
        {"code": "JSS-MATH-MEA-1.2", "strand_code": "JSS-MATH-MEA", "name": "Volume and surface area", "sort_order": 2},
        {"code": "JSS-MATH-GEO-1.1", "strand_code": "JSS-MATH-GEO", "name": "Angles and triangles", "sort_order": 1},
        {"code": "JSS-MATH-GEO-1.2", "strand_code": "JSS-MATH-GEO", "name": "Pythagoras theorem", "sort_order": 2},
        {"code": "JSS-MATH-DAT-1.1", "strand_code": "JSS-MATH-DAT", "name": "Statistics and probability", "sort_order": 1},
        {"code": "JSS-SCI-LIV-1.1",  "strand_code": "JSS-SCI-LIV",  "name": "Cell structure and function", "sort_order": 1},
        {"code": "JSS-SCI-LIV-1.2",  "strand_code": "JSS-SCI-LIV",  "name": "Nutrition and health", "sort_order": 2},
        {"code": "JSS-SCI-CHM-1.1",  "strand_code": "JSS-SCI-CHM",  "name": "States of matter", "sort_order": 1},
        {"code": "JSS-SCI-CHM-1.2",  "strand_code": "JSS-SCI-CHM",  "name": "Elements and compounds", "sort_order": 2},
        {"code": "JSS-SCI-PHY-1.1",  "strand_code": "JSS-SCI-PHY",  "name": "Force and motion", "sort_order": 1},
        {"code": "JSS-SCI-PHY-1.2",  "strand_code": "JSS-SCI-PHY",  "name": "Sound and light", "sort_order": 2},
        {"code": "JSS-SCI-ECO-1.1",  "strand_code": "JSS-SCI-ECO",  "name": "Ecosystems and biodiversity", "sort_order": 1},
        {"code": "JSS-SCI-ECO-1.2",  "strand_code": "JSS-SCI-ECO",  "name": "Environmental conservation", "sort_order": 2},
        {"code": "JSS-KIS-USH-1.1",  "strand_code": "JSS-KIS-USH",  "name": "Ushairi wa Kiswahili", "sort_order": 1},
        {"code": "JSS-KIS-FUP-1.1",  "strand_code": "JSS-KIS-FUP",  "name": "Fasihi simulizi", "sort_order": 1},
        {"code": "JSS-KIS-SAR-1.1",  "strand_code": "JSS-KIS-SAR",  "name": "Sarufi ya Kiswahili", "sort_order": 1},
        {"code": "JSS-SST-GEO-1.1",  "strand_code": "JSS-SST-GEO",  "name": "Physical geography", "sort_order": 1},
        {"code": "JSS-SST-GEO-1.2",  "strand_code": "JSS-SST-GEO",  "name": "Human-environment interaction", "sort_order": 2},
        {"code": "JSS-SST-HIS-1.1",  "strand_code": "JSS-SST-HIS",  "name": "Pre-colonial African communities", "sort_order": 1},
        {"code": "JSS-SST-HIS-1.2",  "strand_code": "JSS-SST-HIS",  "name": "Colonialism in East Africa", "sort_order": 2},
        {"code": "JSS-AGR-CRP-1.1",  "strand_code": "JSS-AGR-CRP",  "name": "Crop production", "sort_order": 1},
        {"code": "JSS-AGR-CRP-1.2",  "strand_code": "JSS-AGR-CRP",  "name": "Crop pest and disease management", "sort_order": 2},
        {"code": "JSS-AGR-LIV-1.1",  "strand_code": "JSS-AGR-LIV",  "name": "Livestock production", "sort_order": 1},
        {"code": "JSS-AGR-LIV-1.2",  "strand_code": "JSS-AGR-LIV",  "name": "Common livestock diseases", "sort_order": 2},
    ],
}


def _load_catalogue_json() -> dict:
    """Load curriculum JSON seed files from the shared packages directory.

    Falls back to the embedded ``CATALOGUE`` dict if the JSON files are
    not present (e.g. running the script outside the monorepo).
    """
    json_files = ["lower-primary.json", "grade-7.json"]
    merged: dict[str, list] = {"learning_areas": [], "strands": [], "sub_strands": []}

    for fname in json_files:
        path = _CURRICULUM_DATA_DIR / fname
        if not path.exists():
            continue
        with open(path) as fh:
            data = json.load(fh)
            for key, value in merged.items():
                value.extend(data.get(key, []))

    if not merged["learning_areas"]:
        return CATALOGUE

    return merged


async def upsert_all(db: AsyncSession) -> None:
    catalogue = _load_catalogue_json()

    la_by_code: dict[str, LearningArea] = {}
    existing_las = (await db.execute(select(LearningArea))).scalars().all()
    for la in existing_las:
        la_by_code[la.code] = la

    for row in catalogue["learning_areas"]:
        if row["code"] in la_by_code:
            continue
        la = LearningArea(
            id=uuid4(),
            code=row["code"],
            name=row["name"],
            level=CurriculumLevel(row["level"]),
            sort_order=row["sort_order"],
        )
        db.add(la)
        la_by_code[row["code"]] = la
    await db.flush()

    strand_by_code: dict[str, Strand] = {}
    existing_ss = (await db.execute(select(Strand))).scalars().all()
    for s in existing_ss:
        strand_by_code[s.code] = s

    for row in catalogue["strands"]:
        if row["code"] in strand_by_code:
            continue
        la = la_by_code[row["learning_area_code"]]
        s = Strand(
            id=uuid4(),
            learning_area_id=la.id,
            code=row["code"],
            name=row["name"],
            sort_order=row["sort_order"],
        )
        db.add(s)
        strand_by_code[row["code"]] = s
    await db.flush()

    existing_subs = (await db.execute(select(SubStrand))).scalars().all()
    have = {s.code for s in existing_subs}
    for row in catalogue["sub_strands"]:
        if row["code"] in have:
            continue
        parent = strand_by_code[row["strand_code"]]
        db.add(
            SubStrand(
                id=uuid4(),
                strand_id=parent.id,
                code=row["code"],
                name=row["name"],
                sort_order=row["sort_order"],
            )
        )
    await db.commit()


async def seed_demo_school(db: AsyncSession) -> None:
    """Create a demo school and teacher if they don't exist."""
    existing = (await db.execute(select(School).where(School.code == "DEMO01"))).scalar_one_or_none()
    if existing:
        return

    school = School(
        id=uuid4(),
        name="Demo Primary School",
        code="DEMO01",
        county="Nairobi",
        level="primary",
        settings={},
    )
    db.add(school)
    await db.flush()

    teacher = User(
        id=uuid4(),
        school_id=school.id,
        email="teacher@demo.mwalimukit.go.ke",
        full_name="Demo Teacher",
        role=UserRole.teacher,
        password_hash=hash_password("password123"),
        is_active=True,
    )
    db.add(teacher)
    await db.commit()
    print("Demo school created: code=DEMO01, teacher=teacher@demo.mwalimukit.go.ke / password123")


async def main() -> None:
    env = os.environ.get("API_ENV", "development")
    async with SessionLocal() as db:
        await upsert_all(db)
        if env != "production":
            await seed_demo_school(db)
    # Invalidate the curriculum catalogue cache since data changed.
    await invalidate_catalogue_cache()
    print("Seeding complete.")


if __name__ == "__main__":
    asyncio.run(main())
