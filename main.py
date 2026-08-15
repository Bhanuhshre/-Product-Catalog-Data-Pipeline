"""
Runs the full pipeline end to end:
  1. (demo only) build and serve a local catalog site to scrape against
  2. scrape listing + detail pages with requests/BeautifulSoup
  3. clean and validate the scraped records with pandas
  4. export the result to a formatted Excel workbook

For a real target, skip step 1 and pass your own list of listing page
URLs into scraper.scrape_catalog.run(). Everything else is unchanged.
"""

import sys
import time

import config
from mock_site import build_sample_site, serve
from pipeline import clean_validate, export_excel
from scraper import scrape_catalog


def main(use_demo_site=True):
    start = time.time()

    if use_demo_site:
        print("building demo catalog site...")
        build_sample_site.build()
        serve.start()
        time.sleep(0.3)

    print("\nstage 1: collecting product URLs")
    product_urls = scrape_catalog.collect_product_urls()

    print("\nstage 2: scraping product detail pages")
    records = scrape_catalog.run(product_urls)
    raw_path = scrape_catalog.save_raw_csv(records)

    print("\nstage 3: cleaning and validating")
    result = clean_validate.run(raw_path)
    result["clean"].to_csv(config.CLEAN_CSV_PATH, index=False)
    print(result["quality_report"].to_string(index=False))

    print("\nstage 4: exporting Excel workbook")
    export_excel.export(
        result["clean"],
        result["removed_duplicates"],
        result["quality_report"],
    )

    if use_demo_site:
        serve.stop()

    elapsed = time.time() - start
    print(f"\npipeline finished in {elapsed:.1f}s")


if __name__ == "__main__":
    demo = "--live" not in sys.argv
    main(use_demo_site=demo)
