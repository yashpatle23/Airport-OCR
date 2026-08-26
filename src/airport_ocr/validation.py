"""Structured validation results.

A validation result is a list of checks. Each check has a status:

- PASS: an expectation held;
- FAIL: a genuine defect that should block a run;
- EXPECTED_BLOCKER: a known, documented limitation (e.g. missing source bytes)
  that is not a defect but must remain visible;
- INFO: a non-gating observation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

PASS = "PASS"
FAIL = "FAIL"
EXPECTED_BLOCKER = "EXPECTED_BLOCKER"
INFO = "INFO"


@dataclass
class Validation:
    checks: List[Dict[str, Any]] = field(default_factory=list)

    def add(self, check_id: str, status: str, detail: str, **extra: Any) -> None:
        item: Dict[str, Any] = {"id": check_id, "status": status, "detail": detail}
        item.update(extra)
        self.checks.append(item)

    def require(
        self, condition: bool, check_id: str, pass_detail: str, fail_detail: str
    ) -> bool:
        self.add(check_id, PASS if condition else FAIL, pass_detail if condition else fail_detail)
        return condition

    def blocker(self, is_blocked: bool, check_id: str, blocked_detail: str, ok_detail: str) -> None:
        self.add(check_id, EXPECTED_BLOCKER if is_blocked else PASS, blocked_detail if is_blocked else ok_detail)

    def info(self, check_id: str, detail: str, **extra: Any) -> None:
        self.add(check_id, INFO, detail, **extra)

    @property
    def failures(self) -> List[Dict[str, Any]]:
        return [item for item in self.checks if item["status"] == FAIL]

    @property
    def blockers(self) -> List[Dict[str, Any]]:
        return [item for item in self.checks if item["status"] == EXPECTED_BLOCKER]

    def counts(self) -> Dict[str, int]:
        result: Dict[str, int] = {}
        for item in self.checks:
            result[item["status"]] = result.get(item["status"], 0) + 1
        return dict(sorted(result.items()))

    def report(self) -> Dict[str, Any]:
        return {
            "report_version": "1.0",
            "status": "FAIL" if self.failures else "PASS_WITH_EXPECTED_BLOCKERS",
            "operational_use": False,
            "counts": self.counts(),
            "failure_count": len(self.failures),
            "blocker_count": len(self.blockers),
            "known_blockers_are_not_failures": True,
            "checks": self.checks,
        }
