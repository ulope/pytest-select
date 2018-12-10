import pytest


TEST_CONTENT = """
    import pytest
    
    @pytest.mark.parametrize(
        ('a', 'b'),
        (
            (1, 1),
            (1, 2),
            (1, 3),
            (1, 4),
        )
    )
    def test_a(a, b):
        assert b in (1, 4)
"""


@pytest.mark.parametrize("option_name", ("--select-from-file", "--deselect-from-file"))
def test_select_options_exist(testdir, option_name):
    selection_file_name = testdir.makefile(".txt", "test_a", "test_b")
    result = testdir.runpytest(option_name, selection_file_name)

    result.assert_outcomes()
    assert result.ret == 5


def test_select_options_conflict(testdir):
    result = testdir.runpytest("--select-from-file", "bla", "--deselect-from-file", "bla")

    assert result.ret == 4
    result.stderr.re_match_lines(
        ["ERROR: '--select-from-file' and '--deselect-from-file' can not be used together."]
    )


@pytest.mark.parametrize("option_name", ("--select-from-file", "--deselect-from-file"))
def test_missing_selection_file_fails(testdir, option_name):
    missing_file_name = "no_such_file.txt"
    result = testdir.runpytest(option_name, missing_file_name)

    assert result.ret == 4
    result.stderr.re_match_lines(
        [f"ERROR: Given selection file '{missing_file_name}' doesn't exist."]
    )


@pytest.mark.parametrize(
    ("select_option", "select_content", "exit_code", "outcomes", "stdout_lines"),
    (
        (None, "", 1, {"passed": 2, "failed": 2}, []),
        ("--select-from-file", ["test_a[1-1]", "test_a[1-4]"], 0, {"passed": 2}, []),
        (
            "--select-from-file",
            ["{testfile}::test_a[1-2]", "test_a[1-4]"],
            1,
            {"passed": 1, "failed": 1},
            [],
        ),
        (
            "--select-from-file",
            ["{testfile}::test_a[1-2]", "test_a[1-3]", "test_a[3-1]", "test_that_does_not_exist"],
            1,
            {"failed": 2},
            [
                r".*Not all selected tests exist \(or have been deselected otherwise\).*",
                r"\s+Missing selected test names:",
                r"\s+- test_a\[3-1\]",
                r"\s+- test_that_does_not_exist",
            ],
        ),
        ("--deselect-from-file", ["test_a[1-1]", "test_a[1-4]"], 1, {"failed": 2}, []),
        (
            "--deselect-from-file",
            ["{testfile}::test_a[1-2]", "test_a[1-4]"],
            1,
            {"passed": 1, "failed": 1},
            [],
        ),
        (
            "--deselect-from-file",
            ["{testfile}::test_a[1-2]", "test_a[1-3]", "test_a[3-1]", "test_that_does_not_exist"],
            0,
            {"passed": 2},
            [
                r".*Not all deselected tests exist \(or have been selected otherwise\).*",
                r"\s+Missing deselected test names:",
                r"\s+- test_a\[3-1\]",
                r"\s+- test_that_does_not_exist",
            ],
        ),
    ),
)
def test_tests_are_selected(
    testdir, select_option, exit_code, select_content, outcomes, stdout_lines
):
    testfile = testdir.makefile(".py", TEST_CONTENT)
    args = ["-v", "-Walways"]
    if select_option and select_content:
        select_file = testdir.makefile(
            ".txt",
            *[line.format(testfile=testfile.relto(testdir.tmpdir)) for line in select_content],
        )
        args.extend([select_option, select_file])
    result = testdir.runpytest(*args)

    assert result.ret == exit_code
    result.assert_outcomes(**outcomes)
    if stdout_lines:
        result.stdout.re_match_lines_random(stdout_lines)


@pytest.mark.parametrize("deselect", (False, True))
def test_fail_on_missing(testdir, deselect):
    testdir.makefile(".py", TEST_CONTENT)
    selectfile = testdir.makefile(".txt", "test_a[1-1]", "test_a[2-1]")
    result = testdir.runpytest(
        "-v",
        "--select-fail-on-missing",
        f"--{'de' if deselect else ''}select-from-file",
        selectfile,
    )
    assert result.ret == 4
    result.stderr.re_match_lines(
        [
            (
                fr"ERROR: pytest-select: Not all {'de' if deselect else ''}selected tests exist "
                fr"\(or have been {'' if deselect else 'de'}selected otherwise\)."
            ),
            f"Missing {'de' if deselect else ''}selected test names:",
            "  - test_a[2-1]",
        ]
    )
