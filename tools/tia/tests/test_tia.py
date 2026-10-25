import json
import subprocess
import time
from pathlib import Path

import pytest

from tia import cli
from tia import coverage as cov
from tia import graph as g
from tia.select import App, decide, match, select


def write(root: Path, files: dict[str, str]) -> None:
    for path, text in files.items():
        p = root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


JAVA = {
    "apps/j/pom.xml": "<project/>",
    "apps/j/src/main/java/com/x/pricing/PricingService.java":
        "package com.x.pricing;\nimport com.x.tax.TaxTable;\npublic class PricingService { TaxTable t; Money m; }",
    "apps/j/src/main/java/com/x/pricing/Money.java": "package com.x.pricing;\npublic record Money(int c) {}",
    "apps/j/src/main/java/com/x/tax/TaxTable.java": "package com.x.tax;\npublic class TaxTable {}",
    "apps/j/src/main/java/com/x/tax/Unused.java": "package com.x.tax;\npublic class Unused {}",
    "apps/j/src/main/java/com/x/order/OrderService.java":
        "package com.x.order;\nimport com.x.pricing.*;\nimport static com.x.tax.TaxTable.rate;\n"
        "public class OrderService { PricingService p; }",
    "apps/j/src/test/java/com/x/pricing/PricingServiceTest.java":
        "package com.x.pricing;\nclass PricingServiceTest { PricingService s; }",
    "apps/j/src/test/java/com/x/order/OrderServiceTest.java":
        "package com.x.order;\nclass OrderServiceTest { OrderService s; }",
    "apps/j/src/test/java/com/x/tax/TaxTableTest.java": "package com.x.tax;\nclass TaxTableTest { TaxTable t; }",
    "apps/j/src/test/java/com/x/AppIT.java": "package com.x;\nclass AppIT {}",
    "apps/j/README.md": "docs",
}

TS = {
    "apps/w/src/lib/cart.ts": "import { round } from './math';\nexport const total = 1;",
    "apps/w/src/lib/math.ts": "export const round = (x: number) => x;",
    "apps/w/src/lib/index.ts": "export * from './cart';",
    "apps/w/src/generated/schemas.ts": "export type Order = {};",
    "apps/w/src/pages/Orders.tsx": "import type { Order } from '@/generated/schemas';\nimport { total } from '../lib';\nimport React from 'react';",
    "apps/w/src/lib/cart.test.ts": "import { total } from './cart';",
    "apps/w/src/lib/math.test.ts": "import { round } from './math';",
    "apps/w/src/pages/Orders.test.tsx": "import Orders from './Orders';\nvi.mock('../lib/math');",
    "apps/w/e2e/orders.spec.ts": "import { test } from '@playwright/test';",
    "apps/w/package.json": "{}",
}

PY = {
    "apps/p/app/__init__.py": "",
    "apps/p/app/metrics/__init__.py": "",
    "apps/p/app/metrics/revenue.py": "from ..generated.schemas import Order\nfrom . import util\n",
    "apps/p/app/metrics/util.py": "X = 1\n",
    "apps/p/app/metrics/customers.py": "import app.metrics.util\n",
    "apps/p/app/generated/__init__.py": "",
    "apps/p/app/generated/schemas.py": "class Order: ...\n",
    "apps/p/app/api.py": "from app.metrics import revenue, customers\n",
    "apps/p/tests/conftest.py": "import pytest\n",
    "apps/p/tests/metrics/test_revenue.py": "from app.metrics.revenue import *\n",
    "apps/p/tests/metrics/test_customers.py": "from app.metrics import customers\n",
    "apps/p/tests/test_api.py": "from app.api import *\n",
    "apps/p/tests/test_broken.py": "def (:\n",
    "apps/p/requirements.txt": "fastapi\n",
}

