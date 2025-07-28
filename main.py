from fastapi import FastAPI
from app import models, routes
from app.database import engine
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()


@app.on_event("startup")   # only for local dev, not production
def on_startup():
    models.Base.metadata.create_all(bind=engine)


app.include_router(routes.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)