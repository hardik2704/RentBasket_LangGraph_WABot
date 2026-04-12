#!/usr/bin/env python3
"""
RentBasket Bot - Test Report Generator

Reads test results from .test_results.json (collected by conftest.ReportCollector)
and generates a structured report with scores, failure analysis, and fix suggestions.

Usage:
    pytest                          # Run tests first
    python tests/report_generator.py  # Generate report
"""

import json
import os
import sys
import re
from pathlib import Path

RESULTS_FILE = os.path.join(os.path.dirname(__file__), ".test_results.json")

# ============================================================
# CATEGORY MAPPING
# ============================================================

CATEGORY_RULES = {
    "Functional": ["test_customer_flows", "test_support_flows"],
    "Conversion": ["test_conversion_flows"],
    "Stability": ["test_edge_cases", "test_load_testing"],
    "AI Quality": ["test_ai_quality"],
}

PRIORITY_MAP = {
    "Stability": "P0 - Critical",
    "Conversion": "P1 - High",
    "Functional": "P2 - Medium",
    "AI Quality": "P3 - Low",
}

# Heuristic: map failure keywords to likely responsible files
FILE_HINTS = {
    "webhook": "webhook_server_revised.py",
    "route_and_run": "agents/orchestrator.py",
    "run_support_agent": "agents/support_agent.py",
    "run_agent": "agents/sales_agent.py",
    "search_products": "tools/product_tools.py",
    "create_quote": "tools/product_tools.py",
    "sync_lead": "tools/lead_tools.py",
    "serviceability": "tools/location_tools.py",
    "catalogue": "tools/catalogue_tools.py",
    "escalat": "tools/support_escalation.py",
    "state": "agents/state.py",
    "pricing_negotiation": "webhook_server_revised.py",
    "dedup": "webhook_server_revised.py",
}

FIX_SUGGESTIONS = {
    "timeout": "Check LLM API timeout settings and add retry logic",
    "assertion": "Verify expected behavior matches actual agent/tool response",
    "keyerror": "Add defensive .get() access or ensure key is always initialized",
    "nonetype": "Add null checks before accessing state fields",
    "connection": "Check Firebase/API connectivity and add fallback",
    "hallucin": "Tighten system prompt constraints and add output validation",
    "pricing_negotiation": "Review keyword list and exclusion patterns in is_pricing_negotiation()",
    "dedup": "Verify processed_ids_dict logic and cache expiry",
    "escalat": "Check escalation routing in orchestrator and support agent",
}


# ============================================================
# FUNCTIONS
# ============================================================

def load_results(path=RESULTS_FILE):
    """Load test results from JSON file."""
    if not os.path.exists(path):
        print(f"No results file found at: {path}")
        print("Run 'pytest' first to generate results.")
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def categorize_results(results):
    """Map each test result to a scoring category."""
    categorized = {cat: [] for cat in CATEGORY_RULES}
    categorized["Regression"] = []
    categorized["Uncategorized"] = []

    for r in results:
        nodeid = r["nodeid"]
        placed = False

        # Check regression first
        if "regression" in nodeid.lower():
            categorized["Regression"].append(r)
            placed = True
            continue

        for category, patterns in CATEGORY_RULES.items():
            if any(pat in nodeid for pat in patterns):
                categorized[category].append(r)
                placed = True
                break

        if not placed:
            categorized["Uncategorized"].append(r)

    return categorized


def compute_score(results):
    """Compute pass rate as percentage."""
    if not results:
        return 100.0
    passed = sum(1 for r in results if r["outcome"] == "passed")
    return round(100 * passed / len(results), 1)


