from fastapi import FastAPI, Depends
import models
from database import engine
from routers import classifier

app = FastAPI()

models.Base.metadata.create_all(bind=engine)

#adding API routers 
app.include_router(classifier.router)