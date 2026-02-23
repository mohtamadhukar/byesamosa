from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from byesamosa.api.routers import baselines, dashboard, insights, trends, workouts

app = FastAPI(title="ByeSamosa API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router, prefix="/api")
app.include_router(trends.router, prefix="/api")
app.include_router(baselines.router, prefix="/api")
app.include_router(workouts.router, prefix="/api")
app.include_router(insights.router, prefix="/api")
