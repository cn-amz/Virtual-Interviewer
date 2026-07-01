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
