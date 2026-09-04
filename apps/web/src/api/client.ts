export const API_BASE = "http://localhost:8000";

export type ProfileList = {
  profiles: string[];
};

export type ProviderStatus = {
  provider: "bailian" | "minicpm";
  state: "offline" | "loading" | "queued" | "idle" | "busy" | "error";
  detail: string;
  queue_length: number;
};

export type ResumeDocument = {
  name: string;
  format: string;
  size: number;
};

export type JobDescriptionDocument = {
  jd_id: string;
  name: string;
  title: string;
  size: number;
  analysis_ready?: boolean;
};

export type JobDescriptionAnalysis = {
  jd_id: string;
  title: string;
  role_family: string;
  role_direction: string;
  focus_points: string[];
  question_strategy: string[];
  initial_prompt: string;
  source_keywords: string[];
  research_sources: Array<{ title: string; url: string; note: string }>;
  analysis_mode: string;
  analysis_error?: string;
  updated_at: string;
};

export type MockReportResponse = {
  interview_id: string;
  created_at?: string;
  report: {
    summary: string;
    strengths?: string[];
    target_gaps?: string[];
    next_practice_plan?: string[];
    transcript?: Array<{ speaker: string; text: string }>;
    analysis_mode?: string;
    score: {
      average: number;
    };
  };
  ability_tree: {
    skills: string[];
    target_skills: string[];
    evidence?: string[];
    edges?: Array<{ from: string; to: string; type: string }>;
  };
};

export type AbilityTree = {
  user_id: string;
  skills: string[];
  projects: string[];
  evidence: string[];
  target_skills: string[];
  edges: Array<{ from: string; to: string; type: string }>;
  evidence_details?: AbilityEvidence[];
  question_groups?: AbilityQuestionGroup[];
  type_branches?: AbilityTypeBranch[];
  organization_mode?: string;
  organization_error?: string;
  markdown_path?: string;
  obsidian_uri?: string;
  updated_at: string;
};

export type KnowledgePoint = {
  title: string;
  summary?: string;
  obsidian_ref?: string;
};

export type AbilityEvidence = {
  evidence_id: string;
  interview_id: string;
  skill: string;
  question: string;
  answer: string;
  knowledge_points: KnowledgePoint[];
};

export type AbilityQuestionGroup = {
  question_id: string;
  canonical_question: string;
  types: string[];
  skills: string[];
  evidence_ids: string[];
  knowledge_points: KnowledgePoint[];
};

export type AbilityTypeBranch = {
  type: string;
  question_ids: string[];
};

export type UserPublic = {
  user_id: string;
  username: string;
  display_name: string;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  user: UserPublic;
};

function getStoredToken(): string | null {
  return localStorage.getItem("auth_token");
}

