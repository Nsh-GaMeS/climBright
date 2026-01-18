import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import models
from database import engine
from routers import classifier

app = FastAPI()

# Allow the browser frontend to call this API (different port => different origin).
origins_env = os.environ.get("FRONTEND_ORIGINS")
if origins_env:
	origins = [o.strip() for o in origins_env.split(",") if o.strip()]
else:
	origins = [
		"http://localhost:6769",
		"http://127.0.0.1:6769",
		"http://localhost:3000",
		"http://127.0.0.1:3000",
	]

app.add_middleware(
	CORSMiddleware,
	allow_origins=origins,
	allow_credentials=False,
	allow_methods=["*"] ,
	allow_headers=["*"],
)

models.Base.metadata.create_all(bind=engine)

#adding API routers 
app.include_router(classifier.router)