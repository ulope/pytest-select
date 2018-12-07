import warnings
from pathlib import Path

from pytest import PytestWarning, UsageError


class PytestSelectWarning(PytestWarning):
    pass


def pytest_addoption(parser):
    parser.addoption(
        "--select-from-file",
        action="store",
        dest="selectfromfile",
        default=None,
        help="Select tests given in file. One line per test name.",
    )
    parser.addoption(
        "--deselect-from-file",
        action="store",
        dest="deselectfromfile",
        default=None,
        help="Deselect tests given in file. One line per test name.",
    )


def pytest_collection_modifyitems(session, config, items):
    is_option_conflict = (
        config.getoption("selectfromfile") is not None
        and config.getoption("deselectfromfile") is not None
    )
    if is_option_conflict:
        raise UsageError(
            "'--select-from-file' and '--deselect-from-file' can not be used together."
        )

    for option_name, should_select in [("selectfromfile", True), ("deselectfromfile", False)]:
        selection_file_name = config.getoption(option_name)
        if selection_file_name is None:
            continue

        selection_file_path = Path(selection_file_name)
        if not selection_file_path.exists():
            raise UsageError(f"Given selection file '{selection_file_name}' doesn't exist.")

        with selection_file_path.open("rt", encoding="UTF-8") as selection_file:
            test_names = {test_name.strip() for test_name in selection_file}

        seen_test_names = set()
        selected_items = []
        deselected_items = []
        for item in items:
            if item.name in test_names or item.nodeid in test_names:
                selected_items.append(item)
            else:
                deselected_items.append(item)
            seen_test_names.add(item.name)
            seen_test_names.add(item.nodeid)

        if not should_select:
            # We are *de*selecting, flip collections
            selected_items, deselected_items = deselected_items, selected_items

        missing_test_names = test_names - seen_test_names
        if missing_test_names:
            # If any items remain in `test_names` those tests either don't exist or
            # have been deselected by another way - warn user

            message = (
                f"pytest-select: Not all {'' if should_select else 'de'}selected tests exist "
                f"(or have been {'de' if should_select else ''}selected otherwise).\n"
                f"Missing {'' if should_select else 'de'}selected test names:\n  - "
            )
            message += "\n  - ".join(missing_test_names)
            warnings.warn(message, PytestSelectWarning)

        # Slice assignment is required since `items` needs to be modified in place
        items[:] = selected_items
        config.hook.pytest_deselected(items=deselected_items)
