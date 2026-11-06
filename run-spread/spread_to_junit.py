#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Convert a spread run log into a JUnit XML result file.

This converter collects all test results and errors from spread and converts them into
a standard JUnit XML result file.

Built against spread version 2026.07.12-g052d7a1.

Usage:

    spread_to_junit.py --log-file LOGFILE --junit-file OUTPUT
                       [--exit-code CODE] [--suite-name NAME]
                       [--expected-jobs JOBS...]
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import ClassVar, Literal, NamedTuple

__all__ = ["TestCase", "convert", "main", "parse_log"]

# A JUnit test case outcome.
Outcome = Literal["passed", "failed", "skipped"]

# Classname for synthetic test cases that cannot be tied to a spread task.
_SPREAD_CLASSNAME = "spread"

# Matches an optional YYYY-MM-DD HH:MM:SS timestamp prefix.
_TIMESTAMP = r"(?:(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+)?"

# Matches '2026-10-28 20:07:10 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (oct282007-149679) (2/5)...'
_START_RE = re.compile(
    rf"^{_TIMESTAMP}(?P<verb>Executing|Preparing|Restoring) "
    r"(?P<ctx>\S+) \((?P<label>[^()]*)\)(?: \((?P<seq>\d+/\d+)\))?\.\.\.$"
)

# Matches '2026-10-28 20:07:10 Error executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (oct282007-149679) : some failure message'
_ERROR_RE = re.compile(
    rf"^{_TIMESTAMP}Error (?P<verb>executing|preparing|restoring) "
    r"(?P<ctx>\S+) \((?P<label>[^()]*)\) : ?(?P<msg>.*)$"
)

# Matches debug outputs, such as:
# 2026-10-28 20:07:10 Debug output for openstack:ubuntu-24.04-64:tests/spread/core24/foo (oct282007-149679) : ...
# 2026-10-28 20:07:10 Error debugging openstack:ubuntu-24.04-64:tests/spread/core24/foo (oct282007-149679) : ...
_DEBUG_RE = re.compile(
    rf"^{_TIMESTAMP}(?:Debug output for|Error debugging) (?P<ctx>\S+) "
    r"\((?P<label>[^()]*)\) : ?(?P<msg>.*)$"
)

# Matches late-task warnings that dump recent task output, such as:
# 2026-10-28 20:07:10 WARNING: openstack:ubuntu-24.04-64:tests/spread/core24/foo running late. Current output:
# 2026-10-28 20:07:10 WARNING: openstack:ubuntu-24.04-64:tests/spread/core24/foo running late. Output unchanged.
# The wrapped output that follows holds arbitrary task text.
_LATE_WARNING_RE = re.compile(
    rf"^{_TIMESTAMP}WARNING: (?P<ctx>.+?) running late\. "
    r"(?P<kind>Current output:|Output unchanged\.|Output still empty\.)$"
)

# Matches final summary lines, such as:
#   2026-10-28 20:07:10 Successful tasks: 41
#   2026-10-28 20:07:10 Aborted tasks: 2
#   2026-10-28 20:07:10 Failed tasks: 1
#   2026-10-28 20:07:10 Failed project prepare: 1
_SUMMARY_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+"
    r"(?P<cat>Successful tasks|Aborted tasks|Failed [^:]*): (?P<count>\d+)$"
)
# Matches final summary items, such as:
#   2026-10-28 20:07:10 Failed tasks: 1
#       - openstack:ubuntu-24.04-64:tests/spread/core24/foo
_LIST_ITEM_RE = re.compile(r"^    - (?P<name>.+)$")

# Multi-line error messages are delimited by "-----" lines and followed by a bare "." line.
_DELIM = "-----"

# Caps error details and message text, as spread errors can be thousands of lines.
_DETAIL_HEAD_LINES = 50
_DETAIL_TAIL_LINES = 200
_DETAIL_LINE_MAX_CHARS = 2000
_MESSAGE_MAX_CHARS = 512

