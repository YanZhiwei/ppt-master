# Pilot Run Report (Replica PPT Agent)

Date: 2026-05-06

## Scope

- Backend workflow smoke run via `debug_workflow.py`
- Deterministic conversion path: HTML -> SVG
- Export path: SVG -> editable PPTX

## Run Results

### Pilot 1

- Theme: `AI提效在制造业落地路径，8页，含封面目录数据总结`
- Session: `sess_29b5ce2ae2`
- Project: `proj_909f65ebbc`
- HTML/SVG count: `8/8`
- Export: `replica-ppt-agent/backend/debug_runs/proj_909f65ebbc/exports/proj_909f65ebbc_20260506_161401.pptx`
- Editability check: `PASS` (`Editable shape/text markers detected`)

### Pilot 2

- Theme: `教育数字化升级方案，10页，包含KPI和阶段路线图`
- Session: `sess_36768f4b57`
- Project: `proj_54109b546c`
- HTML/SVG count: `8/8`
- Export: `replica-ppt-agent/backend/debug_runs/proj_54109b546c/exports/proj_54109b546c_20260506_161437.pptx`
- Editability check: `PASS` (`Editable shape/text markers detected`)

## Acceptance Summary

- Workflow completion: PASS (planning/confirm/rendering/quality/export path exercised in pilot script)
- Deterministic conversion: PASS (existing regression test remains green)
- Export editability: PASS
- Retry behavior: deferred for dedicated API integration test

## Rollback

Follow `docs/acceptance-and-rollback.md`:
1. Disable replica export endpoint.
2. Route traffic to previous stable version.
3. Preserve failed artifacts for postmortem.
4. Re-enable only after staging regression passes.
