from fastapi import APIRouter, HTTPException
from research_and_analyst.api.models.request_models import ReportRequest, FeedbackRequest
from research_and_analyst.api.services.report_service import ReportService
from research_and_analyst.logger import GLOBAL_LOGGER

router = APIRouter(prefix="/report", tags=["Autonomous Report"])
service = ReportService()
logger = GLOBAL_LOGGER.bind(module="ReportRoutes")

@router.post("/generate")
async def generate_report(request: ReportRequest):
    "Start autonomous report generation."
    try:
        response = service.start_report_generation(request.topic, request.max_analysts)
        return response
    except Exception as e:
        logger.exception("API error during report generation")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/feedback")
async def update_feedback(request: FeedbackRequest):
    """Provide feedback for human-feedback node."""
    try:
        return service.submit_feedback(request.thread_id, request.feedback)
    except Exception as e:
        logger.exception("API error during feedback update")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/status/{thread_id}")
async def get_status(thread_id: str):
    """Check report progress or retrieve file paths."""
    try:
        return service.get_report_status(thread_id)
    except Exception as e:
        logger.exception("API error during status check")
        raise HTTPException(status_code=500, detail=str(e))