CONFIG = {
    "settings": {"coverage_max_age_days": 7, "always_full_globs": [".github/workflows/**"]},
    "app": [
        {"name": "j", "language": "java", "root": "apps/j", "sources": ["src/main/java/**/*.java"],
         "suites": {"unit": ["src/test/java/**/*Test.java"], "integration": ["src/test/java/**/*IT.java"]},
         "full_globs": ["pom.xml"], "ignore_globs": ["**/*.md", "*.md"], "unit_style": "java-class",
         "mirror": {"src/main/java/": "src/test/java/"}, "full_suite_on_source_change": ["integration"],
         "unknown_file_full_exts": [".java"]},
        {"name": "w", "language": "ts", "root": "apps/w", "sources": ["src/**/*.ts", "src/**/*.tsx"],
         "suites": {"unit": ["src/**/*.test.ts", "src/**/*.test.tsx"], "e2e": ["e2e/**/*.spec.ts"]},
         "aliases": {"@/": "src/"}, "full_globs": ["package.json"], "mirror": {"src/": "src/"},
         "smoke": {"e2e": ["e2e/orders.spec.ts"]}},
        {"name": "p", "language": "python", "root": "apps/p", "sources": ["app/**/*.py"],
         "support": ["tests/**/conftest.py"], "suites": {"unit": ["tests/**/test_*.py"]},
         "full_globs": ["requirements*.txt"], "python_roots": ["."], "mirror": {"app/": "tests/"},
         "coverage_map": "cov/p.json"},
    ],
}


@pytest.fixture
def repo(tmp_path):
    write(tmp_path, JAVA | TS | PY)
    return tmp_path


def test_match_globs():
    assert match("a/b/c.md", ["**/*.md"])
    assert match("c.md", ["**/*.md"])
    assert match(".github/workflows/ci.yml", [".github/workflows/**"])
    assert not match("src/x.ts", ["**/*.md"])


def test_java_graph(repo):
    files = sorted((repo / "apps/j").rglob("*.java"))
    gr = g.java_graph(files, repo)
    base = "apps/j/src/main/java/com/x/"
    assert gr[base + "pricing/PricingService.java"] == {base + "tax/TaxTable.java", base + "pricing/Money.java"}
    # wildcard import resolves only referenced classes; static import resolves owner
    assert gr[base + "order/OrderService.java"] == {base + "pricing/PricingService.java", base + "tax/TaxTable.java"}
    rc = g.reverse_closure(gr, ["apps/j/src/test/java/com/x/order/OrderServiceTest.java"])
    assert base + "pricing/Money.java" in rc


def test_ts_graph(repo):
    files = sorted((repo / "apps/w").rglob("*.ts*"))
    gr = g.ts_graph(files, repo, {"@/": repo / "apps/w/src/"})
    assert gr["apps/w/src/pages/Orders.tsx"] == {"apps/w/src/generated/schemas.ts", "apps/w/src/lib/index.ts"}
    assert gr["apps/w/src/pages/Orders.test.tsx"] == {"apps/w/src/pages/Orders.tsx", "apps/w/src/lib/math.ts"}
    assert gr["apps/w/e2e/orders.spec.ts"] == set()


def test_python_graph(repo):
    files = sorted((repo / "apps/p").rglob("*.py"))
    gr = g.python_graph(files, repo, [repo / "apps/p"])
    assert "apps/p/app/generated/schemas.py" in gr["apps/p/app/metrics/revenue.py"]
    assert "apps/p/app/metrics/util.py" in gr["apps/p/app/metrics/revenue.py"]
    assert "apps/p/app/metrics/util.py" in gr["apps/p/app/metrics/customers.py"]
    assert "apps/p/tests/conftest.py" in gr["apps/p/tests/test_api.py"]
    assert gr["apps/p/tests/test_broken.py"] == {"apps/p/tests/conftest.py"}


def run(repo, changed, now=None, use_dynamic=True):
    return select(repo, CONFIG, changed, now=now, use_dynamic=use_dynamic)["apps"]


