from typing import Any

from pydantic import BaseModel, Field


class IssueTypeConfig(BaseModel):
    value: str
    label: str
    emergency: bool = False
    description: str = ""


class DomainConfigResponse(BaseModel):
    domain_name: str
    worker_label: str
    issue_types: list[IssueTypeConfig]
    skill_vocabulary: list[str]
    skill_labels: dict[str, str] = Field(default_factory=dict)
    status_transitions: dict[str, list[str]]
    required_metadata: dict[str, list[str]]
    required_skills_by_type: dict[str, list[str]]
    priorities: list[str]
    statuses: list[str]
    metadata_hint: dict[str, Any] = {}
