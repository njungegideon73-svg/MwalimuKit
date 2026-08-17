"""Seed the curriculum catalogue and a demo school.

The TypeScript catalogue in packages/shared/curriculum/data/catalogue.ts is the
canonical source. This module is a hand-maintained mirror so the seed script
does not need a TS toolchain. If you add a new strand/sub-strand in the TS
catalogue, mirror it here too.
"""
from __future__ import annotations

import asyncio
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.curriculum import CurriculumLevel, LearningArea, Strand, SubStrand
from app.models.school import School
from app.models.user import User, UserRole


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
        {"code": "JSS-ENG",  "name": "English",                      "level": "jss", "sort_order": 110},
        {"code": "JSS-MATH", "name": "Mathematics",                  "level": "jss", "sort_order": 120},
        {"code": "JSS-SCI",  "name": "Integrated Science",           "level": "jss", "sort_order": 130},
    ],
    "strands": [
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
        {"code": "JSS-ENG-LIS",  "learning_area_code": "JSS-ENG",  "name": "Listening and Speaking", "sort_order": 1},
        {"code": "JSS-ENG-READ", "learning_area_code": "JSS-ENG",  "name": "Reading", "sort_order": 2},
        {"code": "JSS-ENG-WRIT", "learning_area_code": "JSS-ENG",  "name": "Writing", "sort_order": 3},
        {"code": "JSS-MATH-NUM", "learning_area_code": "JSS-MATH", "name": "Numbers and Algebra", "sort_order": 1},
        {"code": "JSS-MATH-MEA", "learning_area_code": "JSS-MATH", "name": "Measurement", "sort_order": 2},
        {"code": "JSS-MATH-GEO", "learning_area_code": "JSS-MATH", "name": "Geometry", "sort_order": 3},
        {"code": "JSS-SCI-LIV",  "learning_area_code": "JSS-SCI",  "name": "Living Things", "sort_order": 1},
        {"code": "JSS-SCI-CHM",  "learning_area_code": "JSS-SCI",  "name": "Chemistry basics", "sort_order": 2},
        {"code": "JSS-SCI-PHY",  "learning_area_code": "JSS-SCI",  "name": "Physics basics", "sort_order": 3},
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
        {"code": "JSS-ENG-LIS-1.1",  "strand_code": "JSS-ENG-LIS",  "name": "Listening for gist and detail", "sort_order": 1},
        {"code": "JSS-ENG-READ-1.1", "strand_code": "JSS-ENG-READ", "name": "Reading comprehension", "sort_order": 1},
        {"code": "JSS-ENG-WRIT-1.1", "strand_code": "JSS-ENG-WRIT", "name": "Paragraph writing", "sort_order": 1},
        {"code": "JSS-MATH-NUM-1.1", "strand_code": "JSS-MATH-NUM", "name": "Integers and operations", "sort_order": 1},
        {"code": "JSS-MATH-MEA-1.1", "strand_code": "JSS-MATH-MEA", "name": "Perimeter and area", "sort_order": 1},
        {"code": "JSS-MATH-GEO-1.1", "strand_code": "JSS-MATH-GEO", "name": "Angles and triangles", "sort_order": 1},
        {"code": "JSS-SCI-LIV-1.1", "strand_code": "JSS-SCI-LIV", "name": "Cell structure and function", "sort_order": 1},
        {"code": "JSS-SCI-CHM-1.1", "strand_code": "JSS-SCI-CHM", "name": "States of matter", "sort_order": 1},
        {"code": "JSS-SCI-PHY-1.1", "strand_code": "JSS-SCI-PHY", "name": "Force and motion", "sort_order": 1},
    ],
}


async def upsert_all(db: AsyncSession) -> None:
    la_by_code: dict[str, LearningArea] = {}
    existing_las = (await db.execute(select(LearningArea))).scalars().all()
    for la in existing_las:
        la_by_code[la.code] = la

    for row in CATALOGUE["learning_areas"]:
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

    for row in CATALOGUE["strands"]:
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
    for row in CATALOGUE["sub_strands"]:
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
    print(f"Demo school created: code=DEMO01, teacher=teacher@demo.mwalimukit.go.ke / password123")


async def main() -> None:
    async with SessionLocal() as db:
        await upsert_all(db)
        await seed_demo_school(db)
    print("Seeding complete.")


if __name__ == "__main__":
    asyncio.run(main())
