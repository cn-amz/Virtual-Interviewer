from pydantic import BaseModel


class AnswerScore(BaseModel):
    relevance: float
    technical_depth: float
    evidence_quality: float
    structure: float
    communication: float
    rationale: str

    @property
    def average(self) -> float:
        values = [
            self.relevance,
            self.technical_depth,
            self.evidence_quality,
            self.structure,
            self.communication,
        ]
        return round(sum(values) / len(values), 2)


def score_answer(question: str, answer: str) -> AnswerScore:
    answer_len = len(answer.strip())
    has_numbers = any(ch.isdigit() for ch in answer)
    has_mechanism = any(word in answer for word in ["因为", "通过", "引入", "优化", "实现"])
    depth = 4.0 if has_mechanism else 2.5
    evidence = 4.0 if has_numbers else 3.0
    relevance = 4.0 if answer_len > 20 and question else 2.0
    structure = 4.0 if "。" in answer or "；" in answer else 3.0
    communication = 4.0 if answer_len <= 500 else 3.0
    return AnswerScore(
        relevance=relevance,
        technical_depth=depth,
        evidence_quality=evidence,
        structure=structure,
        communication=communication,
        rationale="Deterministic MVP score based on length, mechanism words, and evidence markers.",
    )
