from fastapi import FastAPI
from app import models, routes
from app.database import engine
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

required_env_vars = ['API_KEY']
for var in required_env_vars:
    if not os.getenv(var):
        raise ValueError(f"Required environment variable {var} is not set")

app = FastAPI(
    title="Flight Crew Management API",
    description="Crew scheduling system for Luton Airport",
    version="1.0.0"
)


@app.get("/")
def read_root():
    return {"message": "Flight Crew Management API is running"}


@app.on_event("startup")   # only for local dev, not production
def on_startup():
    models.Base.metadata.create_all(bind=engine)


app.include_router(routes.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3001"), "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
