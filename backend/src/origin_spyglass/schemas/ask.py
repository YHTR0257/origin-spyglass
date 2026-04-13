from pydantic import BaseModel, Field


# This module defines the request and response schemas for the "ask"
# endpoint of the origin-spyglass application.
class AskRequest(BaseModel):
    id: str = Field(..., description="Unique identifier for the request")
    question: str = Field(..., description="The question to be asked")
    timestamp: str = Field(..., description="ISO 8601 formatted timestamp of the request")


class InterpretationResponse(BaseModel):
    id: str = Field(..., description="Unique identifier for the response")
    interpretation: str = Field(..., description="The interpreted question or command")
    timestamp: str = Field(..., description="ISO 8601 formatted timestamp of the response")


class SourceItem(BaseModel):
    title: str = Field(..., description="Title of the source document")
    content: str = Field(..., description="Content of the source document")
    link: str = Field(..., description="URL or reference link to the source document")


class AnswerResponse(BaseModel):
    session_id: str = Field(..., description="Session identifier for tracking")
    question: str = Field(..., description="The question text to be answered")
    answer: str = Field(..., description="The answer text provided")
    sources: list[SourceItem] = Field(..., description="List of source documents with context")
    timestamp: str | None = Field(None, description="Timestamp of the answer request")
