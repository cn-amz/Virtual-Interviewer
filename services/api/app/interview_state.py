from dataclasses import dataclass, field


STAGES = [
    "warmup",
    "resume_overview",
    "project_deep_dive",
    "fundamentals",
    "pressure_followup",
    "candidate_questions",
    "summary",
]


@dataclass
class InterviewState:
    stage: str = "warmup"
    questions_in_stage: int = 0
    low_score_count: int = 0
    history: list[str] = field(default_factory=list)

    def record_answer_score(self, score: float) -> None:
        if score < 3.0:
            self.low_score_count += 1
        self.history.append(f"{self.stage}:{score:.1f}")

    def next_action(self) -> str:
        if self.stage == "warmup":
            return "ask_brief_self_introduction"
        if self.low_score_count >= 2:
            return "ask_targeted_clarification"
        if self.stage == "project_deep_dive":
            return "ask_project_mechanism_followup"
        if self.stage == "summary":
            return "summarize_and_close"
        return "ask_next_stage_question"

    def advance_if_ready(self) -> None:
        self.questions_in_stage += 1
        if self.questions_in_stage < 2:
            return
        current_index = STAGES.index(self.stage)
        if current_index < len(STAGES) - 1:
            self.stage = STAGES[current_index + 1]
            self.questions_in_stage = 0
            self.low_score_count = 0
