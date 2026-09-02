from pydantic import BaseModel, ConfigDict


class SubjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    enabled: bool
