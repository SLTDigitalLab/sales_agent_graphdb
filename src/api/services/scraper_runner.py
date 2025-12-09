import asyncio
from src.api.services.config_manager import load_config
from scrapers.website_scraper import WebsiteScraper
from scrapers.linkedin_scraper import LinkedInScraper
from scrapers.facebook_scraper import FacebookScraper
from scrapers.tiktok_scraper import TikTokScraper
from scrapers.product_scraper import scrape_catalog

def run_linkedin_scraper(li_url: str, max_posts: int = 5) -> str:
    """Run LinkedIn scraper safely."""
    try:
        li = LinkedInScraper(li_url, max_posts=max_posts)
        li.scrape()
        return "success"
    except Exception as e:
        return f"error: {str(e)}"

def run_general_scraping():
    """
    Runs ONLY: Website (Multi-URL), LinkedIn, Facebook, TikTok.
    Does NOT run Product Scraping.
    """
    config = load_config()
    results = {}
    
    # 1. Website Scraper (Handles List or Single URL)
    # Try to get the list 'website_urls', fall back to single 'website_url'
    website_urls = config.get("website_urls")
    if not website_urls:
        single_url = config.get("website_url")
        if single_url:
            website_urls = [single_url]
    
    # Filter out empty strings
    if website_urls:
        website_urls = [u for u in website_urls if u.strip()]

    if website_urls:
        print(f"\n--- Starting Website Scraper for {len(website_urls)} URLs ---")
        try:
            # Pass the list directly to the Selenium Website Scraper
            ws = WebsiteScraper(website_urls)
            ws.scrape()
            results["website"] = f"success ({len(website_urls)} sites scraped)"
        except Exception as e:
            print(f"Error in Website Scraper: {e}")
            results["website"] = f"error: {str(e)}"
    else:
        results["website"] = "skipped (no URLs)"

    # 2. LinkedIn
    li_url = config.get("linkedin_url")
    if li_url:
        print(f"\n--- Starting LinkedIn Scraper ---")
        results["linkedin"] = run_linkedin_scraper(li_url, max_posts=5)
    else:
        results["linkedin"] = "skipped (no URL)"
    
    # 3. Facebook
    fb_url = config.get("facebook_url")
    if fb_url:
        print(f"\n--- Starting Facebook Scraper ---")
        try:
            fb = FacebookScraper(fb_url, max_posts=10, max_comments_per_post=5)
            fb.scrape()
            results["facebook"] = "success"
        except Exception as e:
            results["facebook"] = f"error: {str(e)}"
    else:
        results["facebook"] = "skipped (no URL)"

    # 4. TikTok
    tiktok_url = config.get("tiktok_url")
    if tiktok_url:
        print(f"\n--- Starting TikTok Scraper ---")
        try:
            tt = TikTokScraper(tiktok_url, max_posts=10)
            tt.scrape()
            results["tiktok"] = "success"
        except Exception as e:
            results["tiktok"] = f"error: {str(e)}"
    else:
        results["tiktok"] = "skipped (no URL)"

    return results

def run_product_scraping():
    """
    Runs ONLY: Selenium Product Scraper.
    Saves to CSV. Does NOT Ingest to DB (handled by separate button).
    """
    config = load_config()
    results = {}

    # Product Scraper (Handles List or Single URL)
    product_urls = config.get("product_urls")
    if not product_urls:
        single_p_url = config.get("products_url")
        if single_p_url:
            product_urls = [single_p_url]
    
    if product_urls:
        product_urls = [u for u in product_urls if u.strip()]

    print(f"\n--- Starting Product Scraper (Selenium) ---")
    try:
        # Pass the list (or None) to the scraper function
        scrape_catalog(custom_start_urls=product_urls)
        results["products"] = "success (saved to products.csv)"
    except Exception as e:
        print(f"Error in Product Scraper: {e}")
        results["products"] = f"error: {str(e)}"
        import traceback
        traceback.print_exc()

    return results