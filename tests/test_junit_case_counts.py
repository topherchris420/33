"""Case counts and requirement aggregation have different denominators."""

import pytest

from evidence.common import EvidenceError
from evidence.evaluate import parse_junit


@pytest.mark.parametrize("tag,state", [("", "passed"), ("<failure/>", "failed"), ("<skipped/>", "skipped")])
def test_parameter_cases_are_counted_without_weakening_required_test_outcomes(tag, state):
    data = ('<testsuite><testcase classname="tests.test_example" name="test_input[a]"/>'
            '<testcase classname="tests.test_example" name="test_input[b]">'
            + tag + '</testcase></testsuite>').encode()
    record = parse_junit(data)
    assert record["tests"] == 2
    assert record["passed"] == (2 if state == "passed" else 1)
    assert record["outcomes"]["test_example::test_input"] == state
    assert sum(record[s] for s in ("passed", "failed", "skipped")) == 2


def test_unidentified_testcases_are_rejected_instead_of_silently_omitted():
    with pytest.raises(EvidenceError, match="classname and name"):
        parse_junit(b'<testsuite><testcase classname="tests.test_example" name="test_ok"/><testcase/></testsuite>')
