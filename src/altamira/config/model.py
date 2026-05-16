from typing import Literal

from pydantic import BaseModel


class ProjectConfig(BaseModel):
    name: str
    version: str = "0.1.0"
    subject_type: Literal["person", "event"] = "person"
    subject_name: str = ""
    language: str = "en"
    description: str = ""
    cover: str = ""
    require_source_notes: bool = False
    provider: str = ""
    model: str = ""
