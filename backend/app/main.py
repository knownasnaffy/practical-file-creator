from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.routers import placeholders, practical_files, tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema
    init_db()
    yield


app = FastAPI(
    title="Practical File Generator API",
    description="Backend API for automating practical file generation from markdown to PDF.",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(practical_files.router)
app.include_router(tasks.router)
app.include_router(placeholders.router)


@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok", "app": "Practical File Generator"}
