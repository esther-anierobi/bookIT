from fastapi import FastAPI
from app.database import Base, engine
from fastapi.middleware.cors import CORSMiddleware
from app.middleware import add_request_id_and_process_time
from app.routes.user_route import user_router
from app.routes.service_route import service_router
from app.routes.booking_route import booking_router
from app.routes.review_route import review_router


Base.metadata.create_all(bind=engine)
app = FastAPI(
    title="BookIT API",
    version="1.0.0",
    description="API for a simple bookings platform called BookIT, allowing users to book services, leave reviews, and manage their accounts.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(add_request_id_and_process_time)


@app.get("/", status_code=200)
async def home():
    return {"message": "Welcome to BookIT REST API Project"}


app.include_router(user_router, prefix="/api", tags=["Users"])
app.include_router(service_router, prefix="/api", tags=["Services"])
app.include_router(booking_router, prefix="/api", tags=["Bookings"])
app.include_router(review_router, prefix="/api", tags=["Reviews"])
