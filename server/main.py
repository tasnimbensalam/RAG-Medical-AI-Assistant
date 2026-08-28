from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from middelwares.exception_handlers import catch_exception_middleware


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
) 

# middleware exception handlers
app.middleware("http")(catch_exception_middleware)


#routers
#upload pdf
#asking query