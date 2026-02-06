import os
from pathlib import Path
from dotenv import load_dotenv

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[2]  # .../automated-research-report-generation
PKG_ROOT  = HERE.parents[1]  # .../research_and_analyst

candidates = [
    REPO_ROOT / ".env",
    PKG_ROOT / ".env",
]

loaded = False
for p in candidates:
    if p.exists():
        load_dotenv(p, override=True)
        print(f"Loaded .env from: {p}")
        loaded = True
        break

if not loaded:
    print("WARNING: No .env found in repo root or research_and_analyst/")

print("OPENAI_API_KEY visible in main.py?", bool(os.getenv("OPENAI_API_KEY")))
print("TAVILY_API_KEY visible in main.py?", bool(os.getenv("TAVILY_API_KEY")))

from uuid import uuid4

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session


from research_and_analyst.database.db_config import (
    SessionLocal,
    User,
    hash_password,
    verify_password
)

from research_and_analyst.utils.model_loader import ModelLoader
from research_and_analyst.workflows.report_generator_workflow import AutonomousReportGenerator

# Load .env that is stored inside research_and_analyst/
# env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
# env_path = os.path.abspath(env_path)

app = FastAPI(title="Autonomous Report Generator UI")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="research_and_analyst/api/templates")

def basename_filter(path: str):
    return os.path.basename(path)

templates.env.filters["basename"] = basename_filter

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def show_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

SESSIONS = {}

# WORKFLOWS = {}  # session_id -> {"graph": graph, "generator": generator, "thread": thread}
THREADS = {}  # session_id -> thread_id

@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    db = next(get_db())
    user = db.query(User).filter(User.username == username).first()

    if user and verify_password(password, user.password):
        session_id = f"{username}_session"
        SESSIONS[session_id] = username
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(key="session_id", value=session_id)
        return response
    
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Invalid username or password"},
    )

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id not in SESSIONS:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "user": SESSIONS[session_id]})

@app.post("/generate_report", response_class=HTMLResponse)
async def generate_report(request: Request, topic: str = Form(...)):
    session_id = request.cookies.get("session_id")
    if session_id not in SESSIONS:
        return RedirectResponse(url="/")

    llm = ModelLoader().load_llm()
    generator = AutonomousReportGenerator(llm)
    graph = generator.build_graph()

    thread_id = f"{session_id}-{uuid4().hex}"
    thread = {"configurable": {"thread_id": thread_id}}

    THREADS[session_id] = thread_id

    for _ in graph.stream({"topic": topic, "max_analysts": 3}, thread, stream_mode="values"):
        pass

    state = graph.get_state(thread)
    analysts = state.values.get("analysts") if state and state.values else None
    if not analysts:
        generator.logger.error("No analysts were stored in state after create_analyst; cannot proceed.")
        return templates.TemplateResponse(
            "report_progress.html",
            {
            "request": request, 
            "topic": topic, 
            "feedback": "", 
            "error": "Failed to create analysts. Please retry."
            },
            )

    # persist for /submit_feedback
    # WORKFLOWS[session_id] = {"graph": graph, "generator": generator, "thread": thread, "topic": topic}

    feedback = ""
    return templates.TemplateResponse(
        "report_progress.html",
        {"request": request, "topic": topic, "feedback": feedback},
    )

@app.post("/submit_feedback", response_class=HTMLResponse)
async def submit_feedback(request: Request, topic: str = Form(...), feedback: str = Form(...)):
    session_id = request.cookies.get("session_id")
    if session_id not in SESSIONS:
        return RedirectResponse(url="/")

    # wf = WORKFLOWS.get(session_id)
    # if not wf:
    #     return templates.TemplateResponse(
    #         "report_progress.html",
    #         {"request": request, "topic": topic, "feedback": feedback, "error": "No active workflow. Please generate report again."},
    #     )

    # graph = wf["graph"]
    # generator = wf["generator"]
    # thread = wf["thread"]

    # Option B-1: retrieve the thread_id created in /generate_report
    thread_id = THREADS.get(session_id)
    if not thread_id:
        return templates.TemplateResponse(
            "report_progress.html",
            {
                "request": request,
                "topic": topic,
                "feedback": feedback,
                "error": "No active workflow. Please generate report again."
            },
        )

    # Rebuild objects per request (state is NOT in memory; it is in SQLite)
    llm = ModelLoader().load_llm()
    generator = AutonomousReportGenerator(llm)
    graph = generator.build_graph()

    thread = {"configurable": {"thread_id": thread_id}}

   # Update feedback at the interrupt node
    graph.update_state(
        thread,
        {"human_analyst_feedback": feedback, "topic": topic},
        as_node="human_feedback",
        )

    # Resume graph execution
    for _ in graph.stream(None, thread, stream_mode="values"):
        pass

    # Read final report from state
    final_state = graph.get_state(thread)
    final_report = final_state.values.get("final_report")
        
    if not final_report:
        generator.logger.warning("Final report content is None — generating fallback report.")
        final_report = f"Report on '{topic}' was generated successfully, but no text output was returned.\nPlease re-run the workflow or verify analyst responses."

    doc_path = generator.save_report(final_report, topic, "docx")
    pdf_path = generator.save_report(final_report, topic, "pdf")

    # WORKFLOWS.pop(session_id, None)
    # Optional cleanup: end the workflow for this session
    THREADS.pop(session_id, None)

    return templates.TemplateResponse(
        "report_progress.html",
        {
            "request": request,
            "topic": topic,
            "feedback": feedback,
            "doc_path": doc_path,
            "pdf_path": pdf_path,
        },
    )

@app.get("/signup", response_class=HTMLResponse)
async def show_signup(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup", response_class=HTMLResponse)
async def signup(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    db = next(get_db())
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "error": "Username already exists"},
        )

    hashed_pw = hash_password(password)
    new_user = User(username=username, password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return RedirectResponse(url="/", status_code=302)

@app.get("/download/{file_name}", response_class=FileResponse)
async def download_report(file_name: str):
    report_dir = os.path.join(os.getcwd(), "generated_report")

    for root, dirs, files in os.walk(report_dir):
        if file_name in files:
            return FileResponse(
                path=os.path.join(root, file_name),
                filename=file_name,
                media_type="application/octet-stream"
            )
    return {"error": f"File {file_name} not found"}

