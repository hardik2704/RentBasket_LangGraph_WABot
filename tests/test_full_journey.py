"""
RentBasket WhatsApp Bot - Full Journey Tests
============================================
Simulates a real human customer walking through complete bot flows
from first greeting to receiving the final checkout/cart link.

Each test uses JourneySession, which records every exchange (user
and bot messages, buttons, list selections) as a structured log.
Failures can be diagnosed turn-by-turn from the transcript printout.

Bot flow reference:
  Browse path:
    Hi  ->  [BROWSE_PRODUCTS]  ->  [BROWSE_DUR_x]  ->  [ROOM_x] (list)
    ->  [SUBCAT_x] (list or button)  ->  "1" (variant selection)
    ->  [BROWSE_SHOW_DETAILS]  ->  [BROWSE_CHECKOUT]  ->  "pincode text"
    ->  CART LINK received

  Sales mode path:
    "SALES"  ->  "sofa and fridge for 12mo"  ->  [FINAL_LINK]
    ->  CART LINK with 5% discount received

  1BHK package path:
    [BROWSE_PRODUCTS]  ->  [BROWSE_DUR_12]  ->  [ROOM_1BHK] (list)
    ->  [PKG_COMFORT] (button)  ->  [BROWSE_SHOW_DETAILS]
    ->  [BROWSE_CHECKOUT]  ->  "pincode"  ->  CART LINK
"""

import json
import os
import random
import pytest
from unittest.mock import patch, MagicMock

from conftest import build_webhook_payload


# ============================================================
#  JOURNEY SESSION
# ============================================================