# Characters that are not legal in an XML 1.0 document, such as ANSI escape
# sequences and NUL bytes that can appear in raw task output.
_XML_INVALID_RE = re.compile(
    "[^\u0009\u000a\u000d\u0020-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]"
)


def _xml_safe(text: str) -> str:
    """Strip characters that would make the JUnit document malformed."""
    return _XML_INVALID_RE.sub("", text)


def _cap_message(text: str | None) -> str | None:
    """Cap the message length, which lands in an XML attribute."""
    if text and len(text) > _MESSAGE_MAX_CHARS:
        return text[:_MESSAGE_MAX_CHARS] + " ... [truncated]"
    return text


def _cap_detail(lines: list[str]) -> str | None:
    """Cap a block of task output: truncate long lines, keep head and tail."""
    capped = []
    for line in lines:
        if len(line) > _DETAIL_LINE_MAX_CHARS:
            line = line[:_DETAIL_LINE_MAX_CHARS] + " ... [line truncated]"
        capped.append(line)
    if not capped:
        return None
    if len(capped) <= _DETAIL_HEAD_LINES + _DETAIL_TAIL_LINES:
        return "\n".join(capped)
    elided = len(capped) - _DETAIL_HEAD_LINES - _DETAIL_TAIL_LINES
    head = capped[:_DETAIL_HEAD_LINES]
    tail = capped[-_DETAIL_TAIL_LINES:]
    return "\n".join([*head, f"... [{elided} lines elided] ...", *tail])


@dataclass(frozen=True, slots=True)
class StartEvent:
    """A "<verb> <ctx> (<label>)..." control line, such as:

    '2026-10-28 20:07:10 Executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (oct282007-149679) (2/5)...'
    """

    verb: str
    ctx: str
    label: str
    ts: datetime | None
    seq: str | None
    line: int


@dataclass(frozen=True, slots=True)
class ErrorEvent:
    """An "Error <verb> <ctx> (<label>) : <message>" control line, such as:

    '2026-10-28 20:07:10 Error executing openstack:ubuntu-24.04-64:tests/spread/core24/foo (oct282007-149679) : some failure message'
    """

    verb: str
    ctx: str
    label: str
    ts: datetime | None
    message: str | None
    detail: str | None
    line: int


@dataclass(frozen=True, slots=True)
class WarningEvent:
    """A "WARNING: <job> running late..." control line, such as:

    '2026-10-28 20:07:10 WARNING: openstack:ubuntu-24.04-64:tests/spread/core24/foo running late. Current output:'
    """

    ctx: str
    ts: datetime | None
    text: str | None
    line: int


@dataclass(slots=True)
class Summary:
    """The counts (and, where available, names) from the final summary.

    2026-10-28 20:07:10 Successful tasks: 41
    2026-10-28 20:07:10 Aborted tasks: 2
    2026-10-28 20:07:10 Failed tasks: 1
        - openstack:ubuntu-24.04-64:tests/spread/core24/foo
    """

    ts: datetime | None = None
    successful: int | None = None
    aborted: int | None = None
    failed: dict[str, int] = field(default_factory=dict)
    failed_names: dict[str, list[str]] = field(default_factory=dict)

    @property
    def failure_count(self) -> int:
        return sum(self.failed.values())


@dataclass(slots=True)
class Log:
    """Everything reconstructable from a spread log."""

    starts: list[StartEvent] = field(default_factory=list)
    errors: list[ErrorEvent] = field(default_factory=list)
    warnings: list[WarningEvent] = field(default_factory=list)
    summary: Summary = field(default_factory=Summary)
    has_summary: bool = False


@dataclass(frozen=True, slots=True)
class TestCase:
    """A JUnit test case."""

    # Not a pytest test class, despite the name.
    __test__: ClassVar[bool] = False

    classname: str
    name: str
    outcome: Outcome
    duration: float = 0.0
    message: str | None = None
    detail: str | None = None
    system_out: str | None = None


