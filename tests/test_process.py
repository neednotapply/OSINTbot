import sys

from osintbot.process import run_process


def test_process_captures_structured_output() -> None:
    result = run_process([sys.executable, "-c", "import sys; print('out'); print('err', file=sys.stderr)"], timeout=5)
    assert result.exit_code == 0
    assert result.stdout.strip() == "out"
    assert result.stderr.strip() == "err"
    assert not result.timed_out


def test_process_timeout_is_reported() -> None:
    result = run_process([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.05)
    assert result.timed_out
    assert result.exit_code is None
