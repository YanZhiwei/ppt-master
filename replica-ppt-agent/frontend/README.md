# Replica PPT Agent Frontend

## Quick Start

```bash
pnpm install
pnpm dev
```

## Environment Isolation

- Use a frontend-local Node environment and `pnpm` only.
- Do not reuse backend Python environment for frontend tooling.
- Do not use `npm` for this replica frontend.

Routes:
- `/explore` template explore shell
- `/workspace` generation workspace shell

Notes:
- SSE wiring is implemented in `src/lib/events.ts`.
- Current UI is a functional shell intended for API integration and iterative styling.
