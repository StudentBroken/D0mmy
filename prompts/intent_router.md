# Intent Router Prompt

Classify the following user message into exactly one category.

Categories:
- "hardware" — the request is primarily about physical components, circuits, firmware, or embedded systems
- "software" — the request is primarily about software architecture, algorithms, APIs, or application logic
- "mixed" — the request requires both hardware and software work in roughly equal proportion

Output ONLY a JSON object:
{"intent": "<hardware|software|mixed>", "confidence": <0.0-1.0>}