def analyze_failure(result):
    """Analyze a failed test to extract root cause, file, fix, and priority."""
    nodeid = result["nodeid"]
    longrepr = result.get("longrepr", "") or ""
    longrepr_lower = longrepr.lower()

    # Determine category and priority
    priority = "P2 - Medium"
    for category, patterns in CATEGORY_RULES.items():
        if any(pat in nodeid for pat in patterns):
            priority = PRIORITY_MAP.get(category, "P2 - Medium")
            break

    # Guess responsible file
    responsible_file = "Unknown"
    for keyword, filepath in FILE_HINTS.items():
        if keyword in longrepr_lower or keyword in nodeid.lower():
            responsible_file = filepath
            break

    # Guess fix suggestion
    fix = "Review test output and fix the underlying logic."
    for keyword, suggestion in FIX_SUGGESTIONS.items():
        if keyword in longrepr_lower:
            fix = suggestion
            break

    # Extract root cause (first AssertionError or Exception line)
    root_cause = "Unknown failure"
    for line in longrepr.split("\n"):
        if "AssertionError" in line or "Error" in line or "assert " in line:
            root_cause = line.strip()[:200]
            break

    return {
        "test": nodeid,
        "root_cause": root_cause,
        "responsible_file": responsible_file,
        "suggested_fix": fix,
        "priority": priority,
    }


def generate_report(data):
    """Generate the full structured report."""
    results = data.get("results", [])
    categorized = categorize_results(results)

    scores = {}
    for category in ["Functional", "Conversion", "Stability", "AI Quality"]:
        cat_results = categorized.get(category, [])
        scores[category] = compute_score(cat_results)

    # Overall score (weighted)
    weights = {"Functional": 0.3, "Conversion": 0.3, "Stability": 0.25, "AI Quality": 0.15}
    overall = sum(scores[cat] * weights[cat] for cat in weights)

    # Analyze failures
    failures = [
        analyze_failure(r)
        for r in results
        if r["outcome"] == "failed"
    ]

    return {
        "timestamp": data.get("timestamp", "N/A"),
        "summary": {
            "total": data.get("total", 0),
            "passed": data.get("passed", 0),
            "failed": data.get("failed", 0),
            "overall_score": round(overall, 1),
            "scores": scores,
        },
        "failures": failures,
        "category_breakdown": {
            cat: {
                "total": len(res),
                "passed": sum(1 for r in res if r["outcome"] == "passed"),
                "failed": sum(1 for r in res if r["outcome"] == "failed"),
            }
            for cat, res in categorized.items()
            if res
        },
    }


def print_report(report):
    """Pretty-print the report to stdout."""
    s = report["summary"]
    print()
    print("=" * 60)
    print("  RENTBASKET BOT - TEST REPORT")
    print("=" * 60)
    print(f"  Timestamp:   {report['timestamp']}")
    print(f"  Total Tests: {s['total']}")
    print(f"  Passed:      {s['passed']}")
    print(f"  Failed:      {s['failed']}")
    print()
    print("  SCORES:")
    print(f"  {'Functional:':<20} {s['scores']['Functional']}%")
    print(f"  {'Conversion:':<20} {s['scores']['Conversion']}%")
    print(f"  {'Stability:':<20} {s['scores']['Stability']}%")
    print(f"  {'AI Quality:':<20} {s['scores']['AI Quality']}%")
    print(f"  {'OVERALL:':<20} {s['overall_score']}%")
    print()

    # Category breakdown
    print("  CATEGORY BREAKDOWN:")
    for cat, info in report.get("category_breakdown", {}).items():
        status = "PASS" if info["failed"] == 0 else "FAIL"
        print(f"    {cat}: {info['passed']}/{info['total']} passed [{status}]")
    print()

    # Failures
    if report["failures"]:
        print("  FAILURES & FIX SUGGESTIONS:")
        print("-" * 60)
        for i, f in enumerate(report["failures"], 1):
            print(f"  [{i}] {f['test']}")
            print(f"      Root Cause:      {f['root_cause']}")
            print(f"      Responsible File: {f['responsible_file']}")
            print(f"      Suggested Fix:    {f['suggested_fix']}")
            print(f"      Priority:         {f['priority']}")
            print()
    else:
        print("  All tests passed! No failures to report.")

    print("=" * 60)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    data = load_results()
    report = generate_report(data)
    print_report(report)

    # Also write JSON report
    json_path = os.path.join(os.path.dirname(__file__), "test_report.json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  JSON report saved to: {json_path}")
