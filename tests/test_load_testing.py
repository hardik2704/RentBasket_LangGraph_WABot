"""
Load & Throughput Tests for RentBasket WhatsApp Bot.

Measures webhook processing throughput with mocked agents.
Tests sequential rapid-fire requests to verify stability under load.

NOTE: Since mock_threads makes threading synchronous, we measure
inline processing time per request rather than true concurrent load.
For real HTTP concurrency testing, use locust against a running server.

Run with: pytest -m load -v
"""

import json
import time
import statistics
import pytest
from conftest import build_webhook_payload


def _print_latency_stats(latencies):
    """Print p50, p95, p99, max latency."""
    if not latencies:
        print("  No latency data.")
        return
    latencies.sort()
    n = len(latencies)
    print(f"  Requests: {n}")
    print(f"  p50: {latencies[n // 2]:.4f}s")
    print(f"  p95: {latencies[int(n * 0.95)]:.4f}s")
    print(f"  p99: {latencies[int(n * 0.99)]:.4f}s")
    print(f"  Max: {latencies[-1]:.4f}s")
    print(f"  Avg: {statistics.mean(latencies):.4f}s")


# ============================================================
# LOAD TESTS
# ============================================================

@pytest.mark.load
class TestThroughput:
    """Throughput and stability under rapid sequential load."""

    def test_10_rapid_users(self, client, mock_whatsapp, mock_agent):
        """10 unique users in rapid succession -- all should get 200 OK."""
        latencies = []
        failures = 0

        for i in range(10):
            phone = f"91990010{i:04d}"
            payload = build_webhook_payload(
                phone=phone, text=f"Need furniture item {i}",
                msg_id=f"wamid.load10_{i:04d}",
            )
            start = time.perf_counter()
            resp = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
            elapsed = time.perf_counter() - start
            latencies.append(elapsed)
            if resp.status_code != 200:
                failures += 1

        print(f"\n  10-user rapid test:")
        _print_latency_stats(latencies)
        assert failures == 0, f"{failures}/10 requests failed"

    def test_50_rapid_users(self, client, mock_whatsapp, mock_agent):
        """50 unique users in rapid succession."""
        latencies = []
        failures = 0

        for i in range(50):
            phone = f"91990050{i:04d}"
            payload = build_webhook_payload(
                phone=phone, text=f"Need furniture {i}",
                msg_id=f"wamid.load50_{i:04d}",
            )
            start = time.perf_counter()
            resp = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
            elapsed = time.perf_counter() - start
            latencies.append(elapsed)
            if resp.status_code != 200:
                failures += 1

        print(f"\n  50-user rapid test:")
        _print_latency_stats(latencies)
        assert failures <= 2, f"{failures}/50 requests failed (>2 threshold)"

    def test_100_rapid_users(self, client, mock_whatsapp, mock_agent):
        """100 unique users -- throughput measurement."""
        latencies = []
        failures = 0

        overall_start = time.perf_counter()
        for i in range(100):
            phone = f"9199100{i:05d}"
            payload = build_webhook_payload(
                phone=phone, text=f"Inquiry {i}",
                msg_id=f"wamid.load100_{i:05d}",
            )
            start = time.perf_counter()
            resp = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
            elapsed = time.perf_counter() - start
            latencies.append(elapsed)
            if resp.status_code != 200:
                failures += 1

        overall_elapsed = time.perf_counter() - overall_start
        throughput = 100 / overall_elapsed if overall_elapsed > 0 else 0

        print(f"\n  100-user rapid test:")
        print(f"  Total time: {overall_elapsed:.2f}s")
        print(f"  Throughput: {throughput:.1f} req/s")
        print(f"  Failures: {failures}/100")
        _print_latency_stats(latencies)
        assert failures <= 5, f"{failures}/100 requests failed (>5 threshold)"

    def test_sustained_single_user_20_messages(self, client, mock_whatsapp, mock_agent):
        """Single user sends 20 rapid messages -- no state corruption."""
        phone = "919900009999"
        latencies = []

        for i in range(20):
            payload = build_webhook_payload(
                phone=phone, text=f"Message number {i}",
            )
            start = time.perf_counter()
            resp = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
            elapsed = time.perf_counter() - start
            latencies.append(elapsed)
            assert resp.status_code == 200

        print(f"\n  20-message sustained user:")
        _print_latency_stats(latencies)

        # Verify state exists and is not corrupted
        from webhook_server_revised import conversations
        state = conversations.get(phone)
        assert state is not None
        assert "collected_info" in state

    def test_mixed_with_duplicates(self, client, mock_whatsapp, mock_agent):
        """30 unique + 10 duplicate msg_ids -- dedup works correctly."""
        all_statuses = []
        dedup_count = 0

        # 30 unique messages
        for i in range(30):
            payload = build_webhook_payload(
                phone=f"91990070{i:04d}",
                text=f"Unique msg {i}",
                msg_id=f"wamid.mixed_unique_{i:04d}",
            )
            resp = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
            all_statuses.append(resp.status_code)

        # 10 duplicates (reuse first 10 msg_ids)
        for i in range(10):
            payload = build_webhook_payload(
                phone=f"91990070{i:04d}",
                text=f"Unique msg {i}",
                msg_id=f"wamid.mixed_unique_{i:04d}",
            )
            resp = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
            all_statuses.append(resp.status_code)
            resp_json = resp.get_json()
            if resp_json and resp_json.get("status") == "duplicate":
                dedup_count += 1

        print(f"\n  Mixed load: {dedup_count}/10 duplicates correctly deduped")
        assert all(s == 200 for s in all_statuses)
        assert dedup_count == 10, f"Expected 10 deduped, got {dedup_count}"
