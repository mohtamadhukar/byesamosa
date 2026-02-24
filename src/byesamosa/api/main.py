from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from byesamosa.api.routers import baselines, dashboard, data_status, insights, pipeline, trends, workouts

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
app.include_router(pipeline.router, prefix="/api")
app.include_router(data_status.router, prefix="/api")
