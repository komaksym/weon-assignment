from weon_eval.budget_search_cli import execution_methods
from weon_eval.search_methods import SEARCH_METHODS, TARGETED_METHODS


def test_targeted_execution_prepends_direct_baseline_control() -> None:
    methods = execution_methods("targeted")

    assert methods[0].name == "lite_direct"
    assert methods[1:] == TARGETED_METHODS
    assert sum(method.name == "lite_direct" for method in methods) == 1


def test_broad_execution_queue_is_unchanged() -> None:
    assert execution_methods("broad") == SEARCH_METHODS
