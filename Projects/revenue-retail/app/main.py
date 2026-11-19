from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
# from .database import MONTHS, REGIONS
from .analytics import trend
from .workflow import analyze

ROOT=Path(__file__).resolve().parent.parent


app = FastAPI()
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')

class QueryRequest(BaseModel):
    question: str=Field(min_length=5,max_length=500)
    region: str='West'
    month: str='2026-10'

@app.get('/')
def home(): return FileResponse(ROOT/'static'/'index.html')