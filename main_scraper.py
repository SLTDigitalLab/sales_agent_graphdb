from scrapers.website_scraper import WebsiteScraper
from scrapers.linkedin_scraper import LinkedInScraper
from scrapers.facebook_scraper import FacebookScraper 
from scrapers.tiktok_scraper import TikTokScraper 
# UPDATE: Import the function from your new script
from scrapers.product_scraper import scrape_catalog 
from src.api.services.config_manager import load_config
from src.api.services.neo4j_service import run_neo4j_ingestion
import asyncio 

async def main_scraper(): 
    print("=" * 60)
    print("Starting Data Collection...")
    print("=" * 60)
    
    config = load_config()
    
    if not config:
        print("❌ Exiting due to missing or empty config.json.")
        return 

    # Website Scraper 
    website_url = config.get("website_url")
    if website_url:
        print(f"\n{'='*60}")
        print(f"--- Starting Website Scraper for {website_url} ---")
        print(f"{'='*60}")
        try:
            ws = WebsiteScraper(website_url)
            ws.scrape()
        except Exception as e:
            print(f"❌ Website Scraper Error: {e}")
    else:
        print("\n⚠️  Skipping Website Scraper: 'website_url' not found in config.json")

    # LinkedIn Scraper 
    li_url = config.get("linkedin_url")
    if li_url:
        print(f"\n{'='*60}")
        print(f"--- Starting LinkedIn Scraper for {li_url} ---")
        print(f"{'='*60}")
        try:
            li = LinkedInScraper(li_url, max_posts=5)
            li.scrape()
        except Exception as e:
            print(f"❌ LinkedIn Scraper Error: {e}")
    else:
        print("\n⚠️  Skipping LinkedIn Scraper: 'linkedin_url' not found in config.json")
    
    # Facebook Scraper 
    fb_url = config.get("facebook_url")
    if fb_url:
        print(f"\n{'='*60}")
        print(f"--- Starting Facebook Scraper (via Apify) for {fb_url} ---")
        print(f"{'='*60}")
        try:
            fb = FacebookScraper(fb_url, max_posts=10, max_comments_per_post=5)
            fb.scrape()
        except ValueError as e:
            print(f"⚠️  Skipping Facebook Scraper due to configuration error: {e}")
        except Exception as e:
            print(f"❌ Facebook Scraper Error: {e}")
    else:
        print("\n⚠️  Skipping Facebook Scraper: 'facebook_url' not found in config.json")

    # TikTok Scraper 
    tiktok_url = config.get("tiktok_url")  
    if tiktok_url:
        print(f"\n--- Starting TikTok Scraper for {tiktok_url} ---")
        try:
            tt = TikTokScraper(tiktok_url, max_posts=10)
            tt.scrape()
        except ValueError as e:
            print(f"Skipping TikTok Scraper due to configuration error: {e}")
        except Exception as e:
            print(f"An error occurred running the TikTok scraper: {e}")
    else:
        print("\nSkipping TikTok Scraper: 'tiktok_url' not found in config.json")

    # Product Scraper (UPDATED FOR SELENIUM)
    # Note: We use the global START_URLS inside product_scraper.py
    print(f"\n{'='*60}")
    print(f"--- Starting Product Scraper (Selenium) ---")
    print(f"{'='*60}")
    try:
        # Run the selenium scraper (it runs synchronously, so it pauses here until done)
        scrape_catalog()
        
        # Automatically ingest into Neo4j after scraping
        print(f"\n{'='*60}")
        print("--- Starting Neo4j Product Ingestion ---")
        print(f"{'='*60}")
        try:
            # Removed unexpected argument source='json'
            ingested_count = run_neo4j_ingestion()
            print(f"✅ Successfully ingested {ingested_count} products into Neo4j")
        except Exception as e:
            print(f"❌ Neo4j Ingestion Error: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ Product Scraper Error: {e}")

    print(f"\n{'='*60}")
    print("✅ All scraping completed successfully!")
    print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(main_scraper())