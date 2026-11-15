"""Test coverage analysis tool (honest static mapping + optional pytest-cov artifact parsing)."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from typing import Any

from orchestration.schemas import SubmittedFile


def analyze_test_coverage(
    files: list[SubmittedFile],
    discovery_result: dict[str, Any],
) -> dict[str, Any]:
    """Analyze test coverage from uploaded pytest-cov artifacts or static symbol mapping.

    Strictly avoids executing untrusted submitted code and never claims runtime
    line coverage unless genuine coverage output (coverage.json / coverage.xml) was provided.
    """
    runtime_coverage_pct: float | None = None
    runtime_coverage_source: str | None = None

    for sf in files:
        lower = sf.path.lower()
        if lower.endswith("coverage.json") and sf.content.strip():
            try:
                data = json.loads(sf.content)
                totals = data.get("totals", {})
                if "percent_covered" in totals:
                    runtime_coverage_pct = round(float(totals["percent_covered"]), 2)
                    runtime_coverage_source = sf.path
                    break
            except Exception:
                pass
        elif lower.endswith("coverage.xml") and sf.content.strip():
            try:
                root = ET.fromstring(sf.content)
                line_rate = root.attrib.get("line-rate")
                if line_rate is not None:
                    runtime_coverage_pct = round(float(line_rate) * 100.0, 2)
                    runtime_coverage_source = sf.path
                    break
            except Exception:
                pass

    tested = discovery_result.get("tested_symbols", [])
    untested = discovery_result.get("untested_symbols", [])
    total_symbols = len(tested) + len(untested)

    static_symbol_ratio = round((len(tested) / total_symbols) * 100.0, 1) if total_symbols > 0 else None

    suggested_scenarios: list[str] = []
    if not discovery_result.get("has_tests") and discovery_result.get("production_files"):
        suggested_scenarios.append(
            f"Create unit test module(s) covering {', '.join(discovery_result['production_files'][:3])}."
        )

    for sym in untested[:6]:
        suggested_scenarios.append(
            f"Add unit tests for `{sym['name']}` ({sym['file_path']}:{sym['line_start']}) "
            "covering nominal input, boundary/empty cases, and invalid/error handling."
        )

    return {
        "runtime_coverage_executed": runtime_coverage_pct is not None,
        "runtime_coverage_percent": runtime_coverage_pct,
        "runtime_coverage_source": runtime_coverage_source,
        "static_symbol_coverage_percent": static_symbol_ratio,
        "tested_count": len(tested),
        "untested_count": len(untested),
        "untested_functions": untested,
        "suggested_scenarios": suggested_scenarios,
        "note": (
            f"Parsed runtime coverage ({runtime_coverage_pct}%) from {runtime_coverage_source}."
            if runtime_coverage_pct is not None
            else "Runtime pytest-cov execution was skipped for untrusted code safety; "
            "metrics reflect static test-to-symbol mapping."
        ),
    }

