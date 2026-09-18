"""The NLU backend resolver: rule-based by default, LLM opt-in with fallback."""
from app.dialogue import llm_nlu, nlu_router


def test_defaults_to_rule_based(monkeypatch):
    monkeypatch.delenv("NLU_BACKEND", raising=False)
    assert nlu_router.detect_intent("book a table for two") == "book_table"
    assert nlu_router.extract_slots("for 4 at 7pm")["party_size"] == "4"


def test_llm_backend_falls_back_when_model_unavailable(monkeypatch):
    # select the LLM backend but with no Ollama running → per-call fallback to rules
    monkeypatch.setenv("NLU_BACKEND", "llm")
    monkeypatch.setattr(llm_nlu, "_query", lambda text: (_ for _ in ()).throw(RuntimeError("no model")))
    assert nlu_router.detect_intent("cancel my reservation") == "cancel"
    assert nlu_router.extract_slots("book VB-0007")["ref"] == "VB-0007"


def test_llm_backend_used_when_model_responds(monkeypatch):
    monkeypatch.setenv("NLU_BACKEND", "llm")
    monkeypatch.setattr(llm_nlu, "_query",
                        lambda text: {"intent": "book_table",
                                      "slots": {"party_size": 9, "time": "8 pm"}})
    assert nlu_router.detect_intent("anything") == "book_table"
    slots = nlu_router.extract_slots("anything")
    assert slots == {"party_size": "9", "time": "8 pm"}   # coerced to strings
