import json

from cipro import cli, store

from .conftest import FakeTransport, dag_jobs, jresp, make_run


def _seed_db(path, populated_src):
    dst = store.connect(path)
    populated_src.backup(dst)
    dst.close()


def test_report_and_summary_and_compare(tmp_path, populated, capsys):
    db = tmp_path / "c.sqlite"
    _seed_db(db, populated)
    out = tmp_path / "dash"
    assert cli.main(["--db", str(db), "report", "--workflow", "ci-baseline.yml", "--workflow", "ci-optimized.yml",
                     "--out", str(out), "--pair", "ci-baseline.yml:ci-optimized.yml", "--repo", "o/r"]) == 0
    page = (out / "index.html").read_text(encoding="utf-8")
    assert "Waste breakdown" in page and "Critical path" in page and "Paired comparison" in page
    assert json.loads((out / "summary.json").read_text())["ci-baseline.yml"]["runs"] == 5

    assert cli.main(["--db", str(db), "summary", "--workflow", "ci-baseline.yml"]) == 0
    assert '"runs": 5' in capsys.readouterr().out

    j = tmp_path / "cmp.json"
    assert cli.main(["--db", str(db), "compare", "--a", "ci-baseline.yml", "--b", "ci-optimized.yml",
                     "--json", str(j)]) == 0
    assert json.loads(j.read_text())["pairs"] == 5
    assert cli.main(["--db", str(db), "compare", "--a", "ci-baseline.yml", "--b", "nope.yml"]) == 2


def test_export_is_timestamped(tmp_path, populated):
    db = tmp_path / "c.sqlite"
    _seed_db(db, populated)
    assert cli.main(["--db", str(db), "export", "--workflow", "ci-baseline.yml", "--label", "baseline",
                     "--out", str(tmp_path / "res")]) == 0
    (d,) = list((tmp_path / "res").iterdir())
    assert d.name.startswith("baseline-")
    rows = (d / "runs.csv").read_text().strip().splitlines()
    assert len(rows) == 6  # header + 5 runs
    assert (d / "jobs.csv").exists() and (d / "meta.json").exists()
    assert json.loads((d / "ci-baseline.yml.summary.json").read_text())["runs"] == 5


def test_fetch_logs_and_rebuild(tmp_path, monkeypatch):
    api = "https://api.github.com/repos/o/r/"
    run = make_run(300, "abc")
    jobs = dag_jobs(3000, 0)
    t = FakeTransport({
        api + "actions/workflows/ci-optimized.yml/runs": jresp({"workflow_runs": [run]}),
        api + "actions/runs/300/jobs": jresp({"jobs": jobs}),
        api + "actions/runs/300/timing": jresp({"run_duration_ms": 330000, "billable": {}}),
        api + "actions/jobs/3000/logs": jresp({}, status=200),
        api + "actions/jobs/": jresp({}, status=410),
    })
    from cipro import github

    monkeypatch.setattr(cli, "_gh", lambda args: github.GitHub(args.repo, transport=t))
    db, raw = tmp_path / "f.sqlite", tmp_path / "raw"
    assert cli.main(["--db", str(db), "fetch", "--repo", "o/r", "--workflow", "ci-optimized.yml",
                     "--raw-dir", str(raw)]) == 0
    assert (raw / "ci-optimized.yml" / "300-1.json").exists()
    # second fetch skips stored runs
    calls_before = len(t.calls)
    cli.main(["--db", str(db), "fetch", "--repo", "o/r", "--workflow", "ci-optimized.yml", "--raw-dir", str(raw)])
    assert len(t.calls) == calls_before + 1

    assert cli.main(["--db", str(db), "logs", "--repo", "o/r", "--workflow", "ci-optimized.yml"]) == 0
    con = store.connect(db)
    assert store.logs_done(con, 3000)
    assert not store.logs_done(con, 3001)
    con.close()

    db2 = tmp_path / "rebuilt.sqlite"
    assert cli.main(["--db", str(db2), "rebuild", "--raw-dir", str(raw)]) == 0
    c2 = store.connect(db2)
    assert c2.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == len(jobs)
    assert c2.execute("SELECT run_duration_ms FROM run_timing").fetchone()[0] == 330000
