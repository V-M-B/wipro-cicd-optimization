import json

import pytest

from shardkit import cli, core

SUREFIRE = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="com.retailops.orders.pricing.PricingServiceTest" tests="3">
  <testcase name="a" classname="com.retailops.orders.pricing.PricingServiceTest" time="1.5"/>
  <testcase name="b" classname="com.retailops.orders.pricing.PricingServiceTest" time="0.5"/>
  <testcase name="c" classname="com.retailops.orders.order.StateMachineTest" time="0.25"/>
</testsuite>"""

VITEST = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="vitest tests">
  <testsuite name="src/lib/cart.test.ts" tests="2">
    <testcase classname="src/lib/cart.test.ts" name="x" time="0.2"/>
    <testcase classname="src/lib/cart.test.ts" name="y" time="0.3"/>
  </testsuite>
  <testsuite name="src/pages/Orders.test.tsx" tests="1">
    <testcase classname="src/pages/Orders.test.tsx" name="z" time="2.0"/>
  </testsuite>
</testsuites>"""

PYTEST = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest">
  <testcase classname="tests.metrics.test_revenue" name="t1" time="0.4"/>
  <testcase classname="tests.metrics.test_revenue.TestWeekly" name="t2" time="0.6"/>
  <testcase classname="tests.test_api" name="t3" time="1.0" file="tests/test_api.py"/>
