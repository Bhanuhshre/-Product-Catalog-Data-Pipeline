# Product Catalog Data Pipeline

Scrapes product listings from brand/e-commerce sites, cleans and
validates the results, and produces an Excel-ready catalog.

Built to handle catalogs in the 10,000+ SKU range: a two-stage crawl
(listing pages, then product detail pages) feeds a pandas cleaning
pass that standardizes pricing, flags missing or invalid fields, and
removes duplicate SKUs, before everything is exported to a formatted,
multi-tab Excel workbook.

**Stack:** Python, Requests, BeautifulSoup, pandas, openpyxl

## What it does

1. **Scrape** (`scraper/scrape_catalog.py`) - crawls paginated category
   listing pages, follows each product link, and pulls name, brand,
   category, description, price, and attribute fields (color,
   material, size, weight) with `requests` + `BeautifulSoup`. Detail
   pages are fetched concurrently with a thread pool since that's
   the part that dominates runtime once the catalog gets large.

2. **Clean and validate** (`pipeline/clean_validate.py`) - built on
   `pandas`:
   - strips whitespace and normalizes blank/`NaN` values
   - parses inconsistent price text (`$19.99`, `19.99 USD`, `19`) into
     a numeric column plus currency
   - checks category values against the known taxonomy and flags
     anything that doesn't match
   - removes duplicate SKUs (keeping whichever copy has more fields
     filled in) and logs what was dropped
   - scores each record on completeness across the key catalog fields
     rather than silently discarding partial rows

3. **Export** (`pipeline/export_excel.py`) - writes a formatted,
   multi-tab workbook with `openpyxl`:
   - `Catalog` - the cleaned product records
   - `Data Quality Report` - counts behind the cleaning run
   - `Removed Duplicates` - audit log of what was dropped
   - `Flagged Records` - rows still missing a required field or with
     an unrecognized category

## Running it

```
pip install -r requirements.txt
python main.py
```

By default this builds and serves a small local demo catalog site
(`mock_site/`) to scrape against, so the pipeline runs end to end with
no external dependencies. Output lands in `output/processed/`.

To point it at a real site instead, skip the demo site and call
`scraper.scrape_catalog.run()` with your own list of listing/product
URLs - the cleaning and export stages don't change.

```
python main.py --live
```
(with your own URL source wired into `scraper/scrape_catalog.py`)

## Sample output

Data quality report from a demo run against the bundled 1,200-product
test site:

```
Raw records scraped                        1242
Duplicate SKUs removed                        42
Records after dedupe                        1200
Records missing a required field               0
Records with invalid/unrecognized category      0
Average completeness score (%)                95.0
Missing 'description'                         141
Missing 'color'                               132
Missing 'material'                            149
Missing 'size'                                119
```

## Project layout

```
config.py                    field names, categories, paths, settings
scraper/scrape_catalog.py    requests + BeautifulSoup crawler
pipeline/clean_validate.py   pandas cleaning/validation
pipeline/export_excel.py     openpyxl workbook writer
mock_site/                   local demo site + server (test target only)
main.py                      pipeline entry point
```

## Notes on scale

The demo run generates and scrapes ~1,200 products in a few seconds.
The same code handles a 10,000+ SKU catalog - the listing-page walk
and thread-pooled detail fetches don't change shape, they just run
longer. For a catalog that size in production it's worth adding retry
logic around flaky requests and writing raw records to disk in
batches rather than holding everything in memory until the end.
