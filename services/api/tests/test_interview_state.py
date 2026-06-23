from app.interview_state import InterviewState


def test_state_starts_with_warmup():
    state = InterviewState()

    assert state.stage == "warmup"
    assert state.next_action() == "ask_brief_self_introduction"


def test_state_advances_after_two_questions():
    state = InterviewState()

    state.advance_if_ready()
    assert state.stage == "warmup"
    state.advance_if_ready()

    assert state.stage == "resume_overview"


def test_low_scores_trigger_clarification():
    state = InterviewState(stage="fundamentals")

    state.record_answer_score(2.0)
    state.record_answer_score(2.5)

    assert state.next_action() == "ask_targeted_clarification"
