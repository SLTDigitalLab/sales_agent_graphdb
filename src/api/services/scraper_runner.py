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
    BUTTON 1: 'Trigger General Scraping'
    Runs: Website, LinkedIn, Facebook, AND TikTok.
    Does NOT run Product Scraping.
    """
    config = load_config()
    results = {}
    
    # 1. Website
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

    # 2. LinkedIn
    li_url = config.get("linkedin_url")
    if li_url:
        print(f"\n--- Starting LinkedIn Scraper for {li_url} ---")
        result = run_linkedin_scraper(li_url, max_posts=5)
        results["linkedin"] = result
    else:
        results["linkedin"] = "skipped (no URL)"
    
    # 3. Facebook
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

    # 4. TikTok (Now Enabled!)
    tiktok_url = config.get("tiktok_url")
    if tiktok_url:
        print(f"\n--- Starting TikTok Scraper for {tiktok_url} ---")
        try:
            tt = TikTokScraper(tiktok_url, max_posts=10)
            tt.scrape()
            results["tiktok"] = "success"
        except ValueError as e:
            print(f"Skipping TikTok Scraper due to config error: {e}")
            results["tiktok"] = f"config error: {str(e)}"
        except Exception as e:
            print(f"Error in TikTok Scraper: {e}")
            results["tiktok"] = f"error: {str(e)}"
    else:
        results["tiktok"] = "skipped (no URL)"

    return results

def run_product_scraping():
    """
    BUTTON 2: 'Product Scraping'
    Runs ONLY: Selenium Product Scraper.
    Saves to products.csv. Does NOT Ingest to DB.
    """
    results = {}
    print(f"\n--- Starting Product Scraper (Selenium) ---")
    try:
        # Calls the advanced scraper (auto-discovery)
        scrape_catalog()
        results["products"] = "success (saved to products.csv)"
    except Exception as e:
        print(f"Error in Product Scraper: {e}")
        results["products"] = f"error: {str(e)}"
        import traceback
        traceback.print_exc()

    return results