def _parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        # Task output can mimic control lines but holds arbitrary text, such
        # as impossible timestamps; treat those as undated.
        return None


def _extract_error_block(lines: list[str], index: int) -> tuple[str | None, int]:
    """Collect the "-----"-wrapped multi-line block after an error line.

    Error blocks start with a "-----" line and end with a "-----" line followed by a
    "." line. If no end lines are found, the block will run to the end of the log.

    Returns the block text (or None) and the index of the first line past the block,
    so callers can skip the block contents.
    """
    if index + 1 >= len(lines) or lines[index + 1].strip() != _DELIM:
        return None, index + 1
    block: list[str] = []
    cursor = index + 2
    while cursor < len(lines):
        if lines[cursor].strip() == _DELIM:
            if cursor + 1 < len(lines) and lines[cursor + 1].strip() == ".":
                cursor += 2
                break
            block.append(lines[cursor])
            cursor += 1
            continue
        block.append(lines[cursor])
        cursor += 1
    return _cap_detail(block), cursor


def _extract_warning_block(lines: list[str], index: int) -> tuple[str | None, int]:
    """Collect the "-----"-wrapped output block after a 'running late' warning.

    Unlike error blocks, warning blocks end at the first closing "-----" line
    and carry no "." terminator. Returns the capped block text (or None) and
    the index of the first line past the block.
    """
    if index + 1 >= len(lines) or lines[index + 1].strip() != _DELIM:
        return None, index + 1
    block: list[str] = []
    cursor = index + 2
    while cursor < len(lines) and lines[cursor].strip() != _DELIM:
        block.append(lines[cursor])
        cursor += 1
    return _cap_detail(block), min(cursor + 1, len(lines))


def _summary_item_names(lines: list[str], index: int) -> list[str]:
    """Collect the '    - name' list items following a summary line."""
    names: list[str] = []
    cursor = index + 1
    while cursor < len(lines) and (item := _LIST_ITEM_RE.match(lines[cursor])):
        names.append(item.group("name").strip())
        cursor += 1
    return names


def parse_log(text: str) -> Log:
    """Parse a spread log into starts, errors, and the final summary."""
    lines = text.splitlines()
    result = Log()
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            index += 1
            continue
        if match := _START_RE.match(stripped):
            result.starts.append(
                StartEvent(
                    verb=match.group("verb").lower(),
                    ctx=match.group("ctx"),
                    label=match.group("label"),
                    ts=_parse_ts(match.group("ts")),
                    seq=match.group("seq"),
                    line=index,
                )
            )
            index += 1
            continue
        if match := _ERROR_RE.match(stripped):
            # Skip over the block contents, which hold arbitrary task output
            # that must not be parsed as control lines.
            error_line = index
            block, index = _extract_error_block(lines, index)
            inline_message = _cap_message(match.group("msg").strip() or None)
            message = inline_message
            detail = block
            if block and not inline_message:
                message = _cap_message(block.splitlines()[0])
            result.errors.append(
                ErrorEvent(
                    verb=match.group("verb"),
                    ctx=match.group("ctx"),
                    label=match.group("label"),
                    ts=_parse_ts(match.group("ts")),
                    message=message,
                    detail=detail,
                    line=error_line,
                )
            )
            continue
        if _DEBUG_RE.match(stripped):
            # Skip the debug script block.
            _block, index = _extract_error_block(lines, index)
            continue
        if match := _LATE_WARNING_RE.match(stripped):
            # Extract the wrapped task output as info for the owning task; it
            # can mimic control lines, so it must not be parsed.
            warning_line = index
            if match.group("kind") == "Current output:":
                block_text, index = _extract_warning_block(lines, index)
            else:
                block_text = None
                index += 1
            result.warnings.append(
                WarningEvent(
                    ctx=match.group("ctx"),
                    ts=_parse_ts(match.group("ts")),
                    text=block_text,
                    line=warning_line,
                )
            )
            continue
        if match := _SUMMARY_RE.match(stripped):
            category = match.group("cat")
            count = int(match.group("count"))
            if result.summary.ts is None:
                result.summary.ts = _parse_ts(match.group("ts"))
            result.has_summary = True
            if category == "Successful tasks":
                result.summary.successful = count
            elif category == "Aborted tasks":
                result.summary.aborted = count
            else:
                result.summary.failed[category] = count
                result.summary.failed_names[category] = _summary_item_names(
                    lines, index
                )
            index += 1
            continue
        index += 1
    return result