</testsuite></testsuites>"""


@pytest.fixture
def files(tmp_path):
    (tmp_path / "s.xml").write_text(SUREFIRE)
    (tmp_path / "v.xml").write_text(VITEST)
    (tmp_path / "p.xml").write_text(PYTEST)
    (tmp_path / "tests/metrics").mkdir(parents=True)
    (tmp_path / "tests/metrics/test_revenue.py").write_text("")
    return tmp_path


def test_parse_junit_classes(files):
    d = core.parse_junit([str(files / "s.xml")], "junit")
    assert d == {"com.retailops.orders.order.StateMachineTest": 0.25,
                 "com.retailops.orders.pricing.PricingServiceTest": 2.0}


def test_parse_vitest_files(files):
    d = core.parse_junit([str(files / "v.xml")], "vitest")
    assert d == {"src/lib/cart.test.ts": 0.5, "src/pages/Orders.test.tsx": 2.0}


def test_parse_pytest_modules_with_root(files):
    d = core.parse_junit([str(files / "p.xml")], "pytest", root=str(files))
    assert d == {"tests/metrics/test_revenue.py": 1.0, "tests/test_api.py": 1.0}


def test_parse_pytest_without_root_drops_class():
    assert core._pytest_unit("tests.test_x.TestFoo", None, None) == "tests/test_x.py"
    assert core._pytest_unit("tests.test_x", None, None) == "tests/test_x.py"


def test_bad_framework(files):
    with pytest.raises(ValueError):
        core.parse_junit([str(files / "s.xml")], "nope")


def test_lpt_beats_round_robin():
    durations = {f"u{i}": float(d) for i, d in enumerate([30, 29, 28, 2, 2, 2, 1, 1, 1, 1, 1, 1])}
    units = sorted(durations)
    lpt = core.imbalance(core.plan_lpt(durations, units, 3), durations)
    rr = core.imbalance(core.plan_round_robin(units, 3), durations)
    assert lpt["spread_s"] < rr["spread_s"]
    assert sum(lpt["loads_s"]) == pytest.approx(sum(durations.values()))
    assert lpt["ideal_s"] == pytest.approx(sum(durations.values()) / 3)


def test_lpt_is_deterministic_and_complete():
    durations = {"a": 5, "b": 5, "c": 5, "d": 1}
    units = ["d", "c", "b", "a", "new1", "new2"]
    p1 = core.plan_lpt(durations, units, 2)
    assert p1 == core.plan_lpt(durations, list(reversed(units)), 2)
    assert sorted(u for s in p1 for u in s) == sorted(units)


def test_unknown_units_use_median_and_empty_history_uses_one():
    est = core._estimate({"a": 10, "b": 2, "c": 4}, ["a", "b", "c", "z"])
    assert est["z"] == 4
    assert core._estimate({}, ["x"]) == {"x": 1.0}


def test_more_shards_than_units():
    plan = core.plan_lpt({"a": 1}, ["a"], 3)
    assert sum(len(s) for s in plan) == 1 and len(plan) == 3
    with pytest.raises(ValueError):
        core.plan_lpt({}, ["a"], 0)


def test_java_unit_from_path():
    assert core.java_unit_from_path("apps/orders-api/src/test/java/com/x/FooTest.java") == "com.x.FooTest"
    assert core.java_unit_from_path("com\\x\\BarIT.java".replace("\\", "/")) == "com.x.BarIT"


def test_render_styles():
    assert core.render(["a", "b"], "junit", "maven") == "a,b"
    assert core.render(["a", "b"], "vitest", "args") == "a b"
    assert core.render(["a"], "pytest", "lines") == "a"
    assert json.loads(core.render(["a"], "pytest", "json")) == ["a"]
    with pytest.raises(ValueError):
        core.render(["a"], "pytest", "xml")


def test_cli_end_to_end(files, tmp_path, capsys, monkeypatch):
    src = tmp_path / "app/src/test/java/com/x"
    src.mkdir(parents=True)
    for n in ("ATest", "BTest", "CTest", "DTest"):
        (src / f"{n}.java").write_text("")
    xml = tmp_path / "r.xml"
    xml.write_text("""<testsuite name="s">
      <testcase classname="com.x.ATest" name="1" time="10"/>
      <testcase classname="com.x.BTest" name="1" time="9"/>
      <testcase classname="com.x.CTest" name="1" time="1"/>
      <testcase classname="com.x.DTest" name="1" time="1"/></testsuite>""")
    out = tmp_path / "d.json"
    assert cli.main(["durations", "--framework", "junit", "--junit", str(xml), "--out", str(out)]) == 0
    assert json.loads(out.read_text())["com.x.ATest"] == 10
    capsys.readouterr()

    glob_ = str(tmp_path / "app/src/test/java/**/*Test.java")
    shards = []
    for i in range(2):
        assert cli.main(["plan", "--framework", "junit", "--durations", str(out), "--units", glob_,
                         "--shards", "2", "--index", str(i), "--style", "maven", "--summary"]) == 0
        shards.append(capsys.readouterr().out.strip().split(","))
    assert sorted(shards[0] + shards[1]) == ["com.x.ATest", "com.x.BTest", "com.x.CTest", "com.x.DTest"]
    assert {"com.x.ATest", "com.x.BTest"} not in [set(s) for s in shards]

    assert cli.main(["compare", "--framework", "junit", "--durations", str(out), "--units", glob_, "--shards", "2"]) == 0
    res = json.loads(capsys.readouterr().out)
    assert res["lpt"]["spread_s"] <= res["round_robin"]["spread_s"]

    # no history -> round robin
    assert cli.main(["plan", "--framework", "junit", "--durations", str(tmp_path / "missing.json"),
                     "--units", glob_, "--shards", "2", "--index", "0"]) == 0
    assert capsys.readouterr().out.strip().splitlines() == ["com.x.ATest", "com.x.CTest"]


def test_cli_errors(tmp_path):
    assert cli.main(["durations", "--framework", "junit", "--junit", str(tmp_path / "none*.xml"),
                     "--out", str(tmp_path / "o.json")]) == 1
    with pytest.raises(SystemExit):
        cli.main(["plan", "--framework", "vitest", "--units", str(tmp_path / "*.ts"), "--shards", "2", "--index", "0"])
    (tmp_path / "a.test.ts").write_text("")
    with pytest.raises(SystemExit):
        cli.main(["plan", "--framework", "vitest", "--units", str(tmp_path / "*.ts"), "--shards", "2", "--index", "5"])


def test_strip_prefix(tmp_path, capsys):
    (tmp_path / "e2e").mkdir()
    (tmp_path / "e2e/a.spec.ts").write_text("")
    units = core.discover([str(tmp_path / "e2e/*.spec.ts")], "playwright", strip_prefix=str(tmp_path))
    assert units == ["e2e/a.spec.ts"]


def test_suite_time_includes_setup(tmp_path):
    x = tmp_path / "TEST-it.xml"
    x.write_text('<testsuite name="com.x.SlowIT" time="18.0">'
                 '<testcase classname="com.x.SlowIT" name="a" time="0.5"/>'
                 '<testcase classname="com.x.SlowIT" name="b" time="0.5"/></testsuite>')
    assert core.parse_junit([str(x)], "junit") == {"com.x.SlowIT": 18.0}
