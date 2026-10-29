import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from conftest import cand, jd, sk
from skill_matching import config
from skill_matching.api import app
from skill_matching.cli import main
from skill_matching.llm_plan import enhance_plan
from skill_matching.recommendations import build_plan
from skill_matching.service import improvement_plan_raw, match_raw

client = TestClient(app, raise_server_exceptions=False)


def plan_for(c, j, tc=None, **kw):
    return improvement_plan_raw(c, j, tc, **kw)


def test_gain_and_projection_math():
    resp, plan = plan_for(cand(sk("Python")), jd(sk("Python"), sk("Go"), sk("Rust"), sk("SQL", "SQL")))
    assert resp.match_score == 25 and plan.current_score == 25
    assert [a.score_gain for a in plan.actions] == [25.0, 25.0, 25.0]
    assert [a.projected_score_after for a in plan.actions] == [50, 75, 100]
    assert plan.projected_score_if_all_closed == 100


def test_fully_matched_has_no_actions():
    _, plan = plan_for(cand(sk("Python")), jd(sk("Python")))
    assert plan.actions == [] and plan.projected_score_if_all_closed == 100


def test_partial_and_review_action_types():
    j = jd(sk("SQL", "SQL"), sk("AWS", "CLOUD"))
    _, plan = plan_for(cand(sk("Postgres", "SQL"), sk("Cloud", "CLOUD")), j)
    types = {a.skill_name: a.action_type for a in plan.actions}
    assert types == {"SQL": "strengthen_evidence", "AWS": "verify_and_add_evidence"}
    gains = {a.skill_name: a.score_gain for a in plan.actions}
    assert gains == {"AWS": 50.0, "SQL": 25.0}  # review earns 0, partial earns 0.5


def test_projection_matches_real_rescoring():
    c, j = cand(sk("Python")), jd(sk("Python"), sk("Go"), sk("SQL", "SQL"))
    _, plan = plan_for(c, j)
    # Actually add the first action's skill and rescore: it must equal the projection.
    top = plan.actions[0].skill_name
    new = match_raw(cand(sk("Python"), sk(top, plan.actions[0].category_code)), j)
    assert new.match_score == plan.actions[0].projected_score_after


def test_talent_check_critical_and_level_actions():
    tc = {"skillset_gap": [
        {"category_code": "SYSD", "required_level": 8, "candidate_level": 3},
        {"category_code": "COD", "required_level": 8, "candidate_level": 6}]}
    _, plan = plan_for(cand(sk("Python")), jd(sk("Python"), sk("System Design", "SYSD")), tc)
    by = {a.skill_name: a for a in plan.actions}
    assert by["System Design"].critical_gap and by["System Design"].action_type == "learn_skill"
    assert by["Python"].action_type == "raise_level" and by["Python"].level_needed == "6 -> 8"
    assert by["Python"].score_gain == 0.0
    assert plan.projected_score_if_all_closed == 100


def test_deterministic_plan():
    a = plan_for(cand(sk("Python")), jd(sk("Python"), sk("Go"), sk("Rust")))[1].model_dump()
    b = plan_for(cand(sk("Python")), jd(sk("Python"), sk("Go"), sk("Rust")))[1].model_dump()
    assert a == b


# ---- LLM layer, with a fake OpenAI-compatible client (no network) ----
class FakeClient:
    def __init__(self, content=None, exc=None):
        self.content, self.exc = content, exc
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self.last = None

    def _create(self, **kw):
        self.last = kw
        if self.exc:
            raise self.exc
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))])


def base_plan():
    return plan_for(cand(sk("Python")), jd(sk("Python"), sk("Go"), sk("Rust")))[1]


def test_llm_rewrites_steps_only():
    plan = base_plan()
    before = [(a.skill_name, a.score_gain, a.projected_score_after) for a in plan.actions]
    reply = json.dumps({"narrative": "Start with Go.", "actions": [
        {"skill_name": "Go", "steps": ["Tour of Go", "Build a CLI"]},
        {"skill_name": "Invented", "steps": ["x"]}]})
    out = enhance_plan(plan, "SWE", FakeClient(reply))
    assert out.source == "deterministic+llm" and out.narrative == "Start with Go."
    assert [(a.skill_name, a.score_gain, a.projected_score_after) for a in out.actions] == before
    assert next(a for a in out.actions if a.skill_name == "Go").steps == ["Tour of Go", "Build a CLI"]
    assert all(a.skill_name != "Invented" for a in out.actions)
    assert any("Ignored 1" in w for w in out.warnings)


def test_llm_prompt_leaks_no_personal_data():
    client = FakeClient(json.dumps({"narrative": "ok", "actions": []}))
    plan_for(cand(sk("Python", evidence="SECRET-EVIDENCE")), jd(sk("Python"), sk("Go")),
             use_llm=True, llm_client=client)
    sent = json.dumps(client.last["messages"])
    assert "SECRET-EVIDENCE" not in sent and "Test Candidate" not in sent


def test_llm_bad_json_falls_back():
    out = enhance_plan(base_plan(), None, FakeClient("not json"))
    assert out.source == "deterministic" and out.warnings and out.narrative is None


def test_llm_provider_error_falls_back():
    out = enhance_plan(base_plan(), None, FakeClient(exc=TimeoutError("slow")))
    assert out.source == "deterministic" and "failed" in out.warnings[0]


def test_llm_unconfigured_falls_back(monkeypatch):
    monkeypatch.setattr(config, "LLM_API_KEY", "")
    out = enhance_plan(base_plan())
    assert out.source == "deterministic" and "not configured" in out.warnings[0]


# ---- API / CLI ----
def test_api_plan(load):
    r = client.post("/api/v1/improvement-plan", json=load("sample_match_request.json"))
    assert r.status_code == 200
    d = r.json()
    assert d["source"] == "deterministic" and d["actions"] and d["projected_score_if_all_closed"] == 100


def test_api_plan_use_llm_without_config_still_200(load, monkeypatch):
    monkeypatch.setattr(config, "LLM_API_KEY", "")
    r = client.post("/api/v1/improvement-plan", json={**load("sample_match_request.json"), "use_llm": True})
    assert r.status_code == 200 and r.json()["warnings"]


def test_api_plan_validation():
    assert client.post("/api/v1/improvement-plan", json={"candidate": cand()}).status_code == 400
    r = client.post("/api/v1/improvement-plan", json={"candidate": cand(), "job_description": jd()})
    assert r.status_code == 422


def test_cli_plan(data_dir, capsys):
    assert main(["--candidate", str(data_dir / "sample_candidate.json"), "--jd", str(data_dir / "sample_jd.json"),
                 "--talent-check", str(data_dir / "sample_talent_check.json"), "--plan"]) == 0
    out = capsys.readouterr().out
    assert "IMPROVEMENT PLAN" in out and "[CRITICAL]" in out


def test_cli_plan_json(data_dir, capsys):
    main(["--candidate", str(data_dir / "sample_candidate.json"), "--jd", str(data_dir / "sample_jd.json"),
          "--plan", "--format", "json"])
    d = json.loads(capsys.readouterr().out)
    assert "match" in d and "improvement_plan" in d
