import copy

from tia.select import select

from .test_tia import CONFIG, repo, write  # noqa: F401  (repo is a pytest fixture)


def test_helper_module_does_not_inherit_hub_edges(repo):
    cfg = copy.deepcopy(CONFIG)
    cfg["app"][2]["hub_globs"] = ["tests/conftest.py"]
    cfg["app"][2]["support"] = ["tests/**/conftest.py", "tests/helpers.py"]
    write(repo, {
        "apps/p/tests/conftest.py": "import pytest\nfrom app.api import revenue\n"
                                    "@pytest.fixture\ndef client():\n    return revenue\n",
        "apps/p/tests/helpers.py": "X = 1\n",
        "apps/p/tests/fx/test_uses_helper.py": "from tests import helpers\ndef test_h():\n    assert helpers.X\n",
    })
    r = select(repo, cfg, ["apps/p/app/api.py"], use_dynamic=False)["apps"]["p"]
    assert "tests/fx/test_uses_helper.py" not in r["suites"]["unit"]
