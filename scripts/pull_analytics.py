"""
Raw Pilot Analytics Puller for RentBasket Support Bot.
Produces a brute-force readable summary of how the pilot is performing, 
specifically focusing on Support Ticket Generation and Escalation Rates.
"""

import os
import sys
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import execute_query, is_db_available

def pull_support_metrics():
    if not is_db_available():
        print("❌ Database not available. Cannot pull analytics.")
        return

    print(f"\n📊 RentBasket Support Pilot Metrics (As of {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n")

    try:
        # Get total conversations
        total_sessions = execute_query("SELECT COUNT(*) FROM sessions;", fetch=True)[0][0]
        
        # Get support specific events
        events_query = """
            SELECT event_type, COUNT(*) as count 
            FROM analytics_events 
            WHERE event_type IN ('support_ticket_created', 'support_escalation')
            GROUP BY event_type;
        """
        events = execute_query(events_query, fetch=True)
        
        metrics = {"support_ticket_created": 0, "support_escalation": 0}
        for e in events:
            metrics[e[0]] = e[1]

        # Get Ticket breakdowns
        tickets_query = """
            SELECT issue_type, priority, COUNT(*) 
            FROM operations_tickets 
            GROUP BY issue_type, priority;
        """
        tickets = execute_query(tickets_query, fetch=True)

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
        if not tickets:
            print("   (No tickets in database yet)")
        for t in tickets:
            print(f"   - {t[0].capitalize()} [{t[1]} priority]: {t[2]}")
            
        # Add Recent Logs for human review
        print("\n📝 Recent Tickets (Last 3):")
        recent_tickets = execute_query("SELECT id, issue_type, summary, status FROM operations_tickets ORDER BY created_at DESC LIMIT 3;", fetch=True)
        if not recent_tickets:
            print("   (None)")
        for rt in recent_tickets:
            print(f"   - #{rt[0]} | {rt[1]}: {rt[2]} ({rt[3]})")

        print("\n🚨 Recent Escalations (Last 3):")
        recent_esc = execute_query("SELECT phone_number, timestamp, event_data FROM analytics_events WHERE event_type = 'support_escalation' ORDER BY timestamp DESC LIMIT 3;", fetch=True)
        if not recent_esc:
            print("   (None)")
        for re in recent_esc:
            data = json.loads(re[2]) if isinstance(re[2], str) else re[2]
            reason = data.get("context", {}).get("issue_type", "Unknown")
            print(f"   - {re[0]} at {re[1].strftime('%H:%M')}: {reason}")
            
        print("\n---")
        print("💡 Tips for Pilot Analysis:")
        print("1. If Escalation count is higher than Ticket Created count, check fallback logs. Users might be getting stuck.")
        print("2. If AI Self-Resolution Rate is >80%, the UX is functioning optimally.")

    except Exception as e:
        print(f"❌ Error pulling analytics: {e}")

if __name__ == '__main__':
    pull_support_metrics()
