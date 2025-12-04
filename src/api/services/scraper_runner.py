import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from .config_manager import load_config
from scrapers.website_scraper import WebsiteScraper
from scrapers.linkedin_scraper import LinkedInScraper
from scrapers.facebook_scraper import FacebookScraper
# UPDATED: Only import the scraper, NOT the ingestion service
from scrapers.product_scraper import scrape_catalog

def run_linkedin_scraper(li_url: str, max_posts: int = 5) -> str:
    """Run LinkedIn scraper in a separate thread to avoid async conflicts."""
    try:
        li = LinkedInScraper(li_url, max_posts=max_posts)
        li.scrape()
        return "success"
    except Exception as e:
        return f"error: {str(e)}"

def run_scraping():
    """Run all scrapers using the current config."""
    config = load_config()
    
    results = {}
    
    # 1. Website Scraper
    website_url = config.get("website_url")
    if website_url:
        print(f"\n--- Starting Website Scraper for {website_url} ---")
        try:
            ws = WebsiteScraper(website_url)
            ws.scrape()
            results["website"] = "success"
        except Exception as e:
            print(f"Error in Website Scraper: {e}")
            results["website"] = f"error: {str(e)}"
    else:
        results["website"] = "skipped (no URL)"

    # 2. LinkedIn Scraper (in separate thread)
    li_url = config.get("linkedin_url")
    if li_url:
        print(f"\n--- Starting LinkedIn Scraper for {li_url} ---")
        # Run in a separate thread to avoid Playwright async conflicts
        result = run_linkedin_scraper(li_url, max_posts=5)
        results["linkedin"] = result
    else:
        results["linkedin"] = "skipped (no URL)"
    
    # 3. Facebook Scraper
    fb_url = config.get("facebook_url")
    if fb_url:
        print(f"\n--- Starting Facebook Scraper for {fb_url} ---")
        try:
            fb = FacebookScraper(fb_url, max_posts=10, max_comments_per_post=5)
            fb.scrape()
            results["facebook"] = "success"
        except Exception as e:
            print(f"Error in Facebook Scraper: {e}")
            results["facebook"] = f"error: {str(e)}"
    else:
        results["facebook"] = "skipped (no URL)"

    # 4. Product Scraper (Selenium)
    # UPDATED: Scrapes only. Does NOT ingest into Neo4j.
    products_url = config.get("products_url")
    if products_url:
        print(f"\n--- Starting Product Scraper (Selenium) ---")
        try:
            # Run the selenium scraper
            scrape_catalog()
            
            # The ingestion is now handled exclusively by the "Ingest to Neo4j" button
            results["products"] = "success (scraped to products.csv)"
        except Exception as e:
            print(f"Error in Product Scraper: {e}")
            results["products"] = f"error: {str(e)}"
            import traceback
            traceback.print_exc()
    else:
        results["products"] = "skipped (no URL)"

    return results