export function getAuthHeaders(): Record<string, string> {
  const token = getStoredToken();
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

export async function getProviderStatus(
  provider: ProviderStatus["provider"]
): Promise<ProviderStatus> {
  const response = await fetch(`${API_BASE}/api/interviews/providers/${provider}/status`);
  if (!response.ok) {
    throw new Error(`Failed to load provider status: ${response.status}`);
  }
  return response.json();
}

export async function listProfiles(): Promise<ProfileList> {
  const response = await fetch(`${API_BASE}/api/profiles`);
  if (!response.ok) {
    throw new Error(`Failed to load profiles: ${response.status}`);
  }
  return response.json();
}

export async function listResumes(profileId: string): Promise<ResumeDocument[]> {
  const response = await fetch(
    `${API_BASE}/api/profiles/${encodeURIComponent(profileId)}/resumes`
  );
  if (!response.ok) {
    throw new Error(`Failed to load resumes: ${response.status}`);
  }
  return response.json();
}

export function resumeUrl(profileId: string, resumeName: string): string {
  return `${API_BASE}/api/profiles/${encodeURIComponent(profileId)}/resumes/${encodeURIComponent(resumeName)}`;
}

export async function listJobDescriptions(): Promise<JobDescriptionDocument[]> {
  const response = await fetch(`${API_BASE}/api/job-descriptions`);
  if (!response.ok) {
    throw new Error(`Failed to load job descriptions: ${response.status}`);
  }
  return response.json();
}

export function jobDescriptionUrl(jdId: string): string {
  return `${API_BASE}/api/job-descriptions/${encodeURIComponent(jdId)}/file`;
}

export async function uploadResume(profileId: string, file: File): Promise<ResumeDocument> {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch(
    `${API_BASE}/api/profiles/${encodeURIComponent(profileId)}/resumes`,
    { method: "POST", headers: getAuthHeaders(), body }
  );
  if (!response.ok) {
    throw new Error(`Failed to upload resume: ${response.status}`);
  }
  return response.json();
}

export async function uploadJobDescription(file: File): Promise<JobDescriptionDocument> {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch(`${API_BASE}/api/job-descriptions`, {
    method: "POST",
    headers: getAuthHeaders(),
    body,
  });
  if (!response.ok) {
    throw new Error(`Failed to upload job description: ${response.status}`);
  }
  return response.json();
}

export async function createJobDescriptionFromText(title: string, content: string): Promise<JobDescriptionDocument> {
  const response = await fetch(`${API_BASE}/api/job-descriptions/text`, {
    method: "POST",
    headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify({ title, content }),
  });
  if (!response.ok) {
    throw new Error(`Failed to save job description: ${response.status}`);
  }
  return response.json();
}

export async function analyzeJobDescription(jdId: string): Promise<JobDescriptionAnalysis> {
  const response = await fetch(
    `${API_BASE}/api/job-descriptions/${encodeURIComponent(jdId)}/analyze`,
    { method: "POST", headers: getAuthHeaders() }
  );
  if (!response.ok) {
    throw new Error(`Failed to analyze job description: ${response.status}`);
  }
  return response.json();
}

export async function listInterviewHistory(): Promise<MockReportResponse[]> {
  const response = await fetch(`${API_BASE}/api/interviews/history`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error(`Failed to load interview history: ${response.status}`);
  }
  return response.json();
}

export async function getInterviewReport(interviewId: string): Promise<MockReportResponse> {
  const response = await fetch(`${API_BASE}/api/interviews/${encodeURIComponent(interviewId)}`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error(`Failed to load interview report: ${response.status}`);
  }
  return response.json();
}

export async function analyzeInterview(interviewId: string): Promise<MockReportResponse> {
  for (let attempt = 0; attempt < 4; attempt += 1) {
    const response = await fetch(
      `${API_BASE}/api/interviews/${encodeURIComponent(interviewId)}/analyze`,
      { method: "POST", headers: getAuthHeaders() }
    );
    if (response.ok) return response.json();
    if (response.status !== 404 && response.status !== 422) {
      throw new Error(`Failed to analyze interview: ${response.status}`);
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("Interview transcript is not ready yet.");
}

export async function getAbilityTree(userId: string): Promise<AbilityTree> {
  const response = await fetch(
    `${API_BASE}/api/ability-trees/${encodeURIComponent(userId)}`,
    { headers: getAuthHeaders() }
  );
  if (!response.ok) {
    throw new Error(`Failed to load ability tree: ${response.status}`);
  }
  return response.json();
}

export function abilityTreeMarkdownUrl(userId: string): string {
  return `${API_BASE}/api/ability-trees/${encodeURIComponent(userId)}/markdown`;
}

export async function organizeAbilityTree(userId: string): Promise<AbilityTree> {
  const response = await fetch(
    `${API_BASE}/api/ability-trees/${encodeURIComponent(userId)}/organize`,
    { method: "POST", headers: getAuthHeaders() }
  );
  if (!response.ok) {
    throw new Error(`Failed to organize ability tree: ${response.status}`);
  }
  return response.json();
}

export async function createMockReport(): Promise<MockReportResponse> {
  const response = await fetch(`${API_BASE}/api/interviews/mock-report`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error(`Failed to create report: ${response.status}`);
  }
  return response.json();
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    throw new Error("登录失败：用户名或密码错误");
  }
  const data: LoginResponse = await response.json();
  localStorage.setItem("auth_token", data.access_token);
  return data;
}

export async function getCurrentUser(): Promise<UserPublic> {
  const response = await fetch(`${API_BASE}/api/auth/me`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    localStorage.removeItem("auth_token");
    throw new Error("Session expired");
  }
  return response.json();
}

export async function logout(): Promise<void> {
  const token = getStoredToken();
  if (token) {
    await fetch(`${API_BASE}/api/auth/logout`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
  }
  localStorage.removeItem("auth_token");
}
