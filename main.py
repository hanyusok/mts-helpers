import os
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import HOST, PORT
from database.watcher import watch_db_changes
from routers import websockets, clinic, patients, queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("mts_helpers")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the Firebird DB watcher in the background
    watcher_task = asyncio.create_task(watch_db_changes())
    logger.info("Started Firebird DB real-time watcher task.")
    yield
    # Clean up the DB watcher on shutdown
    watcher_task.cancel()
    try:
        await watcher_task
    except asyncio.CancelledError:
        pass
    logger.info("Cleaned up background watcher.")

app = FastAPI(
    title="Kim Ki-joong Pediatrics Helpers (mts-helpers)",
    description="김기중 소아청소년과의원 모바일 간편접수, 실시간 대기열, 대기실 전광판 및 병원 정보 관리 서비스.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local integration & mobile clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Modular Routers
app.include_router(websockets.router, prefix="/ws")
app.include_router(clinic.router, prefix="/api")
app.include_router(patients.router, prefix="/api")
app.include_router(queue.router, prefix="/api")

# Serve single-page dashboard at root
@app.get("/")
def read_index():
    static_index = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "index.html")
    if not os.path.exists(static_index):
        raise HTTPException(status_code=404, detail="static/index.html not found.")
    return FileResponse(static_index)

@app.get("/admin")
def read_admin():
    admin_index = os.path.join(os.path.dirname(os.path.abspath(__file__)), "admin-ui", "index.html")
    if not os.path.exists(admin_index):
        raise HTTPException(status_code=404, detail="admin-ui/index.html not found.")
    return FileResponse(admin_index)

@app.get("/config.js")
def get_backend_config_js():
    """Serves backend port configuration dynamically to frontend apps."""
    return Response(
        content=f"window.GATEWAY_PORT = {PORT};",
        media_type="application/javascript"
    )

# Mount static folders
base_dir = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(base_dir, "static")), name="static")
app.mount("/admin", StaticFiles(directory=os.path.join(base_dir, "admin-ui"), html=True), name="admin_ui")
app.mount("/quick", StaticFiles(directory=os.path.join(base_dir, "quick-ui"), html=True), name="quick_ui")
app.mount("/quicklist", StaticFiles(directory=os.path.join(base_dir, "quicklist-ui"), html=True), name="quicklist_ui")
app.mount("/signage", StaticFiles(directory=os.path.join(base_dir, "signage-ui"), html=True), name="signage_ui")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting Kim Ki-joong Pediatrics Helpers server on http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info", proxy_headers=True, forwarded_allow_ips="*")
