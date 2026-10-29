import json

from skill_matching.cli import main


def args(data_dir, c="sample_candidate.json", j="sample_jd.json", *extra):
    return ["--candidate", str(data_dir / c), "--jd", str(data_dir / j), *extra]


def test_text_mode(data_dir, capsys):
    assert main(args(data_dir)) == 0
    out = capsys.readouterr().out
    assert "MATCH SCORE" in out and "MISSING" in out and "e@" not in out


def test_json_mode(data_dir, capsys):
    assert main(args(data_dir, "sample_candidate_data.json", "sample_jd_data_role.json", "--format", "json")) == 0
    body = json.loads(capsys.readouterr().out)
    assert {"jd_source_file", "match_score", "matched_skills", "missing_skills"} <= body.keys()


def test_scores_differ_between_combinations(data_dir, capsys):
    scores = []
    for c, j in [("sample_candidate.json", "sample_jd.json"), ("sample_candidate_data.json", "sample_jd.json")]:
        main(args(data_dir, c, j, "--format", "json"))
        scores.append(json.loads(capsys.readouterr().out)["match_score"])
    assert scores[0] != scores[1]


def test_missing_file(data_dir, capsys):
    assert main(["--candidate", "nope.json", "--jd", str(data_dir / "sample_jd.json")]) == 2
    assert "not found" in capsys.readouterr().err


def test_bad_json(tmp_path, data_dir, capsys):
    p = tmp_path / "bad.json"
    p.write_text("{oops")
    assert main(["--candidate", str(p), "--jd", str(data_dir / "sample_jd.json")]) == 2
    assert "not valid JSON" in capsys.readouterr().err


def test_empty_jd_nonzero(tmp_path, data_dir, capsys):
    p = tmp_path / "jd.json"
    p.write_text(json.dumps({"source_file": "x", "skills": []}))
    assert main(["--candidate", str(data_dir / "sample_candidate.json"), "--jd", str(p)]) == 2