def _split_ctx(ctx: str) -> tuple[str | None, str, str | None]:
    """Split a context string into (classname, task name, variant).

    A task context is ``backend:system:suite/task[:variant]``.

    Broad contexts, like suite or environment preparation, fall back to using the whole
    string as the name with no classname.
    """
    parts = ctx.split(":")
    if len(parts) == 3 and "/" in parts[2]:
        return f"{parts[0]}:{parts[1]}", parts[2], None
    if len(parts) == 4 and "/" in parts[2]:
        return f"{parts[0]}:{parts[1]}", f"{parts[2]}:{parts[3]}", parts[3]
    return None, ctx, None


def _strip_sample(name: str) -> str:
    """Drop the "#N" (or "#N..M") sample suffix from a 'spread -list' job name."""
    return re.sub(r"#\d+(?:\.\.\d+)?$", "", name)


def _match_errors_to_starts(log: Log) -> dict[int, int]:
    """Match executing errors to the start line of the execution they ended.

    An error belongs to the most recent still-unmatched start with the same
    (context, label) that precedes it in the log, so a repetition that passed
    keeps its pass when a later repetition fails.

    Returns a mapping of start indices to error indices into the log's lists.
    """
    starts_by_key: dict[tuple[str, str], list[int]] = {}
    for index, start in enumerate(log.starts):
        if start.verb == "executing":
            starts_by_key.setdefault((start.ctx, start.label), []).append(index)
    matches: dict[int, int] = {}
    pointers: dict[tuple[str, str], int] = {}
    for number, error in enumerate(log.errors):
        if error.verb != "executing":
            continue
        key = (error.ctx, error.label)
        candidates = starts_by_key.get(key)
        if not candidates:
            continue
        position = pointers.get(key, 0)
        while (
            position + 1 < len(candidates)
            and log.starts[candidates[position + 1]].line < error.line
        ):
            position += 1
        pointers[key] = position
        start_index = candidates[position]
        if log.starts[start_index].line < error.line:
            matches[start_index] = number
            pointers[key] = position + 1
    return matches


def _collect_control_timestamps(log: Log) -> list[datetime | None]:
    """Gather the timestamps of all control lines, in log order."""
    stamps = [start.ts for start in log.starts]
    stamps += [error.ts for error in log.errors]
    if log.has_summary and log.summary.ts is not None:
        stamps.append(log.summary.ts)
    return stamps


class _PassedTask(NamedTuple):
    """A task that started, never errored, and awaits a verdict."""

    classname: str
    name: str
    duration: float
    key: tuple[str, str]  # (context, label) of its start line
    occurrence: int  # 0-based index among the starts sharing its key


