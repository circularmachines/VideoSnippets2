"""Schema definitions for video snippets."""

from typing import List
from pydantic import BaseModel, Field

class Snippet(BaseModel):
    """A snippet represents a thematic group of video segments."""
    title: str = Field(
        description="A concise title describing the snippet content"
    )
    description: str = Field(
        description="A detailed description of what happens in this snippet"
    )
    segments: List[int] = Field(
        description="List of segment indices that belong to this snippet"
    )

class SnippetsResponse(BaseModel):
    """Response format for snippet generation."""
    snippets: List[Snippet] = Field(
        description="List of snippets generated from the video content"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "snippets": [
                        {
                            "title": "Introduction",
                            "description": "The presenter introduces the topic",
                            "segments": [0, 1, 2]
                        },
                        {
                            "title": "Main Discussion",
                            "description": "Detailed explanation of key points",
                            "segments": [3, 4, 5]
                        }
                    ]
                }
            ]
        }
    }
