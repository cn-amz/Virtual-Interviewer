import { useEffect, useState } from "react";
import { getCurrentUser, type UserPublic } from "./api/client";
import { AbilityTreePage } from "./pages/AbilityTreePage";
import { DashboardPage } from "./pages/DashboardPage";
import { HistoryPage } from "./pages/HistoryPage";
import { InterviewPage } from "./pages/InterviewPage";
import { LoginPage } from "./pages/LoginPage";
import { ManageDataPage } from "./pages/ManageDataPage";
import { ReportPage } from "./pages/ReportPage";
import { SetupPage } from "./pages/SetupPage";
import type { InterviewSessionSelection } from "./realtime/useInterviewSession";

type Screen = "dashboard" | "setup" | "interview" | "report" | "abilityTree" | "history" | "manage";

export function App() {
  const [screen, setScreen] = useState<Screen>("dashboard");
  const [selectedInterviewId, setSelectedInterviewId] = useState<string>();
  const [sessionSelection, setSessionSelection] = useState<InterviewSessionSelection>();
  const [user, setUser] = useState<UserPublic | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("auth_token");
    if (!token) {
      setChecking(false);
      return;
    }
    getCurrentUser()
      .then((currentUser) => {
        setUser(currentUser);
        setScreen("dashboard");
      })
      .catch(() => {
        setUser(null);
      })
      .finally(() => setChecking(false));
  }, []);

  function handleLogin(currentUser: UserPublic) {
    setUser(currentUser);
    setScreen("dashboard");
  }

  function handleLogout() {
    setUser(null);
  }

  if (checking) {
    return (
      <main className="app-shell">
        <section className="panel">
          <p>正在加载...</p>
        </section>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="app-shell">
        <LoginPage onLogin={handleLogin} />
      </main>
    );
  }

  return (
    <main className="app-shell">
      {screen === "dashboard" && (
        <DashboardPage user={user} onNavigate={setScreen} onLogout={handleLogout} />
      )}
      {screen === "setup" && (
        <SetupPage
          initialProfileId={user.display_name}
          onStart={(selection) => {
            setSessionSelection(selection);
            setScreen("interview");
          }}
          onBack={() => setScreen("dashboard")}
        />
      )}
      {screen === "interview" && sessionSelection && (
        <InterviewPage
          selection={sessionSelection}
          onFinish={(interviewId) => {
            setSelectedInterviewId(interviewId);
            setScreen("report");
          }}
          onCancel={() => setScreen("setup")}
        />
      )}
      {screen === "report" && (
        <ReportPage
          interviewId={selectedInterviewId}
          onBack={() => {
            setSelectedInterviewId(undefined);
            setScreen("dashboard");
          }}
        />
      )}
      {screen === "abilityTree" && (
        <AbilityTreePage
          userId={user.user_id}
          onBack={() => setScreen("dashboard")}
          onOpenReport={(interviewId) => {
            setSelectedInterviewId(interviewId);
            setScreen("report");
          }}
        />
      )}
      {screen === "history" && (
        <HistoryPage
          onBack={() => setScreen("dashboard")}
          onOpenReport={(interviewId) => {
            setSelectedInterviewId(interviewId);
            setScreen("report");
          }}
        />
      )}
      {screen === "manage" && <ManageDataPage onBack={() => setScreen("dashboard")} />}
    </main>
  );
}
