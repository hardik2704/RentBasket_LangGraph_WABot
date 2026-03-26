"""
WhatsApp Interactive Menus for the RentBasket Support Experience.
Defines structured choices for standard operational requests.
"""

from typing import Dict, List, Any

# ==========================================
# MAIN SUPPORT MENU (List Message)
# ==========================================
MAIN_SUPPORT_MENU = {
    "header": "🛠️ Support Menu",
    "body_text": "Hi! We're here to help with your rented items. What seems to be the issue?",
    "button_text": "Select Issue Type",
    "sections": [{
        "title": "Select Category",
        "rows": [
            {"id": "SUP_TYPE_MAINTENANCE", "title": "Maintenance Issue", "description": "Repairs, damage, or installation"},
            {"id": "SUP_TYPE_BILLING", "title": "Billing / Payment", "description": "Invoices, late fees, payments"},
            {"id": "SUP_TYPE_REFUND", "title": "Deposit / Refund", "description": "Deposit status, deductions"},
            {"id": "SUP_TYPE_PICKUP", "title": "Pickup / Closure", "description": "Schedule pickup, cancel order"},
            {"id": "SUP_TYPE_RELOCATION", "title": "Relocation", "description": "Move items to a new address"},
            {"id": "SUP_TALK_TEAM", "title": "Talk to Team", "description": "Escalate to a human agent"}
        ]
    }]
}

# ==========================================
# SUBMENUS (Buttons - Max 3 items usually, or List if > 3)
# ==========================================

# 1. Maintenance Submenu (List)
MAINTENANCE_MENU = {
    "body_text": "Got it. Let's get this fixed quickly. What exactly is the problem? 🔧",
    "button_text": "Select Detail",
    "sections": [{
        "title": "Maintenance Type",
        "rows": [
            {"id": "MAINT_APPLIANCE", "title": "Appliance not working", "description": "Fridge, Washing Machine, AC etc."},
            {"id": "MAINT_FURNITURE", "title": "Furniture damaged", "description": "Sofa, Bed, Wardrobe etc."},
            {"id": "MAINT_INSTALL", "title": "Installation issue", "description": "Assembly needed, wobbly item"},
            {"id": "MAINT_REPLACE", "title": "Need replacement", "description": "Item is completely defective"},
            {"id": "MAINT_OTHER", "title": "Other problem", "description": "Something else"}
        ]
    }]
}

# 2. Maintenance Severity (Buttons max 3)
MAINTENANCE_SEVERITY_BUTTONS = [
    {"id": "SEV_UNUSABLE", "title": "Unusable 🚫"},
    {"id": "SEV_USABLE", "title": "Usable but broken ⚠️"},
    {"id": "SEV_INSPECT", "title": "Need Inspection 🔍"}
]

# 3. Billing Submenu (List)
BILLING_MENU = {
    "body_text": "Let's sort out your billing issue. What do you need help with? 💳",
    "button_text": "Billing Query",
    "sections": [{
        "title": "Topic",
        "rows": [
            {"id": "BILL_PAID", "title": "Payment made already", "description": "Money deducted but not updated"},
            {"id": "BILL_LATE", "title": "Late fee question", "description": "Why was I charged a penalty?"},
            {"id": "BILL_INVOICE", "title": "Invoice confusion", "description": "Need breakdown of charges"},
            {"id": "BILL_DUE", "title": "Due date question", "description": "Can I extend my due date?"},
            {"id": "SUP_TALK_TEAM", "title": "Talk to support", "description": "Speak to an executive"}
        ]
    }]
}

# 4. Deposit / Refund (List)
REFUND_MENU = {
    "body_text": "We handle thousands of refunds transparently. What's on your mind? 💸",
    "button_text": "Refund Query",
    "sections": [{
        "title": "Refund Issue",
        "rows": [
            {"id": "REF_STATUS", "title": "Refund status", "description": "Has my refund been processed?"},
            {"id": "REF_DEDUCT", "title": "Deduction question", "description": "Why was money deducted?"},
            {"id": "REF_DELAY", "title": "Refund delayed", "description": "It's been past the standard time"},
            {"id": "SUP_TALK_TEAM", "title": "Talk to support"}
        ]
    }]
}

# 5. Pickup / Closure (List)
PICKUP_MENU = {
    "body_text": "Sorry to see you go! Let's arrange your pickup. 🚚",
    "button_text": "Pickup Detail",
    "sections": [{
        "title": "Closure Request",
        "rows": [
            {"id": "PICK_REQUEST", "title": "Request pickup", "description": "Schedule a return"},
            {"id": "PICK_DELAY", "title": "Pickup delayed", "description": "Team hasn't arrived yet"},
            {"id": "PICK_TERMS", "title": "Contract ending soon", "description": "Want to understand closure terms"},
            {"id": "PICK_OTHER", "title": "Other pickup issue"}
        ]
    }]
}

# 6. Relocation (List)
RELOCATION_MENU = {
    "body_text": "Moving homes? We can help shift your rented items! 🏠🚚",
    "button_text": "Relocation Type",
    "sections": [{
        "title": "Options",
        "rows": [
            {"id": "MOVE_CHECK", "title": "Check serviceability", "description": "Do you deliver to my new pincode?"},
            {"id": "MOVE_REQUEST", "title": "Request relocation", "description": "Book a moving slot"},
            {"id": "MOVE_PRICE", "title": "Pricing / charges", "description": "How much does it cost?"},
            {"id": "SUP_TALK_TEAM", "title": "Talk to support"}
        ]
    }]
}

# 7. Common Functional Buttons
YES_NO_BUTTONS = [
    {"id": "SUP_YES", "title": "Yes 👍"},
    {"id": "SUP_NO", "title": "No 👎"}
]

SKIP_BUTTON = [
    {"id": "SUP_SKIP", "title": "Skip ⏩"}
]

MEDIA_REQUEST_BUTTONS = [
    {"id": "SUP_WILL_SEND", "title": "Sending Photo 📸"},
    {"id": "SUP_NO_PHOTO", "title": "I don't have one ❌"}
]
