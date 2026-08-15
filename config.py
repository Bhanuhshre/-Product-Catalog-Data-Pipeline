"""
Shared configuration for the catalog scraping and cleaning pipeline.
Centralizing this here means the scraper, cleaner and exporter all agree
on field names, valid categories, and file locations.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MOCK_SITE_DIR = os.path.join(BASE_DIR, "mock_site", "site")
RAW_DATA_DIR = os.path.join(BASE_DIR, "output", "raw")
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "output", "processed")
LOG_DIR = os.path.join(BASE_DIR, "logs")

RAW_CSV_PATH = os.path.join(RAW_DATA_DIR, "raw_products.csv")
CLEAN_CSV_PATH = os.path.join(PROCESSED_DATA_DIR, "clean_products.csv")
EXCEL_OUTPUT_PATH = os.path.join(PROCESSED_DATA_DIR, "product_catalog.xlsx")

# host/port the local scrape target runs on when using the bundled demo site
SCRAPE_HOST = "127.0.0.1"
SCRAPE_PORT = 8843
LISTING_PAGE_COUNT = 30      # 30 pages x 40 cards ~= 1200 demo products
PRODUCTS_PER_PAGE = 40

REQUEST_TIMEOUT = 10
REQUEST_DELAY_SECONDS = 0.02   # politeness delay between requests
MAX_WORKERS = 8                # thread pool size for detail page fetches

CATALOG_FIELDS = [
    "sku",
    "product_name",
    "brand",
    "category",
    "subcategory",
    "description",
    "price",
    "currency",
    "color",
    "material",
    "size",
    "weight",
    "in_stock",
    "source_url",
]

VALID_CATEGORIES = {
    "Electronics",
    "Apparel",
    "Footwear",
    "Home & Kitchen",
    "Beauty & Personal Care",
    "Sports & Outdoors",
    "Toys & Games",
    "Accessories",
}

REQUIRED_FIELDS = ["sku", "product_name", "category", "price"]
COMPLETENESS_FIELDS = [
    "product_name", "brand", "category", "subcategory", "description",
    "price", "color", "material", "size",
]

for d in (RAW_DATA_DIR, PROCESSED_DATA_DIR, LOG_DIR, MOCK_SITE_DIR):
    os.makedirs(d, exist_ok=True)
