from scrapers.website_scraper import WebsiteScraper
from scrapers.linkedin_scraper import LinkedInScraper
from scrapers.facebook_scraper import FacebookScraper 
from src.api.services.config_manager import load_config
import asyncio 

async def main_scraper(): 
    print("Starting Data Collection...")
    
    config = load_config()
    
    if not config:
        print("Exiting due to missing or empty config.json.")
        return 

    # Website Scraper 
    website_url = config.get("website_url")
    if website_url:
        print(f"\n--- Starting Website Scraper for {website_url} ---")
        ws = WebsiteScraper(website_url)
        ws.scrape()
    else:
        print("\nSkipping Website Scraper: 'website_url' not found in config.json")

    # LinkedIn Scraper 
    li_url = config.get("linkedin_url")
    if li_url:
        print(f"\n--- Starting LinkedIn Scraper for {li_url} ---")
        li = LinkedInScraper(li_url, max_posts=5)
        li.scrape()  
    else:
        print("\nSkipping LinkedIn Scraper: 'linkedin_url' not found in config.json")
    
    # Facebook Scraper 
    fb_url = config.get("facebook_url")
    if fb_url:
        print(f"\n--- Starting Facebook Scraper (via Apify) for {fb_url} ---")
        try:
            fb = FacebookScraper(fb_url, max_posts=10, max_comments_per_post=5)
            fb.scrape()
        except ValueError as e:
            print(f"Skipping Facebook Scraper due to configuration error: {e}")
        except Exception as e:
            print(f"An error occurred running the Facebook scraper: {e}")
    else:
        print("\nSkipping Facebook Scraper: 'facebook_url' not found in config.json")

    print("\nAll scraping completed successfully!")

if __name__ == "__main__":
    asyncio.run(main_scraper())