@dataclass
class _CaseBuilder:
    """Accumulates test cases and their results from a parsed log.

    Failing and skipped cases are appended first, then passing, then failures that
    couldn't be matched to a test case from 'spread -list'.
    """

    cases: list[TestCase] = field(default_factory=list)
    passed: list[_PassedTask] = field(default_factory=list)
    restored: dict[tuple[str, str], int] = field(default_factory=dict)
    consumed_errors: set[int] = field(default_factory=set)
    started_ctxs: set[str] = field(default_factory=set)
    never_started: list[str] = field(default_factory=list)

    def record_starts(
        self,
        log: Log,
        error_matches: dict[int, int],
        control_ts: list[datetime | None],
    ) -> None:
        """Record executed tasks.

        Passing tasks become PassedTasks and errors become TestCases. Each
        error is matched to the start line of the execution it ended, so one
        failing repetition does not fail its siblings.
        """

        # Use the timestamps from spread to estimate test duration. Task output is not
        # timestamped, so the time between a task's start line and the next control
        # line is a best-effort approximation of its duration.
        def _duration_after(event_ts: datetime | None, from_index: int) -> float:
            if event_ts is None:
                return 0.0
            for later in control_ts[from_index + 1 :]:
                if later is not None and later >= event_ts:
                    return max((later - event_ts).total_seconds(), 0.0)
            return 0.0

        self.consumed_errors = set(error_matches.values())
        occurrences: dict[tuple[str, str], int] = {}
        for index, start in enumerate(log.starts):
            key = (start.ctx, start.label)
            if start.verb == "restoring":
                # A restoring line is the completion evidence for the task
                # occurrence that executed before it.
                self.restored[key] = self.restored.get(key, 0) + 1
                continue
            if start.verb != "executing":
                continue
            occurrence = occurrences.get(key, 0)
            occurrences[key] = occurrence + 1
            self.started_ctxs.add(start.ctx)
            classname, name, _variant = _split_ctx(start.ctx)
            error_number = error_matches.get(index)
            error = log.errors[error_number] if error_number is not None else None
            if error is not None:
                duration = (
                    max((error.ts - start.ts).total_seconds(), 0.0)
                    if error.ts and start.ts
                    else _duration_after(start.ts, index)
                )
                self.cases.append(
                    TestCase(
                        classname=classname or start.ctx,
                        name=name,
                        outcome="failed",
                        duration=duration,
                        message=error.message,
                        detail=error.detail or error.message,
                    )
                )
            else:
                self.passed.append(
                    _PassedTask(
                        classname or start.ctx,
                        name,
                        _duration_after(start.ts, index),
                        key,
                        occurrence,
                    )
                )

    def add_never_started_cases(self, expected_jobs: frozenset[str] | None) -> None:
        """Add skipped cases for 'spread -list' jobs that never started."""
        # They were aborted before producing an outcome, such as an environment prepare failure.
        if expected_jobs is None:
            return
        expected_jobs = frozenset(_strip_sample(name) for name in expected_jobs)
        # Sampled jobs carry a '#N' suffix in the log too; compare both sides
        # without it, or a sampled task that ran would look never-started.
        started = {_strip_sample(ctx) for ctx in self.started_ctxs}
        self.never_started = sorted(expected_jobs - started)
        for name in self.never_started:
            classname, task, _variant = _split_ctx(name)
            self.cases.append(
                TestCase(
                    classname=classname or name,
                    name=task,
                    outcome="skipped",
                    message="expected by 'spread -list' but never started",
                )
            )

    def reconcile_summary(self, log: Log, expected_jobs: frozenset[str] | None) -> None:
        """Reconcile the final summary against the parsed outcomes."""
        self._add_unattributed_failures(log)
        self._add_aborted_tasks(log, expected_jobs)
        self._demote_unverdicted_passes(log)

    def _add_unattributed_failures(self, log: Log) -> None:
        """Add placeholder cases for failures in the summary that don't have an error line."""
        attributed = [error.ctx for error in log.errors]
        uncovered: list[str] = []
        for names in log.summary.failed_names.values():
            for name in names:
                if any(name == ctx or name.startswith(ctx + ":") for ctx in attributed):
                    continue
                if name not in uncovered:
                    uncovered.append(name)
        unattributed_count = log.summary.failure_count - len(log.errors)
        for number in range(max(unattributed_count, 0)):
            if number < len(uncovered):
                name = uncovered[number]
                classname, task, _variant = _split_ctx(name)
                if self._fail_existing_case(name, classname, task):
                    continue
                self.cases.append(
                    TestCase(
                        classname=classname or name,
                        name=task,
                        outcome="failed",
                        message=(
                            "spread reported this failure but no error detail "
                            "was parsed from the log"
                        ),
                    )
                )
            else:
                self.cases.append(
                    TestCase(
                        classname=_SPREAD_CLASSNAME,
                        name=f"unattributed-failure-{number + 1}",
                        outcome="failed",
                        message=(
                            "spread reported more failures than were parsed from the log"
                        ),
                    )
                )

    def _fail_existing_case(self, name: str, classname: str | None, task: str) -> bool:
        """Turn an existing pass or never-started skip for the named execution into a failed case.

        Without this, the same execution would be reported twice, and the
        success-count reconciliation would demote a different task.
        """
        message = (
            "spread reported this failure but no error detail was parsed from the log"
        )
        for index, pending in enumerate(self.passed):
            if _strip_sample(pending.key[0]) == _strip_sample(name):
                self.passed.pop(index)
                self.cases.append(
                    TestCase(
                        classname=pending.classname,
                        name=pending.name,
                        outcome="failed",
                        message=message,
                    )
                )
                return True
        target = (classname or name, task)
        for index, case in enumerate(self.cases):
            if case.outcome == "skipped" and (case.classname, case.name) == target:
                self.cases[index] = replace(case, outcome="failed", message=message)
                return True
        return False

    def _add_aborted_tasks(
        self, log: Log, expected_jobs: frozenset[str] | None
    ) -> None:
        """Add skipped cases for tasks counted as aborted in the summary but not reported from the expected-jobs list."""
        if not log.summary.aborted:
            return
        aborted = log.summary.aborted
        if expected_jobs is not None:
            aborted = max(aborted - len(self.never_started), 0)
        for number in range(aborted):
            self.cases.append(
                TestCase(
                    classname=_SPREAD_CLASSNAME,
                    name=f"aborted-task-{number + 1}",
                    outcome="skipped",
                    message=(
                        "the environment (backend/suite/project prepare or restore) "
                        "failed before the task produced an outcome"
                    ),
                )
            )

    def _demote_unverdicted_passes(self, log: Log) -> None:
        """Demote collected passes that exceed the summary's successful count to skipped cases, for tasks spread ended without a verdict for."""
        expected_passes = (
            log.summary.successful if log.summary.successful is not None else 0
        )
        if len(self.passed) <= expected_passes:
            return
        # If a task never errored and never completed, mark it as skipped.
        surplus = len(self.passed) - expected_passes
        # Completion evidence (a restoring line) identifies unfinished tasks
        # more reliably than start order, which misleads when workers run in
        # parallel. Demote unrestored passes first; only if the summary
        # demands more, fall back to the most recently started tasks.
        unrestored = [
            index
            for index, task in enumerate(self.passed)
            if self.restored.get(task.key, 0) <= task.occurrence
        ]
        if surplus <= len(unrestored):
            demote = set(unrestored[len(unrestored) - surplus :])
        else:
            restored = [
                index
                for index in range(len(self.passed))
                if index not in set(unrestored)
            ]
            extra = surplus - len(unrestored)
            demote = set(unrestored) | set(restored[len(restored) - extra :])
        for index in sorted(demote):
            task = self.passed[index]
            self.cases.append(
                TestCase(
                    classname=task.classname,
                    name=task.name,
                    outcome="skipped",
                    message="spread ended without a verdict for this task",
                )
            )
        self.passed = [
            task for index, task in enumerate(self.passed) if index not in demote
        ]

    def demote_unrestored_passes(self) -> None:
        """Demote collected passes that never reached a restoring line to skipped cases.

        A run that dies before printing its summary leaves its in-flight tasks
        without a verdict; only tasks that reached their restoring line
        actually completed.
        """
        verdicted: list[_PassedTask] = []
        for task in self.passed:
            if self.restored.get(task.key, 0) > task.occurrence:
                verdicted.append(task)
                continue
            # If a task never errored and never completed, mark it as skipped.
            self.cases.append(
                TestCase(
                    classname=task.classname,
                    name=task.name,
                    outcome="skipped",
                    message="spread ended without a verdict for this task",
                )
            )
        self.passed = verdicted

    def add_passed(self) -> None:
        """Add a passed case for every task still holding a pass verdict."""
        for task in self.passed:
            self.cases.append(
                TestCase(
                    classname=task.classname,
                    name=task.name,
                    outcome="passed",
                    duration=task.duration,
                )
            )

    def add_unparsed_output(self, exit_code: int, log: Log) -> None:
        """Add a synthetic failure when spread fails and nothing was parsed."""
        if exit_code == 0 or log.errors or log.starts:
            return
        self.cases.append(
            TestCase(
                classname=_SPREAD_CLASSNAME,
                name="unparsed-spread-output",
                outcome="failed",
                message="spread exited nonzero but its output could not be parsed",
            )
        )

    def add_unmatched_errors(self, log: Log) -> None:
        """Add failing cases for errors that no start line consumed."""
        # A log tail that began mid-run and prepare/restore failures are not
        # ordinary task outcomes. They are reported as their own failing test cases.
        unmatched = [
            error
            for number, error in enumerate(log.errors)
            if number not in self.consumed_errors
        ]
        for error in sorted(unmatched, key=lambda error: (error.verb, error.ctx)):
            classname, name, _variant = _split_ctx(error.ctx)
            prefix = f"{error.verb}:" if error.verb != "executing" else ""
            self.cases.append(
                TestCase(
                    classname=classname or error.ctx,
                    name=f"{prefix}{name}",
                    outcome="failed",
                    message=error.message,
                    detail=error.detail or error.message,
                )
            )

    def dedupe_repeats(self) -> None:
        """Suffix repeated (classname, name) pairs to keep them distinct."""
        # Repeated jobs ('-repeat', or samples sharing one log context) produce
        # identical test case names; suffix the repeats so JUnit consumers that
        # key on (classname, name) keep them distinct.
        seen: dict[tuple[str, str], int] = {}
        for number, case in enumerate(self.cases):
            key = (case.classname, case.name)
            count = seen.get(key, 0) + 1
            seen[key] = count
            if count > 1:
                self.cases[number] = replace(case, name=f"{case.name}#{count}")

    def attach_warnings(self, log: Log) -> None:
        """Attach late-task warnings to their task cases as system output."""
        # A 'running late' warning marks a task as slow; surfacing it (and the
        # wrapped output dump) on the task's case makes slow tests visible.
        for warning in log.warnings:
            classname, name, _variant = _split_ctx(warning.ctx)
            target = _strip_sample(f"{classname}:{name}" if classname else name)
            info = "spread reported this task as running late"
            if warning.text:
                info = f"{info}:\n{warning.text}"
            for number, case in enumerate(self.cases):
                if _strip_sample(f"{case.classname}:{case.name}") != target:
                    continue
                merged = f"{case.system_out}\n{info}" if case.system_out else info
                self.cases[number] = replace(case, system_out=merged)