class JourneySession:
    """
    Full-journey test primitive that records ALL message types
    (text, interactive buttons, list messages) as a numbered transcript.

    Usage::

        def test_something(journey, mock_distance_api):
            journey.send_text("Hi")
            journey.press_button("BROWSE_PRODUCTS")
            journey.press_button("BROWSE_DUR_6")
            journey.select_list_item("ROOM_LIVING")
            journey.select_list_item("SUBCAT_SOFA")
            journey.send_text("1")
            journey.press_button("BROWSE_SHOW_DETAILS")
            journey.press_button("BROWSE_CHECKOUT")
            journey.send_text("Gurugram 122001")
            journey.assert_any_bot_text_contains("serviceable")
            journey.assert_cart_link_received()
    """

    def __init__(self, client, mock_whatsapp, phone=None, sender_name="Rahul Sharma"):
        self.client = client
        self.mock_whatsapp = mock_whatsapp
        self.phone = phone or f"9199{random.randint(10000000, 99999999)}"
        self.sender_name = sender_name
        self.log = []               # {"step", "direction", "type", "content"}
        self._seen_text = 0
        self._seen_buttons = 0
        self._seen_list = 0
        self._last_buttons = []     # button dicts from most recent send_interactive_buttons
        self._last_list_rows = []   # row ids from most recent send_list_message

    # ----------------------------------------------------------
    #  Send methods
    # ----------------------------------------------------------

    def send_text(self, text: str) -> "JourneySession":
        """Send a free-text message."""
        self._log("user", "text", text)
        payload = build_webhook_payload(
            phone=self.phone, text=text, sender_name=self.sender_name
        )
        self.client.post("/webhook", data=json.dumps(payload), content_type="application/json")
        self._capture()
        return self

    def press_button(self, button_id: str, button_title: str = "") -> "JourneySession":
        """Tap an interactive button (button_reply)."""
        label = button_title or button_id
        self._log("user", "button", f"[{label}]")
        interactive = {"button_reply": {"id": button_id, "title": label}}
        payload = build_webhook_payload(
            phone=self.phone, msg_type="interactive",
            interactive=interactive, sender_name=self.sender_name,
        )
        self.client.post("/webhook", data=json.dumps(payload), content_type="application/json")
        self._capture()
        return self

    def select_list_item(self, item_id: str, item_title: str = "") -> "JourneySession":
        """Select from a WhatsApp list message (list_reply)."""
        label = item_title or item_id
        self._log("user", "list_select", f"[{label}]")
        interactive = {"list_reply": {"id": item_id, "title": label}}
        payload = build_webhook_payload(
            phone=self.phone, msg_type="interactive",
            interactive=interactive, sender_name=self.sender_name,
        )
        self.client.post("/webhook", data=json.dumps(payload), content_type="application/json")
        self._capture()
        return self

    # ----------------------------------------------------------
    #  Capture
    # ----------------------------------------------------------

    def _capture(self):
        """Snapshot new bot messages across all three channels."""
        all_text = self.mock_whatsapp.send_text_message.call_args_list
        all_buttons = self.mock_whatsapp.send_interactive_buttons.call_args_list
        all_list = self.mock_whatsapp.send_list_message.call_args_list

        for call in all_text[self._seen_text:]:
            args, kwargs = call
            target = args[0] if args else kwargs.get("to_phone", "")
            if target == self.phone:
                msg = args[1] if len(args) > 1 else kwargs.get("message", "")
                self._log("bot", "text", str(msg))

        for call in all_buttons[self._seen_buttons:]:
            args, kwargs = call
            target = args[0] if args else kwargs.get("to_phone", "")
            if target == self.phone:
                body = kwargs.get("body_text", args[1] if len(args) > 1 else "")
                buttons = kwargs.get("buttons", [])
                btn_row = " | ".join(f"[{b.get('title', b.get('id', ''))}]" for b in buttons)
                self._log("bot", "buttons", f"{str(body)[:80]} => {btn_row}")
                self._last_buttons = buttons

        for call in all_list[self._seen_list:]:
            args, kwargs = call
            target = args[0] if args else kwargs.get("to_phone", "")
            if target == self.phone:
                body = kwargs.get("body_text", "")
                sections = kwargs.get("sections", [])
                row_ids = [r["id"] for sec in sections for r in sec.get("rows", [])]
                self._log("bot", "list_msg", f"{str(body)[:80]} => {', '.join(row_ids[:8])}")
                self._last_list_rows = row_ids

        self._seen_text = len(all_text)
        self._seen_buttons = len(all_buttons)
        self._seen_list = len(all_list)

    def _log(self, direction: str, kind: str, content: str):
        step = len(self.log) + 1
        self.log.append({"step": step, "direction": direction, "type": kind, "content": content})
        tag = "USER" if direction == "user" else "BOT "
        preview = content[:115] + "..." if len(content) > 115 else content
        print(f"\n    {step:2}. {tag} [{kind:12}] {preview}")

    # ----------------------------------------------------------
    #  Assertion helpers
    # ----------------------------------------------------------

    def assert_any_bot_text_contains(self, keyword: str):
        """Assert at least one send_text_message reply contains the keyword."""
        texts = self.all_bot_texts
        assert texts, "No bot text messages recorded yet"
        found = any(keyword.lower() in t.lower() for t in texts)
        assert found, (
            f"No bot text contained '{keyword}'.\n"
            f"All bot texts:\n" + "\n---\n".join(t[:200] for t in texts[-5:])
        )

    def assert_any_bot_message_contains(self, keyword: str):
        """Assert at least one bot log entry (text OR button body OR list body) contains keyword."""
        all_bot = [e["content"] for e in self.log if e["direction"] == "bot"]
        assert all_bot, "No bot messages recorded yet"
        found = any(keyword.lower() in entry.lower() for entry in all_bot)
        assert found, (
            f"No bot message contained '{keyword}'.\n"
            f"All bot messages:\n" + "\n---\n".join(e[:150] for e in all_bot[-6:])
        )

    def assert_no_bot_text_contains(self, keyword: str):
        """Assert no bot text message contains the keyword."""
        for t in self.all_bot_texts:
            assert keyword.lower() not in t.lower(), (
                f"Bot text unexpectedly contained '{keyword}'.\nText: {t[:300]}"
            )

    def assert_last_buttons_include(self, button_id: str):
        """Assert the most recently sent button set includes a button with the given ID."""
        ids = [b.get("id", "") for b in self._last_buttons]
        assert button_id in ids, (
            f"Button '{button_id}' not in last buttons set.\nGot: {ids}"
        )

    def assert_cart_link_received(self):
        """Assert the final bot text is a cart URL."""
        last = self.last_text_reply
        assert last and ("http" in last.lower() or "rentbasket" in last.lower()), (
            f"Expected cart URL as the final bot text message.\nGot: {last!r}"
        )

    # ----------------------------------------------------------
    #  Transcript / Reporting
    # ----------------------------------------------------------

    def print_transcript(self):
        print(f"\n{'='*68}")
        print(f"  JOURNEY TRANSCRIPT  |  {self.sender_name}  |  {self.phone}")
        print(f"{'='*68}")
        for e in self.log:
            tag = "USER" if e["direction"] == "user" else "BOT "
            preview = e["content"][:98] + "..." if len(e["content"]) > 98 else e["content"]
            print(f"  {e['step']:2}. {tag} [{e['type']:12}] {preview}")
        print(f"{'='*68}")

    def save_log(self, filepath: str):
        """Persist the full journey log to a JSON file."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(
                {"phone": self.phone, "sender_name": self.sender_name,
                 "total_steps": len(self.log), "log": self.log},
                f, indent=2, ensure_ascii=False,
            )

    # ----------------------------------------------------------
    #  Properties
    # ----------------------------------------------------------

    @property
    def last_text_reply(self):
        """Most recent text message sent by the bot."""
        for e in reversed(self.log):
            if e["direction"] == "bot" and e["type"] == "text":
                return e["content"]
        return None

    @property
    def all_bot_texts(self):
        return [e["content"] for e in self.log if e["direction"] == "bot" and e["type"] == "text"]

    @property
    def all_user_steps(self):
        return [e for e in self.log if e["direction"] == "user"]


# ============================================================
#  FIXTURES
# ============================================================

@pytest.fixture
def journey(client, mock_whatsapp):
    return JourneySession(client, mock_whatsapp, sender_name="Rahul Sharma")


@pytest.fixture
def mock_distance_api():
    """Serviceable from Gurgaon office (within 25 km)."""
    with patch("webhook_server_revised._call_distance_api") as m:
        m.return_value = {
            "gurgaon_km": 4.5, "noida_km": 38.2,
            "gurgaon_max_km": 25.0, "noida_max_km": 25.0,
        }
        yield m


@pytest.fixture
def mock_distance_api_noida():
    """Serviceable from Noida office only."""
    with patch("webhook_server_revised._call_distance_api") as m:
        m.return_value = {
            "gurgaon_km": 50.0, "noida_km": 8.3,
            "gurgaon_max_km": 25.0, "noida_max_km": 25.0,
        }
        yield m


@pytest.fixture
def mock_distance_api_unserviceable():
    """Outside service range of both offices."""
    with patch("webhook_server_revised._call_distance_api") as m:
        m.return_value = {
            "gurgaon_km": 60.0, "noida_km": 55.0,
            "gurgaon_max_km": 25.0, "noida_max_km": 25.0,
        }
        yield m


# ============================================================
#  HELPER: common browse steps reused across multiple tests
# ============================================================

def _browse_to_variant_list(journey, duration_btn, room_id, subcat_id, room_title="", subcat_title=""):
    """
    Navigate from greeting to the variant text list for a specific subcategory.
    Returns the journey (for chaining).
    """
    journey.send_text("Hi")
    journey.press_button("BROWSE_PRODUCTS")
    journey.press_button(duration_btn, duration_btn.replace("BROWSE_DUR_", "") + " Months")
    journey.select_list_item(room_id, room_title or room_id)
    # Subcategory may come as a button (<=3 subcats) or list (>3 subcats)
    if subcat_id.startswith("SUBCAT_WS_") or subcat_id.startswith("SUBCAT_BED"):
        journey.press_button(subcat_id, subcat_title or subcat_id)
    else:
        journey.select_list_item(subcat_id, subcat_title or subcat_id)
    return journey


# ============================================================
#  BROWSE PRODUCTS — Living Room Sofa  (full 10-step journey)
# ============================================================

class TestBrowseLivingRoomJourney:
    """
    Complete 10-step browse journey for living room sofa.
    Flow: Hi -> Browse -> 6mo -> Living Room -> Sofa ->
          pick variant -> View Cart -> Checkout -> pincode -> CART LINK
    """

    def test_complete_sofa_journey_to_cart_link(self, journey, mock_distance_api):
        """Happy-path: full browse to cart link for a sofa."""
        print("\n--- SOFA JOURNEY (full 10 steps) ---")

        # Step 1: Greeting → greeting buttons
        journey.send_text("Hi")
        journey.assert_any_bot_message_contains("RentBasket")
        journey.assert_last_buttons_include("BROWSE_PRODUCTS")

        # Step 2: Browse Products → duration buttons
        journey.press_button("BROWSE_PRODUCTS", "Browse Products")
        journey.assert_any_bot_message_contains("duration")

        # Step 3: Pick 6-month duration → room list
        journey.press_button("BROWSE_DUR_6", "6 Months")
        journey.assert_any_bot_text_contains("6 months")

        # Step 4: Select Living Room → subcategory list
        journey.select_list_item("ROOM_LIVING", "Living Room")

        # Step 5: Select Sofa → variant text list
        journey.select_list_item("SUBCAT_SOFA", "Sofa")
        journey.assert_any_bot_text_contains("Seater")
        journey.assert_any_bot_text_contains("Rs.")

        # Step 6: Pick item #1 (2 Seater Sofa) → quote + [View Cart, Browse More, Reviews]
        journey.send_text("1")
        journey.assert_any_bot_text_contains("added")
        journey.assert_last_buttons_include("BROWSE_SHOW_DETAILS")

        # Step 7: View full cart details → [Modify Cart, Reviews, Checkout]
        journey.press_button("BROWSE_SHOW_DETAILS", "View Cart")
        journey.assert_any_bot_text_contains("Monthly Rent")
        journey.assert_any_bot_text_contains("Security Deposit")
        journey.assert_last_buttons_include("BROWSE_CHECKOUT")

        # Step 8: Tap Checkout → ask for pincode
        journey.press_button("BROWSE_CHECKOUT", "Checkout")
        journey.assert_any_bot_text_contains("pincode")

        # Step 9: Provide location with pincode → serviceability check
        journey.send_text("Sector 52, Gurugram 122001")

        # Step 10: Receive serviceability confirmation + cart link
        journey.assert_any_bot_text_contains("serviceable")
        journey.assert_any_bot_text_contains("122001")
        journey.assert_cart_link_received()

        journey.print_transcript()
        journey.save_log("tests/journey_logs/living_room_sofa.json")

    def test_sofa_journey_button_states_at_each_step(self, journey, mock_distance_api):
        """Verify exact button IDs at each decision point in the sofa journey."""
        # Greeting → BROWSE_PRODUCTS + HOW_RENTING_WORKS
        journey.send_text("Hello")
        journey.assert_last_buttons_include("BROWSE_PRODUCTS")
        journey.assert_last_buttons_include("HOW_RENTING_WORKS")

        # Browse Products → duration buttons 3 / 6 / 12
        journey.press_button("BROWSE_PRODUCTS")
        journey.assert_last_buttons_include("BROWSE_DUR_3")
        journey.assert_last_buttons_include("BROWSE_DUR_6")
        journey.assert_last_buttons_include("BROWSE_DUR_12")

        # Duration → room list includes all 5 rooms
        journey.press_button("BROWSE_DUR_12", "12 Months")
        assert any(r in journey._last_list_rows for r in ["ROOM_LIVING", "ROOM_BEDROOM"]), (
            f"Room list missing expected IDs, got: {journey._last_list_rows}"
        )

        # Living Room → subcategory list has SUBCAT_SOFA
        journey.select_list_item("ROOM_LIVING", "Living Room")
        assert "SUBCAT_SOFA" in journey._last_list_rows, (
            f"Subcategory list missing SUBCAT_SOFA, got: {journey._last_list_rows}"
        )

        # SUBCAT_SOFA → variant text with sofa names
        journey.select_list_item("SUBCAT_SOFA", "Sofa")
        journey.assert_any_bot_text_contains("2 Seater Sofa")
        journey.assert_any_bot_text_contains("3 Seater Sofa")

        # Pick variant 2 (3 Seater Sofa) → quote + View Cart button
        journey.send_text("2")
        journey.assert_any_bot_text_contains("3 Seater")
        journey.assert_last_buttons_include("BROWSE_SHOW_DETAILS")

        # View Cart → Checkout button visible
        journey.press_button("BROWSE_SHOW_DETAILS", "View Cart")
        journey.assert_last_buttons_include("BROWSE_CHECKOUT")
        journey.assert_last_buttons_include("BROWSE_MODIFY_CART")

        # Checkout → pincode prompt
        journey.press_button("BROWSE_CHECKOUT", "Checkout")
        journey.assert_any_bot_text_contains("pincode")

        # Pincode → cart link
        journey.send_text("Noida Sector 62, 201301")
        journey.assert_any_bot_text_contains("serviceable")
        journey.assert_cart_link_received()


# ============================================================
#  BROWSE PRODUCTS — Workstation (button subcategory path)
# ============================================================

class TestBrowseWorkstationJourney:
    """
    ROOM_WORKSTATION has 3 subcategories so it uses interactive buttons
    (not a list). This exercises the button subcategory code path.
    """

    def test_study_table_journey_to_cart_link(self, journey, mock_distance_api):
        """Study Table: complete journey via button subcategory."""
        print("\n--- WORKSTATION STUDY TABLE JOURNEY ---")

        journey.send_text("Hi")
        journey.press_button("BROWSE_PRODUCTS")
        journey.press_button("BROWSE_DUR_12", "12 Months")
        journey.select_list_item("ROOM_WORKSTATION", "Work Station")

        # Subcategory buttons (<=3 subcats → buttons)
        journey.assert_last_buttons_include("SUBCAT_WS_TABLES")
        journey.press_button("SUBCAT_WS_TABLES", "Tables")
        journey.assert_any_bot_text_contains("Study Table")

        journey.send_text("1")                                 # Study Table
        journey.assert_any_bot_text_contains("Study Table")
        journey.press_button("BROWSE_SHOW_DETAILS", "View Cart")
        journey.assert_last_buttons_include("BROWSE_CHECKOUT")

        journey.press_button("BROWSE_CHECKOUT", "Checkout")
        journey.assert_any_bot_text_contains("pincode")

        journey.send_text("Cyber City Gurugram 122002")
        journey.assert_any_bot_text_contains("serviceable")
        journey.assert_cart_link_received()

        journey.print_transcript()
        journey.save_log("tests/journey_logs/workstation_study_table.json")

    def test_study_chair_journey(self, journey, mock_distance_api):
        """Study chair via SUBCAT_WS_CHAIRS button path."""
        journey.send_text("Hi")
        journey.press_button("BROWSE_PRODUCTS")
        journey.press_button("BROWSE_DUR_6", "6 Months")
        journey.select_list_item("ROOM_WORKSTATION", "Work Station")
        journey.assert_last_buttons_include("SUBCAT_WS_CHAIRS")

        journey.press_button("SUBCAT_WS_CHAIRS", "Chairs")
        journey.assert_any_bot_text_contains("Chair")
        journey.assert_any_bot_text_contains("/mo")

        journey.send_text("study chair")                     # fuzzy name match
        journey.assert_any_bot_text_contains("cart")

        journey.press_button("BROWSE_SHOW_DETAILS", "View Cart")
        journey.press_button("BROWSE_CHECKOUT", "Checkout")
        journey.send_text("Dwarka Sector 12 Delhi 110075")
        journey.assert_any_bot_text_contains("serviceable")
        journey.assert_cart_link_received()


# ============================================================
#  BROWSE PRODUCTS — Kitchen
# ============================================================

class TestBrowseKitchenJourney:
    """Kitchen appliance journey via list subcategory selection."""

    def test_fridge_journey_to_cart_link(self, journey, mock_distance_api):
        """Fridge 190L: Kitchen -> Refrigerator -> item 1 -> checkout -> cart link."""
        print("\n--- KITCHEN FRIDGE JOURNEY ---")

        journey.send_text("Hi")
        journey.press_button("BROWSE_PRODUCTS")
        journey.press_button("BROWSE_DUR_12", "12 Months")
        journey.select_list_item("ROOM_KITCHEN", "Kitchen")
        journey.select_list_item("SUBCAT_FRIDGE", "Refrigerator")

        journey.assert_any_bot_text_contains("Fridge")
        journey.send_text("1")                                 # Fridge 190 Ltr
        journey.assert_any_bot_text_contains("Fridge")

        journey.press_button("BROWSE_SHOW_DETAILS", "View Cart")
        journey.assert_last_buttons_include("BROWSE_CHECKOUT")
        journey.press_button("BROWSE_CHECKOUT", "Checkout")

        journey.send_text("Noida Sector 18 201301")
        journey.assert_any_bot_text_contains("serviceable")
        journey.assert_cart_link_received()

        journey.print_transcript()
        journey.save_log("tests/journey_logs/kitchen_fridge.json")

    def test_washing_machine_journey(self, journey, mock_distance_api):
        """Washing machine → complete checkout."""
        journey.send_text("Hi")
        journey.press_button("BROWSE_PRODUCTS")
        journey.press_button("BROWSE_DUR_6", "6 Months")
        journey.select_list_item("ROOM_KITCHEN", "Kitchen")
        journey.select_list_item("SUBCAT_WASHING", "Washing Machine")

        journey.assert_any_bot_text_contains("Washing")
        journey.send_text("1")                                 # Fully Automatic WM
        journey.press_button("BROWSE_SHOW_DETAILS", "View Cart")
        journey.press_button("BROWSE_CHECKOUT", "Checkout")
        journey.send_text("DLF Phase 2 Gurugram 122002")
        journey.assert_any_bot_text_contains("serviceable")
        journey.assert_cart_link_received()


# ============================================================
#  BROWSE PRODUCTS — 1BHK Package
# ============================================================

class TestBrowse1BHKJourney:
    """Complete 1BHK package journey: PKG_COMFORT → checkout → cart link."""

    def test_1bhk_comfort_package_to_cart_link(self, journey, mock_distance_api):
        """PKG_COMFORT = Double Bed + Mattress + LED TV + Sofa + Fridge."""
        print("\n--- 1BHK COMFORT PACKAGE JOURNEY ---")

        journey.send_text("Hi")
        journey.press_button("BROWSE_PRODUCTS")
        journey.press_button("BROWSE_DUR_12", "12 Months")
        journey.select_list_item("ROOM_1BHK", "Complete 1BHK")

        # Three package buttons
        journey.assert_last_buttons_include("PKG_BASIC")
        journey.assert_last_buttons_include("PKG_COMFORT")
        journey.assert_last_buttons_include("PKG_LUXURY")

        journey.press_button("PKG_COMFORT", "Comfort 1BHK")
        journey.assert_any_bot_text_contains("Comfort")
        journey.assert_any_bot_text_contains("Rs.")

        # After package selection, quote shows [View Cart, Browse More, Reviews]
        journey.press_button("BROWSE_SHOW_DETAILS", "View Cart")
        journey.assert_any_bot_text_contains("Monthly Rent")
        journey.assert_last_buttons_include("BROWSE_CHECKOUT")

        journey.press_button("BROWSE_CHECKOUT", "Checkout")
        journey.assert_any_bot_text_contains("pincode")

        journey.send_text("Gurugram Sector 44 122002")
        journey.assert_any_bot_text_contains("serviceable")
        journey.assert_cart_link_received()

        journey.print_transcript()
        journey.save_log("tests/journey_logs/1bhk_comfort.json")

    def test_1bhk_luxury_package(self, journey, mock_distance_api):
        """PKG_LUXURY path (King Bed + AC + DD Fridge + etc.)."""
        journey.send_text("Hi")
        journey.press_button("BROWSE_PRODUCTS")
        journey.press_button("BROWSE_DUR_12", "12 Months")
        journey.select_list_item("ROOM_1BHK", "Complete 1BHK")

        journey.press_button("PKG_LUXURY", "Luxury 1BHK")
        journey.assert_any_bot_text_contains("Luxury")

        journey.press_button("BROWSE_SHOW_DETAILS", "View Cart")
        journey.press_button("BROWSE_CHECKOUT", "Checkout")
        journey.send_text("MG Road Gurugram 122002")
        journey.assert_any_bot_text_contains("serviceable")
        journey.assert_cart_link_received()


# ============================================================
#  BROWSE PRODUCTS — Error Recovery
# ============================================================

class TestBrowseErrorRecovery:
    """Edge-case recovery: bad pincode, unserviceable area, empty cart checkout."""

    def test_invalid_pincode_then_valid(self, journey, mock_distance_api):
        """First attempt has no pincode → retry with valid one → cart link."""
        print("\n--- INVALID PINCODE RECOVERY ---")

        _browse_to_variant_list(journey, "BROWSE_DUR_6", "ROOM_WORKSTATION",
                                "SUBCAT_WS_TABLES", "Work Station", "Tables")
        journey.send_text("1")
        journey.press_button("BROWSE_SHOW_DETAILS", "View Cart")
        journey.press_button("BROWSE_CHECKOUT", "Checkout")

        # First try: no pincode digits
        journey.send_text("near Cyber Hub Gurugram")
        journey.assert_any_bot_text_contains("pincode")
        journey.assert_no_bot_text_contains("rentbasket.com")  # no link yet

        # Second try: valid pincode
        journey.send_text("Cyber Hub Gurugram 122002")
        journey.assert_any_bot_text_contains("serviceable")
        journey.assert_cart_link_received()

        journey.print_transcript()

    def test_unserviceable_pincode_message(self, journey, mock_distance_api_unserviceable):
        """Pincode outside service range → polite rejection message."""
        _browse_to_variant_list(journey, "BROWSE_DUR_6", "ROOM_WORKSTATION",
                                "SUBCAT_WS_TABLES", "Work Station", "Tables")
        journey.send_text("1")
        journey.press_button("BROWSE_SHOW_DETAILS", "View Cart")
        journey.press_button("BROWSE_CHECKOUT", "Checkout")

        journey.send_text("Some far city 560001")
        last = journey.last_text_reply or ""
        assert any(kw in last.lower() for kw in
                   ["not serviceable", "outside", "not deliver", "not available"]), (
            f"Expected non-serviceable message, got: {last[:400]}"
        )

    def test_checkout_empty_cart_is_rejected(self, journey, mock_distance_api):
        """BROWSE_CHECKOUT with no items in cart → error message, no crash."""
        journey.send_text("Hi")
        journey.press_button("BROWSE_PRODUCTS")
        journey.press_button("BROWSE_DUR_6")

        # Press BROWSE_CHECKOUT before adding any items
        journey.press_button("BROWSE_CHECKOUT", "Checkout")
        journey.assert_any_bot_text_contains("no items")


# ============================================================
#  BROWSE PRODUCTS — Multi-item and Modify Cart
# ============================================================

class TestBrowseMultiItemJourney:
    """Multi-item cart and cart modification."""

    def test_add_item_view_full_cart_checkout(self, journey, mock_distance_api):
        """Add sofa → View Cart details → Checkout → cart link."""
        print("\n--- ADD SOFA + VIEW CART + CHECKOUT ---")

        journey.send_text("Hi")
        journey.press_button("BROWSE_PRODUCTS")
        journey.press_button("BROWSE_DUR_12", "12 Months")
        journey.select_list_item("ROOM_LIVING", "Living Room")
        journey.select_list_item("SUBCAT_SOFA", "Sofa")
        journey.send_text("1")
        journey.assert_any_bot_text_contains("added")

        # Full cart details
        journey.press_button("BROWSE_SHOW_DETAILS", "View Cart")
        journey.assert_any_bot_text_contains("Monthly Rent")
        journey.assert_any_bot_text_contains("Security Deposit")
        journey.assert_last_buttons_include("BROWSE_CHECKOUT")
        journey.assert_last_buttons_include("BROWSE_MODIFY_CART")

        journey.press_button("BROWSE_CHECKOUT", "Checkout")
        journey.send_text("Gurugram Sector 14 122001")
        journey.assert_any_bot_text_contains("serviceable")
        journey.assert_cart_link_received()

        journey.print_transcript()
        journey.save_log("tests/journey_logs/sofa_view_cart_checkout.json")

    def test_modify_cart_add_second_item_checkout(self, journey, mock_distance_api):
        """
        Add sofa → View Cart → Modify Cart → type "add study table"
        → cart now has 2 items → View Cart again → Checkout → cart link.

        Note: when browse_modify_mode is active, numeric text ("1") is
        interpreted as "remove item #1", so we use the explicit "add X" command.
        """
        print("\n--- MODIFY CART: ADD SECOND ITEM ---")

        # Add first item: sofa
        journey.send_text("Hi")
        journey.press_button("BROWSE_PRODUCTS")
        journey.press_button("BROWSE_DUR_12", "12 Months")
        journey.select_list_item("ROOM_LIVING", "Living Room")
        journey.select_list_item("SUBCAT_SOFA", "Sofa")
        journey.send_text("1")
        journey.assert_any_bot_text_contains("added")

        # Open full cart details → Modify Cart button appears
        journey.press_button("BROWSE_SHOW_DETAILS", "View Cart")
        journey.assert_last_buttons_include("BROWSE_MODIFY_CART")

        # Enter Modify Cart mode → cart text + Browse More button
        journey.press_button("BROWSE_MODIFY_CART", "Modify Cart")
        journey.assert_any_bot_text_contains("cart")
        journey.assert_last_buttons_include("BROWSE_PRODUCTS")

        # Use text-based add command (browse_modify_mode is active)
        # "add study table" triggers the "add" intent → adds the item, clears modify mode
        journey.send_text("add study table")
        journey.assert_any_bot_text_contains("Study Table")

        # Cart now has 2 items → quote buttons appear
        journey.press_button("BROWSE_SHOW_DETAILS", "View Cart")
        journey.assert_any_bot_text_contains("Monthly Rent")
        journey.assert_last_buttons_include("BROWSE_CHECKOUT")

        journey.press_button("BROWSE_CHECKOUT", "Checkout")
        journey.send_text("Gurugram DLF Phase 3 122002")
        journey.assert_any_bot_text_contains("serviceable")
        journey.assert_cart_link_received()

        journey.print_transcript()
        journey.save_log("tests/journey_logs/modify_cart_two_items.json")


# ============================================================
#  SALES MODE — SALES keyword → FINAL_LINK
# ============================================================

class TestSalesModeJourney:
    """
    Internal Sales Mode: triggered by the SALES keyword.
    Sales rep types a cart → FINAL_LINK sends checkout URL with 5% discount.
    """

    def test_sofa_fridge_to_final_link(self, journey):
        """SALES → sofa+fridge → FINAL_LINK → cart URL with 5% discount."""
        print("\n--- SALES MODE: SOFA + FRIDGE -> FINAL LINK ---")

        journey.send_text("SALES")
        journey.assert_any_bot_text_contains("cart")

        journey.send_text("1 sofa and 1 fridge for 12 months")
        journey.assert_any_bot_text_contains("Sofa")
        journey.assert_any_bot_text_contains("Fridge")
        journey.assert_any_bot_text_contains("/mo")           # price shown (₹X/mo + GST)
        journey.assert_last_buttons_include("FINAL_LINK")
        journey.assert_last_buttons_include("UPFRONT_PAYMENT")

        journey.press_button("FINAL_LINK", "Final Link")
        # Bot message: "Here is your cart link with 5% additional discount..."
        journey.assert_any_bot_text_contains("5%")
        journey.assert_cart_link_received()

        journey.print_transcript()
        journey.save_log("tests/journey_logs/sales_sofa_fridge_final_link.json")

    def test_upfront_payment_breakdown(self, journey):
        """SALES mode → UPFRONT_PAYMENT → savings breakdown displayed."""
        journey.send_text("SALES")
        journey.send_text("1 bed and 1 washing machine for 12 months")
        journey.assert_last_buttons_include("UPFRONT_PAYMENT")

        journey.press_button("UPFRONT_PAYMENT", "Upfront Payment")
        journey.assert_any_bot_text_contains("Upfront")
        journey.assert_any_bot_text_contains("save")

    def test_unmatched_items_get_warning(self, journey):
        """
        Sending items with one clearly unmatched term:
        - If bot warns about it, that warning text must be in a bot message.
        - If bot fuzzy-matches it to something, the cart must still have items.
        Either way the bot must NOT crash.
        """
        journey.send_text("SALES")
        journey.send_text("1 sofa and 1 xyzfakeitem123 for 6 months")

        # Sofa must appear (it's a known item)
        journey.assert_any_bot_text_contains("Sofa")
        # Bot must not crash regardless of how it handles the unknown item
        journey.assert_no_bot_text_contains("traceback")
        journey.assert_no_bot_text_contains("exception")

    def test_final_link_without_cart_shows_error(self, journey):
        """Pressing FINAL_LINK with nothing in session → error message, no crash."""
        journey.send_text("SALES")
        journey.press_button("FINAL_LINK", "Final Link")
        journey.assert_any_bot_text_contains("No valid products")

    def test_modify_cart_in_sales_mode(self, journey):
        """SALES → build cart → MODIFY_CART button → Remove sofa → new cart."""
        journey.send_text("SALES")
        journey.send_text("1 sofa and 1 fridge for 12 months")
        journey.assert_last_buttons_include("MODIFY_CART")

        # Simulate sales person modifying cart
        journey.press_button("MODIFY_CART", "Modify Cart")
        # After Modify Cart, user can type new cart text (remove item)
        journey.send_text("remove sofa")
        # Bot should rebuild cart without sofa
        bot_texts = journey.all_bot_texts
        assert bot_texts, "Bot should have responded to cart modification"


# ============================================================
#  HINGLISH JOURNEY
# ============================================================

@pytest.mark.hinglish
class TestHinglishJourney:
    """
    Users sending Hinglish (mixed Hindi/English) should navigate
    the same button-driven browse flow without errors.
    """

    def test_hinglish_greeting_navigates_flow(self, journey, mock_distance_api):
        """Namaste greeting → full browse flow works normally."""
        print("\n--- HINGLISH BROWSE JOURNEY ---")

        # "namaste" IS in GREETING_WORDS → triggers handle_greeting
        journey.send_text("Namaste")
        journey.assert_any_bot_message_contains("RentBasket")
        journey.assert_last_buttons_include("BROWSE_PRODUCTS")

        journey.press_button("BROWSE_PRODUCTS")
        journey.press_button("BROWSE_DUR_6", "6 Months")
        journey.select_list_item("ROOM_WORKSTATION", "Work Station")
        journey.press_button("SUBCAT_WS_TABLES", "Tables")
        journey.send_text("1")                                 # numeric selection works

        journey.assert_any_bot_text_contains("Study Table")
        journey.assert_any_bot_text_contains("added")
        journey.assert_no_bot_text_contains("traceback")
        journey.assert_no_bot_text_contains("exception")

        journey.press_button("BROWSE_SHOW_DETAILS", "View Cart")
        journey.press_button("BROWSE_CHECKOUT", "Checkout")
        journey.send_text("Gurugram 122001")
        journey.assert_any_bot_text_contains("serviceable")
        journey.assert_cart_link_received()

        journey.print_transcript()

    def test_hinglish_variant_selection_by_name(self, journey, mock_distance_api):
        """User types partial product name in Hinglish style → fuzzy match works."""
        journey.send_text("Namaste")
        journey.press_button("BROWSE_PRODUCTS")
        journey.press_button("BROWSE_DUR_12", "12 Months")
        journey.select_list_item("ROOM_WORKSTATION", "Work Station")
        journey.press_button("SUBCAT_WS_CHAIRS", "Chairs")

        # User types a partial name, not exact
        journey.send_text("study chair")
        bot_texts = journey.all_bot_texts
        assert bot_texts, "Bot must respond to name-based variant selection"
        journey.assert_no_bot_text_contains("traceback")


# ============================================================
#  REGRESSION GUARDS
# ============================================================

@pytest.mark.regression
class TestJourneyRegressions:
    """Guards for known journey-level bugs."""

    def test_browse_context_survives_mid_flow_greeting(self, journey, mock_distance_api):
        """
        A second greeting message mid-browse must not wipe the browse context.
        User should be able to continue browsing afterward.
        """
        journey.send_text("Hi")
        journey.press_button("BROWSE_PRODUCTS")
        journey.press_button("BROWSE_DUR_6", "6 Months")

        # Spurious second greeting mid-flow
        journey.send_text("Hi")

        # Duration already set → pressing BROWSE_PRODUCTS skips to room list
        journey.press_button("BROWSE_PRODUCTS")
        journey.select_list_item("ROOM_WORKSTATION", "Work Station")
        journey.press_button("SUBCAT_WS_TABLES", "Tables")
        journey.send_text("1")
        journey.assert_any_bot_text_contains("added")

    def test_sales_mode_cleared_after_final_link(self, journey):
        """
        After FINAL_LINK is pressed, sales_mode must be removed from session
        so the next message is not treated as a sales cart.
        """
        from webhook_server_revised import session_context

        journey.send_text("SALES")
        journey.send_text("1 sofa for 12 months")
        journey.press_button("FINAL_LINK", "Final Link")
        journey.assert_any_bot_text_contains("5%")

        ctx = session_context.get(journey.phone, {})
        assert not ctx.get("sales_mode"), (
            "sales_mode must be cleared from session_context after FINAL_LINK"
        )

    def test_quote_variable_not_shadowing_url_encoder(self, journey):
        """
        Regression: local variable 'quote' in handle_interactive_response
        was shadowing urllib.parse.quote, causing FINAL_LINK to crash.
        Bug was fixed by renaming the local variable to 'browse_quote'.
        """
        journey.send_text("SALES")
        journey.send_text("1 sofa for 12 months")

        # FINAL_LINK must complete without raising
        # "cannot access local variable 'quote' where it is not associated..."
        try:
            journey.press_button("FINAL_LINK", "Final Link")
            no_error = True
        except Exception as exc:
            no_error = False
            pytest.fail(f"FINAL_LINK raised an exception: {exc}")

        assert no_error
        journey.assert_any_bot_text_contains("5%")    # cart link message sent

    def test_separate_phones_have_isolated_carts(self, client, mock_whatsapp, mock_distance_api):
        """
        Two concurrent users browsing different categories must not
        see each other's carts (no shared session state).
        """
        user_a = JourneySession(client, mock_whatsapp, phone="919800000001", sender_name="User A")
        user_b = JourneySession(client, mock_whatsapp, phone="919800000002", sender_name="User B")

        # User A: sofa
        user_a.send_text("Hi")
        user_a.press_button("BROWSE_PRODUCTS")
        user_a.press_button("BROWSE_DUR_12", "12 Months")
        user_a.select_list_item("ROOM_LIVING", "Living Room")
        user_a.select_list_item("SUBCAT_SOFA", "Sofa")
        user_a.send_text("1")

        # User B: fridge
        user_b.send_text("Hi")
        user_b.press_button("BROWSE_PRODUCTS")
        user_b.press_button("BROWSE_DUR_6", "6 Months")
        user_b.select_list_item("ROOM_KITCHEN", "Kitchen")
        user_b.select_list_item("SUBCAT_FRIDGE", "Refrigerator")
        user_b.send_text("1")

        from webhook_server_revised import session_context
        items_a = session_context.get(user_a.phone, {}).get("last_browse_quote", {}).get("items", [])
        items_b = session_context.get(user_b.phone, {}).get("last_browse_quote", {}).get("items", [])

        assert items_a and items_b, "Both users must have cart items"
        ids_a = {it["product_id"] for it in items_a}
        ids_b = {it["product_id"] for it in items_b}
        assert ids_a != ids_b, (
            f"Cart isolation violated — both users have same product IDs.\n"
            f"User A: {ids_a}  |  User B: {ids_b}"
        )
