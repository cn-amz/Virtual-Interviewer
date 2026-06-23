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
  });
  if (!response.ok) {
    throw new Error(`Failed to create report: ${response.status}`);
  }
  return response.json();
}
