"""
Structured Data for RentBasket Support Policies.
Ensures deterministic answers rather than LLM hallucinations.
"""

SUPPORT_POLICIES = {
    "maintenance": {
        "description": "Rules regarding product maintenance, damage, and servicing.",
        "points": [
            "RentBasket covers all normal wear and tear maintenance for free.",
            "If an appliance (fridge, AC, washing machine) breaks down, our technician visits within 24-48 hours.",
            "Physical damage caused by mishandling (e.g., broken glass, deep scratches) is charged at actual repair cost.",
            "If a product is completely unrepairable due to our fault, a free replacement is provided within 72 hours."
        ]
    },
    "billing": {
        "description": "Rules for payments, late fees, and invoicing.",
        "points": [
            "Monthly rent is due on the 5th of every month.",
            "A late fee of ₹50 per day is charged after the grace period ends on the 7th.",
            "If payment is not received by the 15th, services may be suspended or pickup initiated.",
            "Invoices are sent automatically to the registered email on the 1st of every month."
        ]
    },
    "refund": {
        "description": "Rules for deposit refunds and deductions.",
        "points": [
            "Security deposits are refunded within 5-7 working days after successful pickup and QA check.",
            "If a subscription is cancelled before the lock-in period (e.g., 3 months), an early closure fee equivalent to 1 month's rent is deducted from the deposit.",
            "Any outstanding dues or damage charges are deducted directly from the security deposit."
        ]
    },
    "pickup": {
        "description": "Rules for ending subscriptions and arranging pickups.",
        "points": [
            "Customers must raise a pickup request at least 7 days before their billing cycle ends.",
            "Pickups are scheduled based on slot availability, usually taking 2-3 days from request approval.",
            "The customer must be present at the address during pickup to sign off on the QA checklist."
        ]
    },
    "relocation": {
        "description": "Rules for moving furniture to a new address.",
        "points": [
            "We offer one free relocation per year within the same city.",
            "Subsequent relocations or inter-city relocations (within our service areas) are chargeable based on distance.",
            "Relocation requests require a 7-day advance notice so we can dispatch proper packing materials and a moving team."
        ]
    }
}
