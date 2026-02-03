from pydantic import BaseModel, Field

class ReportRequest(BaseModel):
    topic: str = Field(..., description="Topic for report generation")
    max_analysts: int = Field(3, description="Number of analyst personas to create")

class FeedbackRequest(BaseModel):
    thread_id: str
    feedback: str = ""

