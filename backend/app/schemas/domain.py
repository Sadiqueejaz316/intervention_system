from typing import Any

from pydantic import BaseModel


class DomainConfigResponse(BaseModel):
    domain_name: str
    worker_label: str
    issue_types: list[str]
    skill_vocabulary: list[str]
    status_transitions: dict[str, list[str]]
    required_metadata: dict[str, list[str]]
    required_skills_by_type: dict[str, list[str]]
    priorities: list[str]
    statuses: list[str]
    metadata_hint: dict[str, Any] = {}
