"""
LoreKeeper API main application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import api, claims, documents, entities, mentions, retrieval, worlds

app: FastAPI = FastAPI(
    title="LoreKeeper",
    description="Lore and knowledge management system for generated worlds",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api.router)

app.include_router(worlds.router)
app.include_router(entities.router)
app.include_router(documents.router)
app.include_router(mentions.router)
app.include_router(retrieval.router)
app.include_router(claims.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
