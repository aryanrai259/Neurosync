# Archive Recommendations Plan

## Files that should remain at Repo Root
- `README.md` (The singular source of truth for visitors).
- `company_brain_final_master_architecture.md` (Despite drift, this is the foundational "whitepaper" for the system and should remain visible, with its ADR disclaimer).
- `Synthetic_Data_and_Demo_Design.md` (Contains the AcmeCloud persona and expected data shaping, which is still highly relevant for upcoming UI/Demo phases).

## Files that should move to `docs/archive/`
- `Build_Manual.md` (Replaced by modern Phase tracking; references "Weeks" and outdated tech).
- `Implementation_Plan.md` (A massive 100KB file that dictates a build order we have already completed/deviated from).
- `Technical_Design_Specification_TDS.md` (Schemas are outdated, QueryRouter logic is abandoned).
- `drift_audit_report.md` (A point-in-time output that is no longer active).

## Duplicated Files
- `Build_Manual.md` vs `Implementation_Plan.md` (Both served as step-by-step guides for the identical early codebase build, creating an unmaintainable dual-state).

## Files Superseded by ADR-0001
- `Technical_Design_Specification_TDS.md` (The vector storage sections and LLM routing sections are directly overridden by ADR-0001).
