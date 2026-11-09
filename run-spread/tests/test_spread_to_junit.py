"""Offline tests for spread_to_junit.py."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from spread_to_junit import TestCase, convert, main, parse_log

TS = "2026-10-28 20:0"

FIXTURES = Path(__file__).parent / "fixtures"


def _case(root: ET.Element, name: str, classname: str | None = None) -> ET.Element:
    for element in root.findall("testsuite/testcase"):
        if element.get("name") == name and (
            classname is None or element.get("classname") == classname
        ):
            return element
    raise AssertionError(
        f"no testcase {name!r} (classname={classname!r}) in {name and list(root.findall('testsuite/testcase'))}"
    )


def _suite(root: ET.Element) -> ET.Element:
    suite = root.find("testsuite")
    assert suite is not None
    return suite


def _failure(case: ET.Element) -> ET.Element:
    failure = case.find("failure")
    assert failure is not None
    return failure


def _skipped(case: ET.Element) -> ET.Element:
    element = case.find("skipped")
    assert element is not None
    return element


def _message(case: ET.Element, tag: str) -> str:
    message = case.find(tag)
    assert message is not None
    text = message.get("message")
    assert text is not None
    return text


# region parsing


def test_task_outcomes_reconstructed_from_control_lines():
    log = "\n".join(
        [
            f"{TS}1:42 Preparing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}1:58 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            "+ echo hello",
            "hello",
            f"{TS}2:30 Executing openstack:ubuntu-24.04-64:tests/spread/core24/basic (worker-1)...",
            f"{TS}3:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/lint:variant (worker-1)...",
            f"{TS}6:37 Error executing openstack:ubuntu-24.04-64:tests/spread/core24/lint:variant (worker-1) : ",
            "-----",
            "+ cd library-gnome",
            "+ snapcraft pack",
            "-----",
            ".",
            f"{TS}6:45 Executing openstack:ubuntu-24.04-64:tests/spread/core24/other (worker-1)...",
            f"{TS}7:10 Successful tasks: 3",
            f"{TS}7:10 Aborted tasks: 0",
            f"{TS}7:10 Failed tasks: 1",
            "    - openstack:ubuntu-24.04-64:tests/spread/core24/lint:variant",
        ]
    )
    root = convert(log)
    suite = _suite(root)
    assert suite.get("tests") == "4"
    assert suite.get("failures") == "1"
    assert suite.get("skipped") == "0"

    passed = _case(root, "tests/spread/core24/foo", "openstack:ubuntu-24.04-64")
    assert passed.find("failure") is None and passed.find("skipped") is None
    _case(root, "tests/spread/core24/basic", "openstack:ubuntu-24.04-64")
    _case(root, "tests/spread/core24/other", "openstack:ubuntu-24.04-64")

    failed = _case(
        root, "tests/spread/core24/lint:variant", "openstack:ubuntu-24.04-64"
    )
    failure = failed.find("failure")
    assert failure is not None
    assert failure.get("message") == "+ cd library-gnome"
    assert failure.text == "+ cd library-gnome\n+ snapcraft pack"
    # Duration: start 20:03:00 -> error 20:06:37.
    assert failed.get("time") == "217.000"


def test_prepare_and_restore_starts_do_not_become_testcases():
    log = "\n".join(
        [
            f"{TS}0:00 Preparing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:10 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:20 Restoring openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:30 Successful tasks: 1",
            f"{TS}0:30 Aborted tasks: 0",
        ]
    )
    root = convert(log)
    assert _suite(root).get("tests") == "1"
    _case(root, "tests/spread/core24/foo")


def test_progress_counter_in_start_line_is_ignored():
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1) (1/2)...",
            f"{TS}0:10 Executing openstack:ubuntu-24.04-64:tests/spread/core24/bar (worker-1) (2/2)...",
            f"{TS}0:20 Successful tasks: 2",
            f"{TS}0:20 Aborted tasks: 0",
        ]
    )
    root = convert(log)
    assert _suite(root).get("tests") == "2"
    _case(root, "tests/spread/core24/foo")
    _case(root, "tests/spread/core24/bar")


def test_task_output_is_not_mistaken_for_control_lines():
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            "Error some unexpected task output: does not match",
            "Executing something without a label is not a control line",
            "Failed tasks: 999",
            f"{TS}0:10 Successful tasks: 1",
            f"{TS}0:10 Aborted tasks: 0",
        ]
    )
    root = convert(log)
    suite = _suite(root)
    assert suite.get("tests") == "1"
    assert suite.get("failures") == "0"


def test_error_block_contents_are_not_parsed_as_control_lines():
    # The "-----"-wrapped block holds arbitrary task output, which may itself
    # look like control lines.
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:10 Error executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1) : ",
            "-----",
            f"{TS}0:11 Executing openstack:ubuntu-24.04-64:tests/spread/core24/fake (worker-9)...",
            f"{TS}0:12 Successful tasks: 999",
            "-----",
            ".",
            f"{TS}0:20 Successful tasks: 0",
            f"{TS}0:20 Aborted tasks: 0",
            f"{TS}0:20 Failed tasks: 1",
            "    - openstack:ubuntu-24.04-64:tests/spread/core24/foo",
        ]
    )
    root = convert(log)
    suite = _suite(root)
    assert suite.get("tests") == "1"
    assert suite.get("failures") == "1"
    with pytest.raises(AssertionError):
        _case(root, "tests/spread/core24/fake")


def test_log_without_timestamp_prefixes_still_parses():
    log = (
        "Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...\n"
        "Successful tasks: 1\n"
        "Aborted tasks: 0"
    )
    root = convert(log)
    assert _suite(root).get("tests") == "1"


# endregion

# region failure shapes


def test_inline_error_message_without_block():
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:10 Error executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1) : LXDError: Failed to start container",
            f"{TS}0:20 Successful tasks: 0",
            f"{TS}0:20 Aborted tasks: 0",
            f"{TS}0:20 Failed tasks: 1",
            "    - openstack:ubuntu-24.04-64:tests/spread/core24/foo",
        ]
    )
    failure = _failure(_case(convert(log), "tests/spread/core24/foo"))
    assert failure.get("message") == "LXDError: Failed to start container"


def test_prepare_failure_is_a_synthetic_failing_testcase():
    log = "\n".join(
        [
            f"{TS}0:00 Preparing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:10 Error preparing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1) : boom",
            f"{TS}0:20 Successful tasks: 0",
            f"{TS}0:20 Aborted tasks: 1",
            f"{TS}0:20 Failed task prepare: 1",
            "    - openstack:ubuntu-24.04-64:tests/spread/core24/foo",
        ]
    )
    root = convert(log)
    assert _suite(root).get("failures") == "1"
    assert _suite(root).get("skipped") == "1"
    failed = _case(root, "preparing:tests/spread/core24/foo")
    assert _failure(failed).get("message") == "boom"
    # The task never ran, so there is no executing testcase for it.
    with pytest.raises(AssertionError):
        _case(root, "tests/spread/core24/foo")


def test_environment_prepare_failure_is_a_synthetic_failing_testcase():
    # A whole backend:system preparation can fail; its context has no
    # suite/task part and spread lists it under its own summary category.
    log = "\n".join(
        [
            f"{TS}0:00 Preparing openstack:ubuntu-24.04-64 (worker-1)...",
            f"{TS}0:10 Error preparing openstack:ubuntu-24.04-64 (worker-1) : ",
            "-----",
            "+ . /snapcraft/tests/spread/tools/prepare.sh",
            "-----",
            ".",
            f"{TS}0:20 Successful tasks: 0",
            f"{TS}0:20 Aborted tasks: 1",
            f"{TS}0:20 Failed project prepare: 1",
            "    - openstack:ubuntu-24.04-64:project",
        ]
    )
    root = convert(log)
    suite = _suite(root)
    assert suite.get("failures") == "1"
    assert suite.get("skipped") == "1"
    failed = _case(root, "preparing:openstack:ubuntu-24.04-64")
    assert failed.get("classname") == "openstack:ubuntu-24.04-64"
    assert (
        _failure(failed).get("message")
        == "+ . /snapcraft/tests/spread/tools/prepare.sh"
    )


# endregion

# region summary cross-check


def test_aborted_tasks_become_skipped_testcases():
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:10 Successful tasks: 1",
            f"{TS}0:10 Aborted tasks: 2",
        ]
    )
    root = convert(log)
    suite = _suite(root)
    assert suite.get("tests") == "3"
    assert suite.get("skipped") == "2"
    assert suite.get("failures") == "0"
    for number in (1, 2):
        skipped = _case(root, f"aborted-task-{number}")
        assert _message(skipped, "skipped").startswith(
            "the environment (backend/suite/project prepare or restore)"
        )


def test_unattributed_summary_failures_become_synthetic_failures():
    # Summary claims two failures but only one Error line is present. The
    # second failure is named from the summary list; an unattributed failure
    # beyond the listed names falls back to a synthetic name.
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:10 Error executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1) : boom",
            f"{TS}0:20 Successful tasks: 0",
            f"{TS}0:20 Aborted tasks: 0",
            f"{TS}0:20 Failed tasks: 3",
            "    - openstack:ubuntu-24.04-64:tests/spread/core24/foo",
            "    - openstack:ubuntu-24.04-64:tests/spread/core24/bar",
        ]
    )
    root = convert(log)
    assert _suite(root).get("failures") == "3"
    named = _case(root, "tests/spread/core24/bar", "openstack:ubuntu-24.04-64")
    assert _message(named, "failure").startswith("spread reported this failure")
    unparsed = _case(root, "unattributed-failure-2")
    assert _message(unparsed, "failure").startswith("spread reported more failures")


def test_summary_failure_names_are_matched_against_error_contexts():
    # A project prepare error's context ('backend:system') prefixes the
    # summary name ('backend:system:project'), so it counts as attributed.
    log = "\n".join(
        [
            f"{TS}0:00 Error preparing openstack:ubuntu-24.04-64 (worker-1) : no space",
            f"{TS}0:20 Successful tasks: 0",
            f"{TS}0:20 Aborted tasks: 0",
            f"{TS}0:20 Failed project prepare: 1",
            "    - openstack:ubuntu-24.04-64:project",
        ]
    )
    root = convert(log)
    assert _suite(root).get("failures") == "1"
    assert _suite(root).get("skipped") == "0"
    _case(root, "preparing:openstack:ubuntu-24.04-64", "openstack:ubuntu-24.04-64")


def test_started_tasks_without_a_verdict_become_skipped_not_passed():
    # spread was killed after starting three tasks but only recorded two
    # successful ones; the newest must not be reported as a pass.
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/first (worker-1)...",
            f"{TS}0:10 Executing openstack:ubuntu-24.04-64:tests/spread/core24/second (worker-1)...",
            f"{TS}0:20 Executing openstack:ubuntu-24.04-64:tests/spread/core24/third (worker-1)...",
            f"{TS}0:30 Successful tasks: 2",
            f"{TS}0:30 Aborted tasks: 0",
        ]
    )
    root = convert(log)
    suite = _suite(root)
    assert suite.get("tests") == "3"
    assert suite.get("failures") == "0"
    assert suite.get("skipped") == "1"
    _case(root, "tests/spread/core24/first")
    _case(root, "tests/spread/core24/second")
    incomplete = _case(root, "tests/spread/core24/third")
    assert _message(incomplete, "skipped").startswith("spread ended without a verdict")


def test_named_summary_failure_replaces_the_pending_pass():
    # The summary names a failure whose Error line was lost; the task's
    # pending pass must become the failure, not sit beside a synthetic case.
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:30 Restoring openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}1:00 Successful tasks: 0",
            f"{TS}1:00 Aborted tasks: 0",
            f"{TS}1:00 Failed tasks: 1",
            "    - openstack:ubuntu-24.04-64:tests/spread/core24/foo",
        ]
    )
    root = convert(log)
    suite = _suite(root)
    assert suite.get("tests") == "1"
    assert suite.get("failures") == "1"
    assert suite.get("skipped") == "0"
    failed = _case(root, "tests/spread/core24/foo", "openstack:ubuntu-24.04-64")
    assert "no error detail" in _message(failed, "failure")


def test_summary_demotion_prefers_completion_evidence_over_start_order():
    # Worker-1's long task started first and never restored; worker-2's task
    # started later but completed. The summary's single success must keep the
    # completed task, not the most recently started one.
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/long (worker-1)...",
            f"{TS}0:10 Executing openstack:ubuntu-24.04-64:tests/spread/core24/short (worker-2)...",
            f"{TS}0:30 Restoring openstack:ubuntu-24.04-64:tests/spread/core24/short (worker-2)...",
            f"{TS}1:00 Successful tasks: 1",
            f"{TS}1:00 Aborted tasks: 0",
        ]
    )
    root = convert(log)
    suite = _suite(root)
    assert suite.get("tests") == "2"
    assert suite.get("failures") == "0"
    assert suite.get("skipped") == "1"
    passed = _case(root, "tests/spread/core24/short", "openstack:ubuntu-24.04-64")
    assert passed.find("skipped") is None
    incomplete = _case(root, "tests/spread/core24/long", "openstack:ubuntu-24.04-64")
    assert _message(incomplete, "skipped").startswith("spread ended without a verdict")


# endregion

# region unparseable output


def test_garbage_log_with_nonzero_exit_becomes_a_failure_testcase():
    root = convert("completely unrecognizable output\n", exit_code=1)
    suite = _suite(root)
    assert suite.get("tests") == "1"
    assert suite.get("failures") == "1"
    assert _case(root, "unparsed-spread-output").find("failure") is not None


def test_garbage_log_with_zero_exit_stays_empty():
    root = convert("completely unrecognizable output\n", exit_code=0)
    assert _suite(root).get("tests") == "0"


def test_empty_log_is_an_empty_suite():
    root = convert("", exit_code=0)
    assert _suite(root).get("tests") == "0"


def test_errors_without_a_summary_are_kept():
    # A killed spread run never prints its summary, but real Error lines
    # are still real failures.
    log = f"{TS}0:10 Error executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1) : boom"
    root = convert(log, exit_code=1)
    assert _suite(root).get("failures") == "1"
    _case(root, "tests/spread/core24/foo")


def test_killed_run_without_summary_demotes_in_flight_task():
    # spread was killed mid-task: the completed task (which reached its
    # restoring line) stays a pass; the in-flight one never got a verdict.
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/first (worker-1)...",
            f"{TS}0:10 Restoring openstack:ubuntu-24.04-64:tests/spread/core24/first (worker-1)...",
            f"{TS}0:20 Executing openstack:ubuntu-24.04-64:tests/spread/core24/second (worker-1)...",
        ]
    )
    root = convert(log, exit_code=1)
    suite = _suite(root)
    assert suite.get("tests") == "2"
    assert suite.get("failures") == "0"
    assert suite.get("skipped") == "1"
    passed = _case(root, "tests/spread/core24/first", "openstack:ubuntu-24.04-64")
    assert passed.find("skipped") is None
    incomplete = _case(root, "tests/spread/core24/second", "openstack:ubuntu-24.04-64")
    assert _message(incomplete, "skipped").startswith("spread ended without a verdict")


def test_truncated_log_with_zero_exit_keeps_passes():
    # A zero exit means spread finished; a missing summary is a log artifact,
    # so started tasks are still reported as passes.
    log = f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)..."
    root = convert(log, exit_code=0)
    suite = _suite(root)
    assert suite.get("tests") == "1"
    assert suite.get("skipped") == "0"
    _case(root, "tests/spread/core24/foo", "openstack:ubuntu-24.04-64")


# endregion

# region robustness


def test_impossible_timestamp_does_not_crash():
    # Task output can mimic a control line but carry impossible values; the
    # converter must degrade to an undated event instead of raising.
    log = "9999-99-99 99:99:99 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...\n"
    root = convert(log)
    assert _suite(root).get("tests") == "1"


def test_control_characters_are_stripped_from_xml():
    log = (
        "Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...\n"
        "Error executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1) : "
        "boom \x1b[31mred\x1b[0m and \x00 null\n"
    )
    root = convert(log, exit_code=1)
    message = _message(_case(root, "tests/spread/core24/foo"), "failure")
    assert "\x1b" not in message and "\x00" not in message
    assert "boom" in message


# endregion

# region structure and CLI


def test_junit_document_is_well_formed_with_counts():
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:10 Error executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1) : boom",
            f"{TS}0:20 Successful tasks: 0",
            f"{TS}0:20 Aborted tasks: 1",
            f"{TS}0:20 Failed tasks: 1",
        ]
    )
    root = convert(log, suite_name="spread-manual")
    assert root.tag == "testsuites"
    assert root.get("name") == "spread-manual"
    suite = _suite(root)
    assert suite.get("name") == "spread-manual"
    for attribute in ("tests", "failures", "errors", "skipped", "time"):
        assert suite.get(attribute) == root.get(attribute)


def test_total_time_sums_task_durations():
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:10 Executing openstack:ubuntu-24.04-64:tests/spread/core24/bar (worker-1)...",
            f"{TS}0:25 Successful tasks: 2",
            f"{TS}0:25 Aborted tasks: 0",
        ]
    )
    suite = _suite(convert(log))
    # 10s + 15s
    assert suite.get("time") == "25.000"


def test_cli_writes_junit_xml(tmp_path):
    logfile = tmp_path / "spread.log"
    logfile.write_text(
        f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...\n"
        f"{TS}0:10 Successful tasks: 1\n"
        f"{TS}0:10 Aborted tasks: 0\n",
        encoding="utf-8",
    )
    output = tmp_path / "results" / "junit.xml"
    assert (
        main(
            [
                "--log-file",
                str(logfile),
                "--junit-file",
                str(output),
                "--exit-code",
                "0",
            ]
        )
        == 0
    )
    root = ET.parse(output).getroot()
    assert root.tag == "testsuites"
    assert _suite(root).get("tests") == "1"


def test_dataclass_fields_are_stable():
    # Guards against accidental changes to the public record shapes.
    case = TestCase(classname="c", name="n", outcome="passed")
    assert (case.classname, case.name, case.outcome) == ("c", "n", "passed")
    log = parse_log("")
    assert log.starts == [] and log.errors == [] and not log.has_summary


# endregion

# region error blocks


def test_error_block_with_literal_delimiter_is_not_terminated_early():
    # Task output can contain "-----" lines and text mimicking control lines;
    # the block only ends at "-----" followed by the bare "." terminator.
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:10 Error executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1) : ",
            "-----",
            "before the fake delimiter",
            "-----",
            f"{TS}9:99 Executing fake:backend:fake/task (fake-label) (1/1)...",
            f"{TS}9:99 Error executing fake:backend:fake/task (fake-label) : phantom failure",
            f"{TS}9:99 Successful tasks: 999",
            "-----",
            "tail of real stderr",
            "-----",
            ".",
            f"{TS}0:20 Successful tasks: 0",
            f"{TS}0:20 Aborted tasks: 0",
            f"{TS}0:20 Failed tasks: 1",
            "    - openstack:ubuntu-24.04-64:tests/spread/core24/foo",
        ]
    )
    root = convert(log)
    suite = _suite(root)
    # Exactly one task outcome; the fake control lines must not become cases
    # and the fake summary counts must not be picked up.
    assert suite.get("tests") == "1"
    assert suite.get("failures") == "1"
    failure = _failure(_case(root, "tests/spread/core24/foo"))
    assert failure.text is not None
    assert "phantom failure" in failure.text
    assert "tail of real stderr" in failure.text


def test_unclosed_error_block_runs_to_end_of_log():
    # A log truncated mid-block has no terminator; the block consumes the rest.
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:10 Error executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1) : ",
            "-----",
            "output line",
            "-----",
            "more output after a stray delimiter",
        ]
    )
    root = convert(log)
    failure = _failure(_case(root, "tests/spread/core24/foo"))
    assert failure.text is not None
    assert "more output after a stray delimiter" in failure.text


def test_debug_output_blocks_are_skipped():
    # After a task failure, spread runs the task's debug script and logs its
    # output in a "-----"-wrapped block; its contents must not be parsed.
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:10 Error executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1) : boom",
            f"{TS}0:11 Debug output for openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1) : ",
            "-----",
            "debug output line",
            "-----",
            f"{TS}9:99 Executing fake:backend:fake/task (fake-label) (1/1)...",
            "-----",
            ".",
            f"{TS}0:12 Error debugging openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1) : ",
            "-----",
            f"{TS}9:99 Error executing fake:backend:fake/task2 (fake-label) : phantom from debug",
            "-----",
            ".",
            f"{TS}0:20 Successful tasks: 0",
            f"{TS}0:20 Aborted tasks: 0",
            f"{TS}0:20 Failed tasks: 1",
            "    - openstack:ubuntu-24.04-64:tests/spread/core24/foo",
        ]
    )
    root = convert(log)
    suite = _suite(root)
    assert suite.get("tests") == "1"
    assert suite.get("failures") == "1"
    assert _case(root, "tests/spread/core24/foo").find("failure") is not None


def test_late_task_warning_output_is_not_parsed_as_control_lines():
    # A 'running late' warning dumps recent task output in a "-----"-wrapped
    # block; control-looking lines inside must not become phantom results,
    # but are kept as info on the owning task.
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}5:00 WARNING: openstack:ubuntu-24.04-64:tests/spread/core24/foo running late. Current output:",
            "-----",
            "Executing openstack:ubuntu-24.04-64:tests/spread/core24/phantom (worker-9)...",
            "Error executing openstack:ubuntu-24.04-64:tests/spread/core24/phantom (worker-9) : fake",
            "-----",
            f"{TS}6:00 Restoring openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}6:10 Successful tasks: 1",
            f"{TS}6:10 Aborted tasks: 0",
        ]
    )
    root = convert(log)
    suite = _suite(root)
    assert suite.get("tests") == "1"
    assert suite.get("failures") == "0"
    case = _case(root, "tests/spread/core24/foo", "openstack:ubuntu-24.04-64")
    system_out = case.find("system-out")
    assert system_out is not None and system_out.text is not None
    assert "running late" in system_out.text
    assert "core24/phantom" in system_out.text


def test_late_warning_without_output_block_still_marks_the_task():
    # The 'Output unchanged.' variant carries no block but still marks the
    # task as slow.
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}5:00 WARNING: openstack:ubuntu-24.04-64:tests/spread/core24/foo running late. Output unchanged.",
            f"{TS}6:00 Restoring openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}6:10 Successful tasks: 1",
            f"{TS}6:10 Aborted tasks: 0",
        ]
    )
    root = convert(log)
    assert _suite(root).get("tests") == "1"
    case = _case(root, "tests/spread/core24/foo", "openstack:ubuntu-24.04-64")
    system_out = case.find("system-out")
    assert system_out is not None
    assert system_out.text == "spread reported this task as running late"


def test_late_warning_is_attached_to_every_repetition():
    # Repeats share one context and the warning carries no worker label, so
    # every occurrence of the task carries the slowness info.
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:10 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}5:00 WARNING: openstack:ubuntu-24.04-64:tests/spread/core24/foo running late. Output unchanged.",
            f"{TS}6:10 Successful tasks: 2",
            f"{TS}6:10 Aborted tasks: 0",
        ]
    )
    root = convert(log)
    assert _suite(root).get("tests") == "2"
    for name in ("tests/spread/core24/foo", "tests/spread/core24/foo#2"):
        case = _case(root, name, "openstack:ubuntu-24.04-64")
        assert case.find("system-out") is not None


def test_error_block_after_late_warning_is_still_parsed():
    # The warning block ends at its first closing delimiter; a real error
    # block that follows must still be parsed normally.
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}5:00 WARNING: openstack:ubuntu-24.04-64:tests/spread/core24/foo running late. Current output:",
            "-----",
            "task output line",
            "-----",
            f"{TS}6:00 Error executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1) : boom",
            "-----",
            "error detail",
            "-----",
            ".",
        ]
    )
    root = convert(log, exit_code=1)
    failure = _failure(_case(root, "tests/spread/core24/foo"))
    assert failure.get("message") == "boom"
    assert failure.text == "error detail"


# endregion

# region size caps


def test_error_detail_is_capped_to_head_and_tail():
    lines = [f"output line {number}" for number in range(1, 1001)]
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:10 Error executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1) : ",
            "-----",
            *lines,
            "-----",
            ".",
        ]
    )
    root = convert(log)
    failure = _failure(_case(root, "tests/spread/core24/foo"))
    text = failure.text
    assert text is not None
    assert "output line 1" in text
    assert "output line 50" in text
    assert "output line 51" not in text
    assert "... [750 lines elided] ..." in text
    assert "output line 1000" in text
    assert "output line 801" in text
    assert "output line 800" not in text


def test_very_long_lines_are_truncated():
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:10 Error executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1) : ",
            "-----",
            "X" * 20000,
            "-----",
            ".",
        ]
    )
    root = convert(log)
    failure = _failure(_case(root, "tests/spread/core24/foo"))
    assert failure.text is not None
    assert len(failure.text) < 2100
    assert failure.text.endswith("... [line truncated]")


def test_error_message_is_capped():
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:10 Error executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1) : {'Y' * 2000}",
        ]
    )
    root = convert(log)
    failure = _failure(_case(root, "tests/spread/core24/foo"))
    message = failure.get("message")
    assert message is not None
    assert len(message) == 512 + len(" ... [truncated]")


# endregion

# region expected jobs


def test_expected_jobs_never_started_become_named_skipped_cases():
    log = "\n".join(
        [
            f"{TS}0:00 Error preparing openstack:ubuntu-24.04-64 (worker-1) : no space",
            f"{TS}0:20 Successful tasks: 0",
            f"{TS}0:20 Aborted tasks: 2",
            f"{TS}0:20 Failed project prepare: 1",
            "    - openstack:ubuntu-24.04-64:project",
        ]
    )
    expected = frozenset(
        {
            "openstack:ubuntu-24.04-64:tests/spread/core24/foo",
            "openstack:ubuntu-24.04-64:tests/spread/core24/bar:variant",
        }
    )
    root = convert(log, expected_jobs=expected)
    suite = _suite(root)
    assert suite.get("failures") == "1"
    # Both expected tasks are named; no synthetic aborted-task cases remain.
    assert suite.get("skipped") == "2"
    assert (
        _case(root, "tests/spread/core24/foo", "openstack:ubuntu-24.04-64") is not None
    )
    assert (
        _case(root, "tests/spread/core24/bar:variant", "openstack:ubuntu-24.04-64")
        is not None
    )
    assert _message(_case(root, "tests/spread/core24/foo"), "skipped").startswith(
        "expected by 'spread -list'"
    )


def test_expected_job_sample_suffixes_are_stripped_for_matching():
    log = "\n".join(
        [
            f"{TS}0:00 Error preparing openstack:ubuntu-24.04-64 (worker-1) : no space",
            f"{TS}0:20 Successful tasks: 0",
            f"{TS}0:20 Aborted tasks: 1",
        ]
    )
    expected = frozenset({"openstack:ubuntu-24.04-64:tests/spread/core24/foo#1..3"})
    root = convert(log, expected_jobs=expected)
    # The sample range collapses to one context; the aborted count is covered
    # by the named never-started case.
    assert _suite(root).get("skipped") == "1"
    _case(root, "tests/spread/core24/foo", "openstack:ubuntu-24.04-64")


def test_expected_jobs_started_tasks_are_not_reported_as_never_started():
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:10 Successful tasks: 1",
            f"{TS}0:10 Aborted tasks: 0",
        ]
    )
    expected = frozenset({"openstack:ubuntu-24.04-64:tests/spread/core24/foo"})
    root = convert(log, expected_jobs=expected)
    suite = _suite(root)
    assert suite.get("tests") == "1"
    assert suite.get("skipped") == "0"


def test_sampled_job_in_log_and_list_is_not_reported_never_started():
    # Sampled jobs carry a '#N' suffix in the log; the '-list' name without
    # the suffix must still count as started.
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo#1 (worker-1)...",
            f"{TS}0:10 Restoring openstack:ubuntu-24.04-64:tests/spread/core24/foo#1 (worker-1)...",
            f"{TS}0:20 Successful tasks: 1",
            f"{TS}0:20 Aborted tasks: 0",
        ]
    )
    expected = frozenset({"openstack:ubuntu-24.04-64:tests/spread/core24/foo"})
    root = convert(log, expected_jobs=expected)
    suite = _suite(root)
    assert suite.get("tests") == "1"
    assert suite.get("skipped") == "0"
    _case(root, "tests/spread/core24/foo#1", "openstack:ubuntu-24.04-64")


def test_cli_passes_expected_jobs(tmp_path):
    logfile = tmp_path / "spread.log"
    logfile.write_text(
        f"{TS}0:00 Error preparing openstack:ubuntu-24.04-64 (worker-1) : no space\n"
        f"{TS}0:20 Successful tasks: 0\n"
        f"{TS}0:20 Aborted tasks: 1\n",
        encoding="utf-8",
    )
    output = tmp_path / "results" / "junit.xml"
    assert (
        main(
            [
                "--log-file",
                str(logfile),
                "--junit-file",
                str(output),
                "--expected-jobs",
                "openstack:ubuntu-24.04-64:tests/spread/core24/foo#2",
            ]
        )
        == 0
    )
    root = ET.parse(output).getroot()
    assert _suite(root).get("skipped") == "1"
    _case(root, "tests/spread/core24/foo", "openstack:ubuntu-24.04-64")


def test_cli_passes_empty_expected_jobs(tmp_path):
    logfile = tmp_path / "spread.log"
    logfile.write_text(
        f"{TS}0:00 Error preparing openstack:ubuntu-24.04-64 (worker-1) : no space\n"
        f"{TS}0:20 Successful tasks: 0\n"
        f"{TS}0:20 Aborted tasks: 1\n",
        encoding="utf-8",
    )
    output = tmp_path / "results" / "junit.xml"
    assert (
        main(
            [
                "--log-file",
                str(logfile),
                "--junit-file",
                str(output),
                "--expected-jobs",
            ]
        )
        == 0
    )
    root = ET.parse(output).getroot()
    assert _suite(root).get("skipped") == "1"
    _case(root, "aborted-task-1", "spread")


# endregion

# region duplicates


def test_duplicate_testcases_are_suffixed():
    # '-repeat' (or samples sharing one log context) produces identical
    # control lines; repeats must stay distinct for JUnit consumers.
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:05 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:10 Successful tasks: 2",
            f"{TS}0:10 Aborted tasks: 0",
        ]
    )
    root = convert(log)
    suite = _suite(root)
    assert suite.get("tests") == "2"
    _case(root, "tests/spread/core24/foo", "openstack:ubuntu-24.04-64")
    _case(root, "tests/spread/core24/foo#2", "openstack:ubuntu-24.04-64")


def test_repeated_task_failure_does_not_fail_its_sibling():
    # Two repetitions of one task share a context and label; only the first
    # errored, so the second must not inherit the failure.
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:10 Error executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1) : boom",
            f"{TS}0:20 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:30 Restoring openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:40 Successful tasks: 1",
            f"{TS}0:40 Aborted tasks: 0",
            f"{TS}0:40 Failed tasks: 1",
            "    - openstack:ubuntu-24.04-64:tests/spread/core24/foo",
        ]
    )
    root = convert(log)
    suite = _suite(root)
    assert suite.get("tests") == "2"
    assert suite.get("failures") == "1"
    failed = _case(root, "tests/spread/core24/foo", "openstack:ubuntu-24.04-64")
    assert _message(failed, "failure") == "boom"
    passed = _case(root, "tests/spread/core24/foo#2", "openstack:ubuntu-24.04-64")
    assert passed.find("failure") is None and passed.find("skipped") is None


def test_error_is_matched_to_the_start_with_its_own_label():
    # Parallel repetitions run under different worker labels; the error must
    # fail the occurrence whose label it carries, not the first one. The
    # duration (0:05 -> 0:10) proves the second start was matched.
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:05 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-2)...",
            f"{TS}0:10 Error executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-2) : boom",
            f"{TS}0:20 Restoring openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:30 Successful tasks: 1",
            f"{TS}0:30 Aborted tasks: 0",
            f"{TS}0:30 Failed tasks: 1",
            "    - openstack:ubuntu-24.04-64:tests/spread/core24/foo",
        ]
    )
    root = convert(log)
    suite = _suite(root)
    assert suite.get("tests") == "2"
    assert suite.get("failures") == "1"
    failed = _case(root, "tests/spread/core24/foo", "openstack:ubuntu-24.04-64")
    assert _message(failed, "failure") == "boom"
    assert failed.get("time") == "5.000"
    passed = _case(root, "tests/spread/core24/foo#2", "openstack:ubuntu-24.04-64")
    assert passed.find("failure") is None and passed.find("skipped") is None


def test_pass_then_fail_repetition_is_attributed_to_the_failed_start():
    # The first repetition completed (restoring line) before the second one
    # failed; the failure must land on the second start, with its duration.
    log = "\n".join(
        [
            f"{TS}0:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}0:30 Restoring openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}1:00 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1)...",
            f"{TS}1:20 Error executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (worker-1) : boom",
            f"{TS}1:30 Successful tasks: 1",
            f"{TS}1:30 Aborted tasks: 0",
            f"{TS}1:30 Failed tasks: 1",
            "    - openstack:ubuntu-24.04-64:tests/spread/core24/foo",
        ]
    )
    root = convert(log)
    suite = _suite(root)
    assert suite.get("tests") == "2"
    assert suite.get("failures") == "1"
    assert suite.get("skipped") == "0"
    failed = _case(root, "tests/spread/core24/foo", "openstack:ubuntu-24.04-64")
    assert _message(failed, "failure") == "boom"
    # Duration from the second start (1:00), not the first (0:00).
    assert failed.get("time") == "20.000"
    passed = _case(root, "tests/spread/core24/foo#2", "openstack:ubuntu-24.04-64")
    assert passed.find("failure") is None and passed.find("skipped") is None


# endregion

# region fixtures


@pytest.mark.parametrize(
    ("fixture", "exit_code", "tests", "failures", "skipped"),
    [
        # A clean run: every executed task passes.
        ("spread-pass.log", 0, "2", "0", "0"),
        # A failing run: one task fails, one environment prepare fails (and is
        # reported as its own synthetic failure), and one task is aborted.
        ("spread-fail.log", 1, "4", "2", "1"),
    ],
)
def test_fixture_logs(
    fixture: str, exit_code: int, tests: str, failures: str, skipped: str
):
    text = (FIXTURES / fixture).read_text(encoding="utf-8")
    suite = _suite(convert(text, exit_code=exit_code))
    assert suite.get("tests") == tests
    assert suite.get("failures") == failures
    assert suite.get("skipped") == skipped


def test_fixture_log_with_expected_jobs_names_the_aborted_task():
    # The '-list' fixture pairs with spread-fail.log: the job that never
    # started is reported under its real name instead of a synthetic one.
    text = (FIXTURES / "spread-fail.log").read_text(encoding="utf-8")
    expected = frozenset(
        (FIXTURES / "spread-fail-list.log").read_text(encoding="utf-8").split()
    )
    root = convert(text, exit_code=1, expected_jobs=expected)
    suite = _suite(root)
    assert suite.get("tests") == "4"
    assert suite.get("failures") == "2"
    assert suite.get("skipped") == "1"
    skipped_case = _case(
        root, "tests/spread/core26/aborted:default", "openstack:ubuntu-26.04-64"
    )
    assert _message(skipped_case, "skipped").startswith("expected by 'spread -list'")

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    expected_xml = (FIXTURES / "spread-fail-junit.xml").read_text(encoding="utf-8")
    actual_xml = (
        "<?xml version='1.0' encoding='utf-8'?>\n"
        + ET.tostring(root, encoding="unicode")
        + "\n"
    )
    assert actual_xml == expected_xml


# endregion
