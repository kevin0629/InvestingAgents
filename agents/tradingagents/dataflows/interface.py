from .news_utils import get_company_news, get_macro_news
from .stock_utils import get_stock_chart, get_taiex_chart
from .fundamentals_utils import (
    get_company_factors, 
    get_company_balance_sheet, 
    get_company_cash_flow_statement, 
    get_company_income_statement, 
    get_company_monthly_revenue, 
    get_dupont_analysis,
    get_stock_river_chart
)
from .reflection_utils import store_reflections, retrieve_reflections
from .account_utils import create_stock_holding

# Configuration and routing logic
from .config import get_config

# Tools organized by category
TOOLS_CATEGORIES = {
    "stock_data": {
        "description": "OHLCV stock price data and technical analysis indicators",
        "tools": [
            "get_stock_data",
            "get_taiex_data"
        ]
    },
    "fundamental_data": {
        "description": "Company fundamentals",
        "tools": [
            "get_factors",
            "get_balance_sheet",
            "get_cashflow",
            "get_income_statement",
            "get_monthly_revenue",
            "get_dupont_analysis",
            "get_river_chart"
        ]
    },
    "news_data": {
        "description": "News data",
        "tools": [
            "get_company_news",
            "get_macro_news"
        ]
    },
    "reflection_data": {
        "description": "Reflection data storage and retrieval",
        "tools": [
            "store_reflections",
            "retrieve_reflections"
        ]
    },
    "account_data": {
        "description": "Stock holding information",
        "tools": [
            "create_stock_holding"
        ]
    }
}

VENDOR_LIST = [
    "myself",
]

# Mapping of methods to their vendor-specific implementations
VENDOR_METHODS = {
    # core_stock_apis
    "get_stock_data": {
        "myself": get_stock_chart,
    },
    "get_taiex_data": {
        "myself": get_taiex_chart,
    },
    # fundamental_data
    "get_factors": {
        "myself": get_company_factors,
    },
    "get_balance_sheet": {
        "myself": get_company_balance_sheet,
    },
    "get_cashflow": {
        "myself": get_company_cash_flow_statement,
    },
    "get_income_statement": {
        "myself": get_company_income_statement,
    },
    "get_monthly_revenue": {
        "myself": get_company_monthly_revenue,
    },
    "get_dupont_analysis": {
        "myself": get_dupont_analysis,
    },
    "get_river_chart": {
        "myself": get_stock_river_chart,
    },
    # news_data
    "get_company_news": {
        "myself": get_company_news,
    },
    "get_macro_news": {
        "myself": get_macro_news,
    },
    # reflection_data
    "store_reflections": {
        "myself": store_reflections,
    },
    "retrieve_reflections": {
        "myself": retrieve_reflections,
    },
    # account_data
    "create_stock_holding": {
        "myself": create_stock_holding,
    },
}

def get_category_for_method(method: str) -> str:
    """Get the category that contains the specified method."""
    for category, info in TOOLS_CATEGORIES.items():
        if method in info["tools"]:
            return category
    raise ValueError(f"Method '{method}' not found in any category")

def get_vendor(category: str, method: str = None) -> str:
    """Get the configured vendor for a data category or specific tool method.
    Tool-level configuration takes precedence over category-level.
    """
    config = get_config()

    # Check tool-level configuration first (if method provided)
    if method:
        tool_vendors = config.get("tool_vendors", {})
        if method in tool_vendors:
            return tool_vendors[method]

    # Fall back to category-level configuration
    return config.get("data_vendors", {}).get(category, "default")

def route_to_vendor(method: str, *args, **kwargs):
    """Route method calls to appropriate vendor implementation with fallback support."""
    category = get_category_for_method(method)
    vendor_config = get_vendor(category, method)
    primary_vendors = [v.strip() for v in vendor_config.split(',')]

    if method not in VENDOR_METHODS:
        raise ValueError(f"Method '{method}' not supported")

    # Build fallback chain: primary vendors first, then remaining available vendors
    all_available_vendors = list(VENDOR_METHODS[method].keys())
    fallback_vendors = primary_vendors.copy()
    for vendor in all_available_vendors:
        if vendor not in fallback_vendors:
            fallback_vendors.append(vendor)

    for vendor in fallback_vendors:
        if vendor not in VENDOR_METHODS[method]:
            continue

        vendor_impl = VENDOR_METHODS[method][vendor]
        impl_func = vendor_impl[0] if isinstance(vendor_impl, list) else vendor_impl

        try:
            return impl_func(*args, **kwargs)
        except Exception as e:
            print(f"Error in vendor '{vendor}' for method '{method}': {e}")
            continue
    raise RuntimeError(f"No available vendor for '{method}'")