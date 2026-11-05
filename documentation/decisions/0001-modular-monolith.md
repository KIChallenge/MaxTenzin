# 0001 Modular monolith instead of microservices
**Context:** 24 h, solo, local demo. **Decision:** one FastAPI app, one router + contract module + store collection per service.
**Consequence:** service boundaries are real and testable; independent deployment is a later roadmap step.
