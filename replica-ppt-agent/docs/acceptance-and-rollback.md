# Pilot Acceptance and Rollback

## Pilot Deck Acceptance Criteria

1. Workflow completion
- Session can pass planning -> rendering -> quality_check -> exporting -> done.

2. Deterministic conversion
- Same HTML input produces byte-identical SVG output in repeated runs.

3. Export editability
- Exported PPTX contains editable text/shape markers (`<p:sp>` or `<a:t>` in slide XML).

4. Provider routing
- Text generation path resolves to Azure OpenAI.
- Image generation path can switch between Gemini and OpenAI (`gpt-image-2`) by config.

5. Retry behavior
- Failed page can be retried by page scope without restarting all completed pages.

## Rollback Procedure

1. Disable replica export endpoint in deployment config.
2. Route traffic back to previous stable release.
3. Preserve failed-session artifacts for postmortem.
4. Re-enable replica only after regression checks pass in staging.