def build_testcases(
    log: Log, exit_code: int, expected_jobs: frozenset[str] | None = None
) -> list[TestCase]:
    """Reconstruct per-task test cases from a parsed log.

    When 'expected_jobs' holds the job names from 'spread -list', tasks that were expected
    but never started are reported as skipped test cases under their real names.
    """
    builder = _CaseBuilder()
    error_matches = _match_errors_to_starts(log)
    builder.record_starts(log, error_matches, _collect_control_timestamps(log))
    builder.add_never_started_cases(expected_jobs)
    if log.has_summary:
        builder.reconcile_summary(log, expected_jobs)
    elif exit_code != 0:
        builder.demote_unrestored_passes()
    builder.add_passed()
    if not log.has_summary:
        builder.add_unparsed_output(exit_code, log)
    builder.add_unmatched_errors(log)
    builder.dedupe_repeats()
    builder.attach_warnings(log)
    return builder.cases


def convert(
    text: str,
    *,
    exit_code: int = 0,
    suite_name: str = "spread",
    expected_jobs: frozenset[str] | None = None,
) -> ET.Element:
    """Convert spread log text into a ``testsuites`` JUnit XML element."""
    cases = build_testcases(parse_log(text), exit_code, expected_jobs)

    failures = sum(1 for case in cases if case.outcome == "failed")
    skipped = sum(1 for case in cases if case.outcome == "skipped")
    total_time = sum(case.duration for case in cases)

    counts = {
        "tests": str(len(cases)),
        "failures": str(failures),
        "errors": "0",
        "skipped": str(skipped),
        "time": f"{total_time:.3f}",
    }
    suite_name = _xml_safe(suite_name)
    suites = ET.Element("testsuites", {"name": suite_name, **counts})
    ET.SubElement(suites, "testsuite", {"name": suite_name, **counts})
    suite = suites.find("testsuite")
    assert suite is not None
    for case in cases:
        attributes = {
            "classname": _xml_safe(case.classname),
            "name": _xml_safe(case.name),
        }
        if case.duration:
            attributes["time"] = f"{case.duration:.3f}"
        element = ET.SubElement(suite, "testcase", attributes)
        if case.outcome == "failed":
            failure = ET.SubElement(
                element,
                "failure",
                {"message": _xml_safe(case.message or "task failed")},
            )
            if case.detail:
                failure.text = _xml_safe(case.detail)
        elif case.outcome == "skipped":
            ET.SubElement(
                element,
                "skipped",
                {"message": _xml_safe(case.message or "skipped")},
            )
        if case.system_out:
            ET.SubElement(element, "system-out").text = _xml_safe(case.system_out)
    return suites


