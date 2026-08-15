"""
Catalog scraper.

Two-stage crawl, which is how most brand/e-commerce sites are structured:
  1. Walk the paginated listing pages to collect product URLs.
  2. Fetch each product detail page and pull out name, price, category,
     description and attribute fields.

Runs the detail fetches in a small thread pool since they're I/O bound
and this is the part that dominates runtime once the catalog gets into
the thousands of products.
"""

import csv
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "catalog-pipeline/1.0 (data collection)"})


def base_url():
    return f"http://{config.SCRAPE_HOST}:{config.SCRAPE_PORT}"


def get_soup(path):
    url = path if path.startswith("http") else f"{base_url()}{path}"
    resp = SESSION.get(url, timeout=config.REQUEST_TIMEOUT)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser"), url


def collect_product_urls():
    """Walk listing pages starting at page 1, following 'next' links."""
    urls = []
    page = 1
    while True:
        try:
            soup, _ = get_soup(f"/catalog/page_{page}.html")
        except requests.exceptions.HTTPError:
            break

        cards = soup.select(".product-card")
        if not cards:
            break

        for card in cards:
            link = card.select_one(".product-link")
            if link and link.get("href"):
                urls.append(link["href"])

        has_next = soup.select_one('a[href*="page_{}.html"]'.format(page + 1))
        page += 1
        time.sleep(config.REQUEST_DELAY_SECONDS)
        if not has_next:
            break

    return urls


def _text_or_blank(soup, selector):
    node = soup.select_one(selector)
    return node.get_text(strip=True) if node else ""


def parse_price(raw_price_text):
    """Splits a loosely-formatted price string into (numeric value, currency)."""
    if not raw_price_text:
        return "", ""
    cleaned = raw_price_text.strip()
    currency = "USD" if ("$" in cleaned or "usd" in cleaned.lower()) else ""
    digits = "".join(ch for ch in cleaned if ch.isdigit() or ch in ".,")
    digits = digits.replace(",", "")
    return digits, currency


def scrape_product(url):
    soup, full_url = get_soup(url)

    name = _text_or_blank(soup, ".product-title")
    brand = _text_or_blank(soup, ".brand-tag")
    breadcrumb = _text_or_blank(soup, ".breadcrumb")
    category, _, subcategory = breadcrumb.partition(" / ")

    price_raw = _text_or_blank(soup, ".price-block")
    price, currency = parse_price(price_raw)

    description = _text_or_blank(soup, ".description")
    stock_text = _text_or_blank(soup, ".stock-tag")
    in_stock = "yes" if stock_text.lower().startswith("in stock") else \
               ("limited" if "limited" in stock_text.lower() else "no")

    attr_rows = soup.select(".attributes tr")
    attrs = {}
    for row in attr_rows:
        cells = row.find_all("td")
        if len(cells) == 2:
            attrs[cells[0].get_text(strip=True).lower()] = cells[1].get_text(strip=True)

    sku_node = soup.select_one(".sku-tag")
    sku = sku_node.get_text(strip=True) if sku_node else ""

    return {
        "sku": sku,
        "product_name": name,
        "brand": brand,
        "category": category.strip(),
        "subcategory": subcategory.strip(),
        "description": description,
        "price": price,
        "currency": currency,
        "color": attrs.get("color", ""),
        "material": attrs.get("material", ""),
        "size": attrs.get("size", ""),
        "weight": attrs.get("weight", ""),
        "in_stock": in_stock,
        "source_url": full_url,
    }


def run(product_urls=None, max_workers=None):
    product_urls = product_urls or collect_product_urls()
    max_workers = max_workers or config.MAX_WORKERS
    print(f"found {len(product_urls)} product URLs, fetching detail pages...")

    records = []
    errors = 0
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(scrape_product, url): url for url in product_urls}
        done = 0
        for future in as_completed(futures):
            done += 1
            try:
                records.append(future.result())
            except Exception as exc:
                errors += 1
                print(f"  failed on {futures[future]}: {exc}")
            if done % 200 == 0:
                print(f"  scraped {done}/{len(product_urls)}")

    print(f"scrape complete: {len(records)} records, {errors} failures")
    return records


def save_raw_csv(records, path=None):
    path = path or config.RAW_CSV_PATH
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=config.CATALOG_FIELDS)
        writer.writeheader()
        writer.writerows(records)
    print(f"raw data written to {path}")
    return path


if __name__ == "__main__":
    urls = collect_product_urls()
    results = run(urls)
    save_raw_csv(results)
