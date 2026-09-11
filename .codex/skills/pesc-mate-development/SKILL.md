---
name: pesc-mate-development
description: Implement, diagnose, review, and verify features in the PESC MATE repository. Use for changes to its React/Vite frontend, FastAPI/MongoDB backend, PECS card board, authentication, recommendations, sentence generation, TTS, caregiver notes, dashboard, tests, Docker setup, or project documentation.
---

# Develop PESC MATE

## Establish scope

- Read `README.md` and the relevant requirements in `docs/functional_requirements_specification.md`.
- Inspect `git status --short` before editing. Preserve unrelated user changes.
- Trace the existing implementation before choosing a design. Keep API behavior aligned with `docs/API_SPECIFICATION.md` when changing endpoints.
- Prefer a small end-to-end increment with clear acceptance behavior when a request is broad.

## Follow repository structure

- Put React UI and state in `frontend/src`, and HTTP client behavior in `frontend/src/services`.
- Put FastAPI routes and request/response schemas in `backend/app/api/router.py`.
- Put domain and persistence behavior in `backend/app/services`; keep routes thin.
- Preserve the 12-card board limit, ordered duplicate cards, role checks, and per-user data isolation.
- Treat MongoDB as the persistent store. Ensure optional AI behavior keeps the rule-based fallback usable.
- Keep Korean user-facing messages concrete, friendly, and actionable.

## Implement safely

1. Define the observable behavior and failure cases from the requirement.
2. Update the narrowest production files that own that behavior.
3. Add or update tests when backend logic or a regression-prone helper changes.
4. Keep optional browser capabilities and external services non-blocking; show a usable fallback or error state.
5. Review the diff for secrets, generated output, accidental broad formatting, and unrelated edits.

## Verify proportionally

- For frontend changes, run `npm run build` from `frontend`.
- For backend changes, run the relevant `python -m unittest <test_module> -v` from `backend`; run all `test_*.py` modules when shared authentication, database, or API behavior changes.
- Exercise pure helpers with a focused check when no test runner exists.
- Use `docker compose config` when changing `compose.yaml` or Docker service wiring.
- Report which checks passed and any checks not run.

## Prepare commits

- Follow `docs/COMMIT_CONVENTION.md`: use an English type, a Korean imperative subject of at most 50 characters, and no trailing punctuation.
- Before committing or pushing, inspect `git diff` and `git status --short` again.
- Do not commit runtime secrets, local environment files, virtual environments, dependency directories, or generated build output.
