import pytest
from tools.catalogue_tools import get_full_catalogue_overview_tool, browse_category_tool
from tools.product_tools import search_products_tool

def test_catalogue_labels():
    """Verify that 'Best Price' is changed to 'Starting Price'."""
    # Test full overview
    overview = get_full_catalogue_overview_tool.invoke({})
    assert "starting prices" in overview.lower()
    assert "best prices" not in overview.lower()
    
    # Test browse category
    category_list = browse_category_tool.invoke({"category": "sofa"})
    assert "Starting Price:" in category_list
    assert "Best Price:" not in category_list

def test_product_id_hiding():
    """Verify that internal IDs are hidden from search results."""
    # Search for a common term
    results = search_products_tool.invoke({"query": "sofa"})
    
    # It should contain product names but NOT the "ID:" string
    assert "Found" in results
    assert "Sofa" in results
    assert "(ID:" not in results
    assert "ID: " not in results
