"""
Drip Messaging Scheduler for RentBasket "Ku" Bot.

Checks Firestore for cold leads and sends HSM template follow-ups via
WhatsApp Cloud API. Designed to be called by a Cloud Scheduler / cron job.

Follow-up sequence:
  - < 24 hrs since last message + browsed items but no cart  → cart_reminder template
  - ~Day 1 (24–48 hrs)                                       → followup_day1 template
  - ~Day 3 (72–120 hrs)                                      → followup_day3 template (final)

Leads with stage 'converted' or 'lost' are never contacted.
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.firebase_client import get_db
from utils.db_logger import log_event

# ─────────────────────────────────────────────
# HSM TEMPLATE DEFINITIONS
# Each entry maps a follow-up type to its approved template name and
# the variable components needed.  Update names once Meta approves them.
# ─────────────────────────────────────────────

DRIP_TEMPLATES = {
    "cart_reminder": {
        "template_name": "cart_reminder",          # Must match approved name in Meta
        "language_code": "en",
        "description": "Cart reminder < 24 hrs — browsed but no cart",
        "hours_min": 0,
        "hours_max": 24,
        "eligible_stages": ["browsing", "qualified"],
        "requires_cart": False,
        "requires_browsed": True,
    },
    "followup_day1": {
        "template_name": "followup_day1",
        "language_code": "en",
        "description": "Day 1 follow-up — still looking? soft offer",
        "hours_min": 24,
        "hours_max": 48,
        "eligible_stages": ["new", "browsing", "qualified", "cart_created"],
        "requires_cart": False,
        "requires_browsed": False,
    },
    "followup_day3": {
        "template_name": "followup_day3",
        "language_code": "en",
        "description": "Day 3 final outreach before archiving lead",
        "hours_min": 72,
        "hours_max": 120,
        "eligible_stages": ["new", "browsing", "qualified", "cart_created"],
        "requires_cart": False,
        "requires_browsed": False,
    },
}

SKIP_STAGES = {"converted", "lost", "reserved"}


# ─────────────────────────────────────────────
# FIRESTORE HELPERS
# ─────────────────────────────────────────────

def get_cold_leads(hours_min: int, hours_max: int, eligible_stages: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch leads whose last_message_timestamp falls within the [hours_min, hours_max)
    window and whose lead_stage is in eligible_stages.
    """
    db = get_db()
    if not db:
        print("⚠️ Firestore not available — skipping drip check.")
        return []

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=hours_max)
    window_end = now - timedelta(hours=hours_min)

    try:
        docs = (
            db.collection("leads")
            .where("last_message_timestamp", ">=", window_start)
            .where("last_message_timestamp", "<=", window_end)
            .get()
        )
    except Exception as e:
        print(f"⚠️ Firestore query error in get_cold_leads: {e}")
        return []

    leads = []
    for doc in docs:
        data = doc.to_dict()
        stage = data.get("lead_stage", "new")
        if stage in SKIP_STAGES:
            continue
        if stage not in eligible_stages:
            continue
        data["_doc_id"] = doc.id
        leads.append(data)

    return leads


def mark_drip_sent(phone: str, drip_key: str) -> None:
    """Record that a drip message was sent so we don't double-send."""
    db = get_db()
    if not db:
        return
    try:
        db.collection("leads").document(phone).set(
            {
                f"drip_sent_{drip_key}": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            merge=True,
        )
    except Exception as e:
        print(f"⚠️ Failed to mark drip sent for {phone}: {e}")


def already_sent(lead: Dict[str, Any], drip_key: str) -> bool:
    """Return True if this drip was already sent to this lead."""
    return f"drip_sent_{drip_key}" in lead


# ─────────────────────────────────────────────
# TEMPLATE COMPONENT BUILDER
# ─────────────────────────────────────────────

def build_components(lead: Dict[str, Any], drip_key: str) -> List[Dict[str, Any]]:
    """
    Build the template variable components for a given lead.
    Adjust the variable list to match your approved template body.
    """
    name = lead.get("name") or lead.get("push_name") or "there"
    cart = lead.get("final_cart", [])
    cart_count = len(cart)

    if drip_key == "cart_reminder" and cart_count > 0:
        return [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": name},
                    {"type": "text", "text": str(cart_count)},
                ],
            }
        ]

    # Default: just the first name
    return [
        {
            "type": "body",
            "parameters": [{"type": "text", "text": name}],
        }
    ]


# ─────────────────────────────────────────────
# MAIN RUNNER
# ─────────────────────────────────────────────

def run_drip_sequence(dry_run: bool = False) -> Dict[str, int]:
    """
    Check all drip buckets and send any due follow-ups.

    Args:
        dry_run: If True, prints what would be sent but makes no API calls.

    Returns:
        Dict with counts: {"sent": N, "skipped": N, "errors": N}
    """
    from whatsapp.client import WhatsAppClient

    wa = WhatsAppClient(demo_mode=dry_run)

    counts = {"sent": 0, "skipped": 0, "errors": 0}

    for drip_key, cfg in DRIP_TEMPLATES.items():
        leads = get_cold_leads(
            hours_min=cfg["hours_min"],
            hours_max=cfg["hours_max"],
            eligible_stages=cfg["eligible_stages"],
        )

        print(f"\n📬 [{drip_key}] {len(leads)} candidate lead(s) in window "
              f"{cfg['hours_min']}–{cfg['hours_max']}h")

        for lead in leads:
            phone = lead.get("phone") or lead.get("_doc_id")
            if not phone:
                counts["skipped"] += 1
                continue

            if already_sent(lead, drip_key):
                print(f"   ⏭️  {phone} — already sent {drip_key}, skipping")
                counts["skipped"] += 1
                continue

            # Optional: skip if no browsed items for cart_reminder
            if cfg.get("requires_browsed") and not lead.get("product_preferences"):
                print(f"   ⏭️  {phone} — no browsed items, skipping {drip_key}")
                counts["skipped"] += 1
                continue

            components = build_components(lead, drip_key)

            try:
                result = wa.send_template_message(
                    to_phone=phone,
                    template_name=cfg["template_name"],
                    language_code=cfg["language_code"],
                    components=components,
                )

                if not dry_run:
                    mark_drip_sent(phone, drip_key)
                    log_event(phone, "drip_sent", {
                        "drip_key": drip_key,
                        "template": cfg["template_name"],
                        "lead_stage": lead.get("lead_stage"),
                    })

                print(f"   ✅ {phone} — {drip_key} sent ({result})")
                counts["sent"] += 1

            except Exception as e:
                print(f"   ❌ {phone} — error sending {drip_key}: {e}")
                counts["errors"] += 1

    print(f"\n📊 Drip run complete: {counts}")
    return counts


# ─────────────────────────────────────────────
# CLI ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RentBasket Drip Scheduler")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without sending")
    args = parser.parse_args()

    run_drip_sequence(dry_run=args.dry_run)
