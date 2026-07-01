export const API_BASE = "http://localhost:8000";

export type ProfileList = {
  profiles: string[];
};

export type MockReportResponse = {
  interview_id: string;
  report: {
    summary: string;
    score: {
      average: number;
    };
  };
  ability_tree: {
    skills: string[];
    target_skills: string[];
  };
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

export async function listProfiles(): Promise<ProfileList> {
  const response = await fetch(`${API_BASE}/api/profiles`);
  if (!response.ok) {
    throw new Error(`Failed to load profiles: ${response.status}`);
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
