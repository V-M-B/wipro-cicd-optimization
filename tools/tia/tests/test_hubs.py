import copy
import time

from tia import coverage as cov
from tia.select import select

from .test_tia import CONFIG, repo, write  # noqa: F401  (repo is a pytest fixture)

HUB = (
    "import pytest\n"
    "from app.api import revenue as api_mod\n"
    "from app.metrics import util\n"
    "@pytest.fixture\n"
    "def client():\n"
    "    return api_mod\n"
    "@pytest.fixture\n"
    "def wrapped(client):\n"
    "    return client\n"
    "@pytest.fixture\n"
    "def constant():\n"
    "    return 1\n"
)


def _cfg():
    cfg = copy.deepcopy(CONFIG)
    cfg["app"][2]["hub_globs"] = ["tests/conftest.py"]
    return cfg


def test_fixture_aware_hub(repo):
    write(repo, {
        "apps/p/tests/conftest.py": HUB,
        # receives the API only through fixtures (no import): must still depend on app/api.py
        "apps/p/tests/fx/test_via_fixture.py": "def test_x(wrapped):\n    assert wrapped\n",
        "apps/p/tests/fx/test_plain.py": "def test_y(constant):\n    assert constant\n",
        "apps/p/tests/fx/test_marker.py": "import pytest\n@pytest.mark.usefixtures('client')\ndef test_z():\n    pass\n",
    })
    r = select(repo, _cfg(), ["apps/p/app/api.py"], use_dynamic=False)["apps"]["p"]
    assert "tests/fx/test_via_fixture.py" in r["suites"]["unit"]
    assert "tests/fx/test_marker.py" in r["suites"]["unit"]
    assert "tests/fx/test_plain.py" not in r["suites"]["unit"]
    assert any("resolved per requested fixture" in x for x in r["reasons"])


def test_hub_change_runs_everything(repo):
    write(repo, {"apps/p/tests/conftest.py": HUB})
    r = select(repo, _cfg(), ["apps/p/tests/conftest.py"], use_dynamic=False)["apps"]["p"]
    assert r["mode"] == "full"
    assert "hub changed: tests/conftest.py" in r["reasons"]


def test_autouse_fixture_applies_to_all(repo):
    write(repo, {
        "apps/p/tests/conftest.py": "import pytest\nfrom app.metrics import util\n"
                                    "@pytest.fixture(autouse=True)\ndef env():\n    return util\n",
        "apps/p/tests/test_plain.py": "def test_y():\n    pass\n",
    })
    r = select(repo, _cfg(), ["apps/p/app/metrics/util.py"], use_dynamic=False)["apps"]["p"]
    assert "tests/test_plain.py" in r["suites"]["unit"]


def test_hub_with_hooks_is_an_ordinary_dependency(repo):
    write(repo, {"apps/p/tests/conftest.py": "from app.api import *\ndef pytest_configure(config):\n    pass\n"})
    r = select(repo, _cfg(), ["apps/p/app/metrics/util.py"], use_dynamic=False)["apps"]["p"]
    assert len(r["suites"]["unit"]) == 4


def test_hub_without_fixtures_adds_no_dependencies(repo):
    write(repo, {"apps/p/tests/conftest.py": "from app.api import *\n"})
    r = select(repo, _cfg(), ["apps/p/app/metrics/util.py"], use_dynamic=False)["apps"]["p"]
    # real import chains only: revenue->util, customers->util, api->customers->util
    assert set(r["suites"]["unit"]) == {"tests/metrics/test_customers.py", "tests/metrics/test_revenue.py",
                                        "tests/test_api.py"}


def test_empty_selection_falls_back_to_mirrored_tests(repo):
    now = time.time()
    cov.write_map(repo / "cov/p.json", {"apps/p/app/api.py": {"apps/p/tests/test_api.py"}}, "t", now=now)
    write(repo, {"apps/p/app/metrics/lonely.py": "Y = 2\n"})
    r = select(repo, CONFIG, ["apps/p/app/metrics/lonely.py"], now=now)["apps"]["p"]
    assert set(r["suites"]["unit"]) == {"tests/metrics/test_customers.py", "tests/metrics/test_revenue.py"}
    assert any("used mirrored tests" in x for x in r["reasons"])
