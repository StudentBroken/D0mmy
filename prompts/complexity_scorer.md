Score implementation complexity for an AI coding agent on a scale of 0–10.

## Scale
- 0–3: Trivial. CSS change, single-line fix, config value, rename.
- 4–6: Standard. New component, add endpoint, refactor one function, add field.
- 7: Moderate. Cross-file refactor, new agent/service, multi-step logic in one module.
- 8–9: Hard. System architecture change, complex algorithm, multi-module integration, security-critical logic.
- 10: Near-impossible. Multi-system migration, cryptographic primitives from scratch.

## Output
`{"score": int, "reason": "≤80 chars explaining the score"}`

Be conservative — only escalate to ≥8 when complexity genuinely warrants the heavier model.
