from pydantic import BaseModel, Field


class ProfileSummary(BaseModel):
    profile_id: str
    name: str
    skills: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)


class JobDescription(BaseModel):
    jd_id: str
    title: str
    content: str


class SessionProfile(BaseModel):
    profile: ProfileSummary
    job_description: JobDescription
    prompt: str
    qa_bank: str


class ResumeDocument(BaseModel):
    name: str
    format: str
    size: int


class JobDescriptionDocument(BaseModel):
    jd_id: str
    name: str
    title: str
    size: int
    analysis_ready: bool = False


class JobDescriptionTextRequest(BaseModel):
    title: str = ""
    content: str


class JobDescriptionAnalysis(BaseModel):
    jd_id: str
    title: str
    role_family: str
    role_direction: str
    focus_points: list[str] = Field(default_factory=list)
    question_strategy: list[str] = Field(default_factory=list)
    initial_prompt: str
    source_keywords: list[str] = Field(default_factory=list)
    research_sources: list[dict[str, str]] = Field(default_factory=list)
    analysis_mode: str
    analysis_error: str | None = None
    updated_at: str


class LoginRequest(BaseModel):
    username: str
    password: str


class UserPublic(BaseModel):
    user_id: str
    username: str
    display_name: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