def test_java_selection_subset_and_it_rule(repo):
    r = run(repo, ["apps/j/src/main/java/com/x/tax/TaxTable.java"])["j"]
    assert r["mode"] == "subset"
    assert r["suites"]["unit"] == ["com.x.order.OrderServiceTest", "com.x.pricing.PricingServiceTest",
                                   "com.x.tax.TaxTableTest"]
    assert r["suites"]["integration"] == ["com.x.AppIT"]


def test_java_mirror_widening_selects_package_tests(repo):
    # Unused has no importers; widening selects tests in the mirrored package com/x/tax
    r = run(repo, ["apps/j/src/main/java/com/x/tax/Unused.java"])["j"]
    assert "com.x.tax.TaxTableTest" in r["suites"]["unit"]


def test_full_triggers(repo):
    assert run(repo, ["apps/j/pom.xml"])["j"]["mode"] == "full"
    all_apps = run(repo, [".github/workflows/ci.yml"])
    assert {d["mode"] for d in all_apps.values()} == {"full"}
    assert all_apps["w"]["suites"]["e2e"] == ["e2e/orders.spec.ts"]
    assert run(repo, ["apps/j/src/main/java/com/x/New.java"])["j"]["mode"] == "full"  # unknown java file


def test_ignored_and_unrelated(repo):
    r = run(repo, ["apps/j/README.md", "apps/p/app/api.py"])
    assert r["j"]["mode"] == "none" and "ignored" in r["j"]["reasons"][0]
    assert r["w"]["mode"] == "none"


def test_ts_selection_with_alias_and_smoke(repo):
    r = run(repo, ["apps/w/src/generated/schemas.ts"])["w"]
    assert r["suites"]["unit"] == ["src/pages/Orders.test.tsx"]
    assert r["suites"]["e2e"] == ["e2e/orders.spec.ts"]  # smoke
    r = run(repo, ["apps/w/src/lib/math.ts"])["w"]
    assert set(r["suites"]["unit"]) == {"src/lib/cart.test.ts", "src/lib/math.test.ts", "src/pages/Orders.test.tsx"}


def test_changed_test_file_selects_itself(repo):
    r = run(repo, ["apps/w/src/lib/math.test.ts"])["w"]
    assert "src/lib/math.test.ts" in r["suites"]["unit"]


def test_python_with_and_without_dynamic_map(repo):
    now = time.time()
    cov.write_map(repo / "cov/p.json", {"apps/p/app/metrics/util.py": {"apps/p/tests/test_api.py"}}, "test", now=now)
    r = run(repo, ["apps/p/app/metrics/util.py"], now=now)["p"]
    assert set(r["suites"]["unit"]) == {"tests/metrics/test_revenue.py", "tests/metrics/test_customers.py",
                                        "tests/test_api.py"}
    assert "days old" in r["reasons"][0]
    # stale map -> static + widening
    r = run(repo, ["apps/p/app/metrics/util.py"], now=now + 30 * 86400)["p"]
    assert "30.0 days old" in r["reasons"][0]
    assert any("widened" in x for x in r["reasons"])
    r = run(repo, ["apps/p/app/metrics/util.py"], use_dynamic=False)["p"]
    assert "disabled" in r["reasons"][0]


def test_missing_coverage_map_note(repo):
    r = run(repo, ["apps/p/app/api.py"])["p"]
    assert "missing" in r["reasons"][0]
    # static hit plus widening to root-level tests (no coverage map)
    assert r["suites"]["unit"] == ["tests/test_api.py", "tests/test_broken.py"]


def test_app_unknown_language(repo):
    app = App({"name": "z", "language": "cobol", "root": "apps/z", "sources": [], "suites": {"unit": []}}, repo)
    with pytest.raises(ValueError):
        decide(app, ["apps/z/a.cbl"], {})


