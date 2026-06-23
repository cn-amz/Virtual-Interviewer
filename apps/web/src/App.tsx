import { useState } from "react";
import { InterviewPage } from "./pages/InterviewPage";
import { ReportPage } from "./pages/ReportPage";
import { SetupPage } from "./pages/SetupPage";

type Screen = "setup" | "interview" | "report";

export function App() {
  const [screen, setScreen] = useState<Screen>("setup");

  return (
    <main className="app-shell">
      {screen === "setup" && <SetupPage onStart={() => setScreen("interview")} />}
      {screen === "interview" && <InterviewPage onFinish={() => setScreen("report")} />}
      {screen === "report" && <ReportPage />}
    </main>
  );
}
