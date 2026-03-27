"""
Raw Pilot Analytics Puller for RentBasket Support Bot (Firestore Version).
Produces a readable summary of how the pilot is performing.
"""

import os
import sys
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.firebase_client import get_db
from google.cloud import firestore

def pull_support_metrics():
    db = get_db()
    if not db:
        print("❌ Firebase not available. Cannot pull analytics.")
        return

    print(f"\n📊 RentBasket Support Pilot Metrics (As of {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n")

    try:
        # Get total conversations
        total_sessions = len(db.collection("sessions").get())
        
        # Get support specific events
        tickets_created = len(db.collection("analytics").where("event_type", "==", "support_ticket_created").get())
        escalations = len(db.collection("analytics").where("event_type", "==", "support_escalation").get())
        
        metrics = {
            "support_ticket_created": tickets_created,
            "support_escalation": escalations
        }

        # Get Ticket breakdowns
        tickets_docs = db.collection("tickets").get()
        breakdown = {}
        for t_doc in tickets_docs:
            t = t_doc.to_dict()
            key = (t.get("issue_type", "unknown"), t.get("priority", "medium"))
            breakdown[key] = breakdown.get(key, 0) + 1

        print(f"🔹 Total Sessions Logged: {total_sessions}")
        print(f"🔹 Support Tickets Created by AI: {metrics['support_ticket_created']}")
        print(f"🔹 Support Conversations Escalated: {metrics['support_escalation']}")
        
        total_support_actions = metrics['support_ticket_created'] + metrics['support_escalation']
        if total_support_actions > 0:
            ai_resolution_rate = (metrics['support_ticket_created'] / total_support_actions) * 100
            print(f"🔹 AI Self-Resolution Rate (Approx): {ai_resolution_rate:.1f}%")
        else:
            print("🔹 AI Self-Resolution Rate: N/A (No actions logged yet)")

        print("\n📥 Tickets Breakdown:")
        if not breakdown:
            print("   (No tickets in database yet)")
        for (issue, priority), count in breakdown.items():
            print(f"   - {issue.capitalize()} [{priority} priority]: {count}")
            
        # Add Recent Logs for human review
        print("\n📝 Recent Tickets (Last 3):")
        recent_tickets = db.collection("tickets").order_by("created_at", direction=firestore.Query.DESCENDING).limit(3).get()
        if not recent_tickets:
            print("   (None)")
        for rt_doc in recent_tickets:
            rt = rt_doc.to_dict()
            print(f"   - #{rt_doc.id[:8]} | {rt.get('issue_type')}: {rt.get('summary')} ({rt.get('status')})")

        print("\n🚨 Recent Escalations (Last 3):")
        recent_esc = db.collection("analytics") \
                       .where("event_type", "==", "support_escalation") \
                       .order_by("timestamp", direction=firestore.Query.DESCENDING) \
                       .limit(3).get()
        if not recent_esc:
            print("   (None)")
        for re_doc in recent_esc:
            re = re_doc.to_dict()
            ts = re.get("timestamp")
            ts_str = ts.strftime('%H:%M') if ts else "??:??"
            reason = re.get("event_data", {}).get("reason_for_escalation", "Unknown")
            print(f"   - {re.get('phone')} at {ts_str}: {reason}")
            
        print("\n---")
        print("💡 Tips for Pilot Analysis:")
        print("1. If Escalation count is higher than Ticket Created count, check fallback logs.")
        print("2. If AI Self-Resolution Rate is >80%, the UX is functioning optimally.")

    except Exception as e:
        print(f"❌ Error pulling analytics from Firebase: {e}")

if __name__ == '__main__':
    pull_support_metrics()