def _normalize_expected_jobs(raw: list[str] | None) -> frozenset[str] | None:
    """Turn '--expected-jobs' values into a job-name set, or None when empty."""
    if not raw:
        return None
    return frozenset(job.strip() for job in raw if job.strip()) or None


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: read a spread log, write JUnit XML."""
    parser = argparse.ArgumentParser(description="Convert a spread log to JUnit XML")
    parser.add_argument(
        "--log-file", required=True, help="Path to the spread log to parse"
    )
    parser.add_argument(
        "--junit-file", required=True, help="Path of the JUnit XML file to write"
    )
    parser.add_argument(
        "--exit-code",
        type=int,
        default=0,
        help="spread's exit code, used to interpret unparseable output",
    )
    parser.add_argument(
        "--suite-name",
        default="spread",
        help="Name for the JUnit testsuite (default: %(default)s)",
    )
    parser.add_argument(
        "--expected-jobs",
        nargs="*",
        default=None,
        help=(
            "Jobs from 'spread -list' (run with the same arguments); "
            "expected-but-never-started jobs are reported as skipped test cases"
        ),
    )
    args = parser.parse_args(argv)

    text = Path(args.log_file).read_text(encoding="utf-8", errors="replace")
    expected_jobs = _normalize_expected_jobs(args.expected_jobs)
    suites = convert(
        text,
        exit_code=args.exit_code,
        suite_name=args.suite_name,
        expected_jobs=expected_jobs,
    )

    output = Path(args.junit_file)
    output.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(suites)
    ET.indent(tree, space="  ")
    tree.write(output, encoding="unicode", xml_declaration=True)
    with output.open("a", encoding="utf-8") as handle:
        handle.write("\n")

    suite = suites.find("testsuite")
    assert suite is not None
    print(
        f"spread_to_junit: {suite.get('tests')} test cases "
        f"({suite.get('failures')} failed, {suite.get('skipped')} skipped) -> {output}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