def test_coverage_helpers(tmp_path):
    assert cov.context_to_test_file("tests/test_a.py::TestX::test_y|run") == "tests/test_a.py"
    assert cov.context_to_test_file("") is None
    assert cov.context_to_test_file("some-label") is None
    data = {"files": {"app/a.py": {"contexts": {"1": ["", "tests/test_a.py::t|run"], "2": ["tests/test_b.py::u|run"]}},
                      "app/b.py": {"contexts": {"1": [""]}}}}
    m = cov.from_coverage_py(data, prefix="apps/p")
    assert m == {"apps/p/app/a.py": {"apps/p/tests/test_a.py", "apps/p/tests/test_b.py"}}
    inv = cov.from_per_test_files({"src/a.test.ts": ["src/a.ts", "src/b.ts"]}, prefix="apps/w")
    assert inv["apps/w/src/b.ts"] == {"apps/w/src/a.test.ts"}


def test_cli(repo, capsys, monkeypatch, tmp_path):
    import tomllib  # noqa: F401
    cfg = repo / "tia.toml"
    cfg.write_text(_toml(CONFIG), encoding="utf-8")
    changed = repo / "changed.txt"
    changed.write_text("apps/w/src/lib/math.ts\napps\\p\\app\\api.py\n")
    out = repo / "sel.json"
    assert cli.main(["select", "--config", str(cfg), "--repo", str(repo), "--changed", str(changed),
                     "--out", str(out)]) == 0
    sel = json.loads(out.read_text())
    assert sel["apps"]["p"]["suites"]["unit"] == ["tests/test_api.py", "tests/test_broken.py"]
    assert cli.main(["show", "--selection", str(out), "--app", "w", "--style", "args"]) == 0
    assert "src/lib/math.test.ts" in capsys.readouterr().out
    assert cli.main(["show", "--selection", str(out), "--app", "j", "--field", "mode"]) == 0
    assert capsys.readouterr().out.strip() == "none"
    assert cli.main(["select", "--config", str(cfg), "--repo", str(repo), "--changed", str(changed),
                     "--static-only"]) == 0
    assert '"static_only": true' in capsys.readouterr().out

    cj = tmp_path / "c.json"
    cj.write_text(json.dumps({"files": {"app/a.py": {"contexts": {"1": ["tests/test_a.py::t|run"]}}}}))
    assert cli.main(["coverage-python", "--coverage-json", str(cj), "--prefix", "apps/p", "--out", str(tmp_path / "m1.json")]) == 0
    cov.write_map(tmp_path / "m2.json", {"apps/p/app/a.py": {"apps/p/tests/test_z.py"}}, "x")
    assert cli.main(["coverage-merge", str(tmp_path / "m1.json"), str(tmp_path / "m2.json"), "--out", str(tmp_path / "m.json")]) == 0
    merged = json.loads((tmp_path / "m.json").read_text())["map"]
    assert merged["apps/p/app/a.py"] == ["apps/p/tests/test_a.py", "apps/p/tests/test_z.py"]


def test_git_changed_files(tmp_path):
    from tia.select import changed_files

    def git(*a):
        subprocess.run(["git", *a], cwd=tmp_path, check=True, capture_output=True)

    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    write(tmp_path, {"a.txt": "1"})
    git("add", "-A")
    git("commit", "-q", "-m", "a")
    git("checkout", "-q", "-b", "feature")
    write(tmp_path, {"b/c.txt": "2", "a.txt": "3"})
    git("add", "-A")
    git("commit", "-q", "-m", "b")
    assert changed_files(tmp_path, "main", "feature") == ["a.txt", "b/c.txt"]


def _toml(cfg: dict) -> str:
    def val(v):
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (int, float)):
            return str(v)
        if isinstance(v, str):
            return json.dumps(v)
        if isinstance(v, list):
            return "[" + ", ".join(val(x) for x in v) + "]"
        if isinstance(v, dict):
            return "{ " + ", ".join(f"{json.dumps(k)} = {val(x)}" for k, x in v.items()) + " }"
        raise TypeError(v)

    lines = ["[settings]"] + [f"{k} = {val(v)}" for k, v in cfg["settings"].items()]
    for app in cfg["app"]:
        lines += ["", "[[app]]"] + [f"{k} = {val(v)}" for k, v in app.items()]
    return "\n".join(lines)
