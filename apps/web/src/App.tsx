import { useEffect, useState } from "react";
import { getCurrentUser, type UserPublic } from "./api/client";
import { AbilityTreePage } from "./pages/AbilityTreePage";
import { DashboardPage } from "./pages/DashboardPage";
import { InterviewPage } from "./pages/InterviewPage";
import { LoginPage } from "./pages/LoginPage";
import { ReportPage } from "./pages/ReportPage";
import { SetupPage } from "./pages/SetupPage";

type Screen = "dashboard" | "setup" | "interview" | "report" | "abilityTree";

export function App() {
  const [screen, setScreen] = useState<Screen>("dashboard");
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
        <SetupPage onStart={() => setScreen("interview")} onBack={() => setScreen("dashboard")} />
      )}
      {screen === "interview" && <InterviewPage onFinish={() => setScreen("report")} />}
      {screen === "report" && <ReportPage onBack={() => setScreen("dashboard")} />}
      {screen === "abilityTree" && <AbilityTreePage onBack={() => setScreen("dashboard")} />}
    </main>
  );
}
