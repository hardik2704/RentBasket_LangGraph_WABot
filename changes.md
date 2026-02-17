# Architectural Changes & Improvements
**Date:** February 17, 2026
**Feature:** Recommendation Agent & Orchestrator Implementation

## 🚀 Qualitative Improvements

### 1. From Linear to Orchestrated Logic
Previously, `webhook_server.py` passed all messages directly to the `Sales Agent`. This meant every "Hi" or "Browse products" query was treated as a potential sales funnel entry.
- **Change:** Introduced an **Orchestrator** (`orchestrator.py`) that acts as a traffic controller.
- **Benefit:** Separation of concerns. Browsing queries go to the discovery specialist (Recommendation Agent), while specific pricing/policy queries go to the Sales Agent. This allows each agent to have a distinct "personality" and prompt optimization.

### 2. Deep Catalogue Discovery vs. Surface Search
The old `search_products_tool` was a simple keyword match.
- **Change:** Created 5 specialized **Catalogue Tools** (`catalogue_tools.py`):
  - `get_full_catalogue_overview_tool`: A bird's-eye view of all 19 categories.
  - `browse_category_tool`: Systematic listing of all options in a category.
  - `compare_products_tool`: Side-by-side spec and price comparison.
  - `filter_by_budget_tool`: Smart filtering based on monthly commitment.
  - `get_room_package_tool`: Curated bundles (e.g., Bedroom, WFH).
- **Benefit:** Users can now *explore* the catalogue naturally ("Show me sofas", "What fits in 3000?") rather than needing to know exact product names.

### 3. Display Pricing Strategy
We standardized how pricing is presented during discovery to emphasize value.
- **Change:** All catalogue tools now display the **Best Price** (12-month rate with 10% Upfront Payment Discount).
- **Benefit:** Shows the most attractive price point first, while transparency is maintained by explicitly labeling it as "12mo + upfront". The original 12-month rate is still shown for comparison.

### 4. Plug-and-Play Architecture
- **Change:** Implemented an **Agent Registry** in `orchestrator.py`.
- **Benefit:** Agents can be enabled/disabled via a simple config flag. This makes the system modular — we can A/B test different agents or kill-switch a malfunctioning one instantly without touching the server code.

### 5. Sticky Context Routing
- **Change:** The Orchestrator remembers the `active_agent`.
- **Benefit:** If a user is in a "discovery flow" (Recommendation Agent), follow-up questions stay there. They don't get bounced back to the Sales Agent just because a message was ambiguous. The context sticks until the intent clearly shifts.

### 6. Multi-Message Greeting with Rich Previews
- **Change:** Updated `Sales Agent` to output a 3-part greeting sequence separated by `|||`, and enhanced `webhook_server.py` to split and send them sequentially.
- **Benefit:** Allows for a structured onboarding experience: 
  1. Warm personal greeting
  2. Value proposition
  3. Social proof with **rich link preview** (enabled via `preview_url=True`).

## 📂 File Changes

### New Modules
- `agents/recommendation_agent.py`: The discovery specialist.
- `agents/orchestrator.py`: The intelligent router.
- `tools/catalogue_tools.py`: The suite of discovery tools.
- `test_report.md`: Comprehensive 10-scenario test suite.

### Modified Files
- `webhook_server.py`: Integrated `route_and_run` API and message splitting logic.
- `agents/state.py`: Added `active_agent` tracking.
- `agents/sales_agent.py`: Updated mandatory greeting prompt.
- `whatsapp/client.py`: Verified `preview_url` support.
- `agents/__init__.py` & `tools/__init__.py`: Exported new capabilities.

## 🎯 Test-Driven Improvements
Based on the test scenarios, we refined:
- **Quality Comparisons**: Added specific logic to highlight capacity differences (e.g., 5-seater vs 3-seater sofas).
- **Discount Wording**: Clarified "10% Upfront Payment Discount" to be precise.
- **Comparison Logic**: Defaults to 12-month pricing for apples-to-apples comparison unless requested otherwise.
