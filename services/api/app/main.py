"""SV KI-Lotse API — deterministic services + AI top layer. OpenAPI at /docs."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent.router import router as agent
from app.core.audit import AuditMiddleware
from app.core.config import get_settings
from app.services.appointments.router import router as appointments
from app.services.audit.router import router as audit
from app.services.benefits.router import router as benefits
from app.services.cases.router import router as cases
from app.services.directory.router import router as directory
from app.services.documents.router import router as documents
from app.services.forms.router import router as forms
from app.services.identity.router import router as identity
from app.services.legal.router import router as legal
from app.services.medications.router import router as medications
from app.services.notifications.router import router as notifications
from app.services.prevention.router import router as prevention
from app.services.situation.router import router as situation
from app.services.values.router import router as values

app = FastAPI(
    title="SV KI-Lotse API",
    version="0.1.0",
    description="Deterministische, quellenbelegte Services der Sozialversicherung – die KI ist ein Top Layer ohne Sonderrechte.",
)
app.add_middleware(AuditMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

for r in (identity, situation, documents, benefits, prevention, forms, cases, appointments, notifications, directory, medications, legal, values, audit, agent):
    app.include_router(r)


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok", "llm": "live" if get_settings().llm_live else "fake"}
