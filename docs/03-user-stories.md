# 03 — User Stories

Stories are scoped to **v0.1 MVP** unless tagged `[later]`. Story IDs map
to the functional spec in `04-functional-spec.md`.

## Authentication & onboarding

| ID    | Story                                                                                                                       |
| ----- | --------------------------------------------------------------------------------------------------------------------------- |
| US-01 | As a new teacher, I can sign up with my email, name, school code, and a password so I can start using MwalimuKit.            |
| US-02 | As a returning teacher, I can log in and land on my dashboard.                                                              |
| US-03 | As a school admin, I can create a school with a unique code so teachers can join. `[later]`                                  |
| US-04 | As a teacher, I can join an existing school by entering its code so my data is scoped correctly.                            |

## Curriculum browsing

| ID    | Story                                                                                                                       |
| ----- | --------------------------------------------------------------------------------------------------------------------------- |
| US-10 | As a teacher, I can browse learning areas by level (Lower Primary, Upper Primary, JSS) so I can find the one I teach.       |
| US-11 | As a teacher, I can pick a strand and sub-strand from a list, with the official KICD label visible.                         |
| US-12 | As a teacher, I can search across strands by keyword because there are hundreds.                                            |

## Assessment generation

| ID    | Story                                                                                                                       |
| ----- | --------------------------------------------------------------------------------------------------------------------------- |
| US-20 | As a teacher, I can pick a strand and ask the AI to draft 5 assessment items + a 4-level rubric, and I can edit each item.   |
| US-21 | As a teacher, I can switch to "structured template" mode and fill in items + rubric myself when I don't want AI involved.    |
| US-22 | As a teacher, I can save an assessment, name it, tag it to a strand, and find it later in my library.                       |
| US-23 | As a teacher, I can duplicate a previous assessment to reuse it for the next term.                                          |
| US-24 | As a teacher, I can mark an assessment as "shared with my school" so colleagues can clone it. `[later]`                     |

## Class register & score entry

| ID    | Story                                                                                                                       |
| ----- | --------------------------------------------------------------------------------------------------------------------------- |
| US-30 | As a teacher, I can create a class with a name, grade level, and learning area.                                              |
| US-31 | As a teacher, I can add learners to a class by name and (optional) admission number.                                        |
| US-32 | As a teacher, I can paste a CSV of names to bulk-add learners.                                                               |
| US-33 | As a teacher, I can open a saved assessment against a class and see the learners as rows + the rubric as columns.            |
| US-34 | As a teacher, I can tap a cell to record a level (1–4) for each learner.                                                    |
| US-35 | As a teacher, I can enter scores with no internet and see a clear "saved offline" indicator.                                |
| US-36 | As a teacher, I can see scores sync automatically when connectivity returns.                                                 |

## Reports `[later — v1.x]`

| ID    | Story                                                                                                                       |
| ----- | --------------------------------------------------------------------------------------------------------------------------- |
| US-40 | As a teacher, I can export a per-learner report card PDF aligned to KPSEA's expected format.                                |
| US-41 | As a school head, I can export a class-level summary CSV.                                                                   |

## Admin `[later]`

| ID    | Story                                                                                                                       |
| ----- | --------------------------------------------------------------------------------------------------------------------------- |
| US-50 | As a school admin, I can see how many assessments my teachers have run this term. `[later]`                                  |
| US-51 | As a platform owner, I can flip the paywall on for a school without redeploying.                                             |

## Cross-cutting quality bars

Every story above must also satisfy:

- Works offline (writes to local IndexedDB; reads from cached curriculum).
- Loads in < 3 s on a low-end Android over 3G.
- Passes basic WCAG AA contrast and keyboard navigation.
