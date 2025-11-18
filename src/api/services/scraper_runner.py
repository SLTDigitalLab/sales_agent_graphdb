import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from .config_manager import load_config
from scrapers.website_scraper import WebsiteScraper
from scrapers.linkedin_scraper import LinkedInScraper
from scrapers.facebook_scraper import FacebookScraper
from scrapers.product_scraper import ProductScraper 
from src.api.services.neo4j_service import ingest_scraped_products_to_neo4j 


def _run_async_scraper(coroutine):
    """Utility to run an async coroutine on the current synchronous thread."""
    return asyncio.run(coroutine)


def run_linkedin_scraper_thread(li_url: str, max_posts: int = 5) -> str:
    """Run LinkedIn scraper, handling the asynchronous execution."""
    try:
        li = LinkedInScraper(li_url, max_posts=max_posts)
        
        _run_async_scraper(li.scrape()) 
        
        return "success"
    except Exception as e:
        return f"error: {str(e)}"

def run_product_scraper_thread(product_url: str) -> str:
    """Run Product scraper and Neo4j ingestion, handling async execution."""
    try:
        ps = ProductScraper(product_url)
        
        # 1. Run the scraper asynchronously
        scraped_products = _run_async_scraper(ps.scrape())
        
        # 2. Ingest the result synchronously into Neo4j
        if scraped_products:
            items_added = ingest_scraped_products_to_neo4j(scraped_products)
            return f"success, neo4j_added={items_added}"
        else:
            return "success (0 products scraped)"
    except Exception as e:
        print(f"FATAL ERROR in Product/Neo4j Ingestion: {e}")
        return f"error: {str(e)}"

# --- Main Synchronous Runner ---

def run_scraping():
    """Run all scrapers using the current config."""
    config = load_config()
    
    results = {}
    
    # We use ThreadPoolExecutor for the asynchronous Playwright scrapers
    # to ensure they don't block the main server thread (e.g., FastAPI's main event loop).
    with ThreadPoolExecutor(max_workers=2) as executor:

        # --- 1. Product Scraper (Threaded) ---
        product_url = config.get("product_scraper_url")
        if product_url:
            print(f"\n--- Starting Product Scraper for {product_url} (Threaded) ---")
            future = executor.submit(run_product_scraper_thread, product_url)
            results["product"] = future.result()
        else:
            results["product"] = "skipped (no URL)"
            
        # --- 2. LinkedIn Scraper (Threaded) ---
        li_url = config.get("linkedin_url")
        if li_url:
            print(f"\n--- Starting LinkedIn Scraper for {li_url} (Threaded) ---")
            future = executor.submit(run_linkedin_scraper_thread, li_url, max_posts=5)
            results["linkedin"] = future.result()
        else:
            results["linkedin"] = "skipped (no URL)"

    # --- 3. Website Scraper (Synchronous - No Thread needed) ---
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
    
    # --- 4. Facebook Scraper (Synchronous - No Thread needed) ---
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

    return results