# RentBasket Knowledge Base
# Company information, FAQs, terms & conditions

RENTBASKET_KNOWLEDGE_BASE = """
## COMPANY OVERVIEW
- Mission: Democratize lifestyle for young professionals by making urban living comfortable and accessible.
- Tagline: "Comfort ki Tokri"
- Business Model: Furniture & appliance rental (3–12+ months flexible plans)
- **RentBasket Mini**: Short-term rental service for 1-2 months (contact sales team)


## SERVICE AREAS
- Gurgaon: All sectors (excl. Manesar) — Covered
- Noida: All sectors — Covered
- West Ghaziabad: Limited coverage
- Delhi/Faridabad/Manesar/Other Cities: Not covered (standard rejection)
- Border Areas: "We might cater on call"
- PG Addresses: Not served

### Location Responses
- Covered: "Yes, we deliver there"
- Uncovered: "Sorry, we don't serve in [CITY] yet. Only Gurugram and Noida for now."
- Border: "We might cater this on a call. Please contact our sales agent."
- PG: "We won't be able to cater to PG addresses right now."


## TERMS & CONDITIONS

### 1. RENTAL TERMS & TERMINATION
- Minimum Commitment: 3 months
- Lock-in: As per Annexure I
- Early Termination: 30 days notice + penalty
- Penalty Rates:
  - <3 months: Full 3-month rent
  - 3–6: 3-month rate
  - 6–9: 6-month rate
  - 9–12: 9-month rate
  - 12–18: 12-month rate
  - 18–24: 18-month rate
- Contractor Rights: Can terminate for non-payment; reclaim goods; discretion on deposit refund

### 2. PAYMENT STRUCTURE
- Security Deposit: Refundable (7 days post pickup), used for damages
- Monthly Rent: Due by 7th; first month pro-rata
- Late Fees:
  - By 15th: ₹100
  - After 15th: +5%
  - After 25th: +10%
- Other Charges: Delivery, labor (stairs, no lift)

### 3. DELIVERY & PICKUP
- Delivery: Customer ensures entry & lift; stairs charged extra
- Photos taken for inspection
- Pickup: Must be present or pay logistics fee
- QC report created; contractor's damage decision final
- Standard Delivery: 2-5 business days
- Express/Priority: Subject to availability, may incur extra charges

### 4. DAMAGE POLICY
- Customer liable for damage, loss, theft
- Irreparable: Pay market price
- Damage Types:
  - Scratches/dents, upholstery tears, stains
  - Manufacturing defects: Free
- Contractor's QC is final

### 5. MAINTENANCE POLICY
- Company:
  - Covers electronic maintenance
  - Repair in 3–5 days; replace if unrepairable
  - Furniture cleaning once/year after 12 months
- Customer:
  - Responsible for misuse damage
  - Must report promptly

### 6. UNAUTHORIZED MOVEMENT
- Consent needed for moving
- Violations: Immediate termination, legal action, Gurugram/Noida jurisdiction

### 7. REFUND POLICY
- Timeline: 7 days post pickup
- Deductions: Repairs, logistics
- Early Termination Refund = (Actual – Contract rate) × Months + pickup/labor cost


## CUSTOMER INTERACTION PROTOCOLS
- Needed for Pricing: Location, duration, product variant
- Standard Flow:
  1. Confirm area
  2. Use defaults if info missing
  3. Share pricing with assumptions
  4. Ask for customizations
  5. Share product options separately


## CONTACT INFORMATION & OFFICES

### Gurgaon Office
- Address: C9/2, Lower Ground Floor, Ardee City, Sector 52, Gurugram, Haryana 122003
- Opening Hours: Mon - Sun: 9am - 9pm
- Contact Number: +91 9958858473
- Sales: +91 9958187021

### Noida Office
- Address: Plot No B.L.K 15, Basement, Sector 116, Noida, UP 201301
- Opening Hours: Mon - Sun: 9am - 9pm
- Contact Number: +91 9958440038

### Other Contacts
- WhatsApp Bot: Primary contact method
- Email: support@rentbasket.com
- Website: RentBasket.com
- App: Available for order tracking and complaints


## EMERGENCIES
1. Report via App
2. Call +91 9958858473 (Gurgaon) or +91 9958440038 (Noida)
3. 24–48 hr response guaranteed


## COMMON QUERIES

### Pricing & Deals
- Based on location, cart, tenure, referrals, IG stories
- Senior agent decides custom deals
- Longer duration = better rates

### Quality Assurance
- Mint/new condition only
- Refurbishment done professionally
- Real images used (no stock photos)
- 24–48hr replacement for issues

### Customization
- Trendy styles available
- Fabric color customization possible
- Extra charges may apply

### Bulk Orders
- Call sales for bulk (e.g. 5 beds, 3 fridges)
- Special pricing available

### Referral Program
- 50% of friend's 1st month rent as cashback
- No limit on referrals


## COMPETITIVE EDGE
- Cost-effective: Rent ₹5,650/mo vs Buy ₹2L
- Tech-first: Mobile apps for all platforms
- Quality: Professional refurbishment + inspection
- Flexible: Easy upgrades, returns, relocation
- Free maintenance included


## PAYMENT METHODS
- UPI, Card, Netbanking accepted
- No offsetting deposit with rent
- Discounts for long-term plans


## EDGE CASES
- Bizarre Queries: Be polite, redirect to support
- Urgent Needs: 1-day delivery for essentials (mattress, RO, bed) if available
- Catalogue: Available on website
- Technical Issues: Report immediately; 3–5 day fix; complex issues get a timeline
"""


# Structured FAQs for quick lookup
FAQS = {
    "minimum_duration": "Our minimum rental duration is 3 months.",
    "security_deposit": "Security deposit is refundable within 7 days after pickup, minus any damage charges.",
    "payment_due": "Monthly rent is due by the 7th of each month.",
    "late_fee": "Late fees: ₹100 by 15th, +5% after 15th, +10% after 25th.",
    "cancellation": "Early termination requires 30 days notice and penalty based on duration completed.",
    "maintenance": "Free maintenance for electronics. Furniture cleaning after 12 months.",
    "delivery_time": "Standard delivery: 2-5 business days. Express delivery subject to availability.",
    "service_areas": "We serve Gurgaon (all sectors except Manesar) and Noida (all sectors).",
    "pg_addresses": "Sorry, we don't serve PG addresses currently.",
}


def get_faq(topic: str) -> str:
    """Get FAQ answer by topic."""
    topic = topic.lower().strip()
    for key, answer in FAQS.items():
        if topic in key or key in topic:
            return answer
    return None
