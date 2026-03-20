from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import dispose_engine, initialize_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    await initialize_database()
    yield
    await dispose_engine()


app = FastAPI(lifespan=lifespan)



@app.get("/")
async def root():
    return {"message": "Hello World"}
