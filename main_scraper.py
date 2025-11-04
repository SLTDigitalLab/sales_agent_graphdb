from scrapers.website_scraper import WebsiteScraper
from scrapers.linkedin_scraper import LinkedInScraper
from scrapers.facebook_scraper import FacebookScraper 

if __name__ == "__main__":
    print("Starting Data Collection...")

    # --- 1. Website Scraper ---
    website_url = "https://www.slt.lk/home"
    ws = WebsiteScraper(website_url)
    ws.scrape()

    print("\n--- Starting LinkedIn Scraper ---")
    # --- 2. LinkedIn Scraper ---
    li_url = "https://lk.linkedin.com/company/srilankatelecom"
    li = LinkedInScraper(li_url, max_posts=5)
    li.scrape()
    
    print("\n--- Starting Facebook Scraper (via Apify) ---")
    # --- 3. Facebook Scraper ---
    # NOTE: Use the public Facebook page URL corresponding to the company
    fb_url = "https://www.facebook.com/SLTMobitel/" 
    
    # Scrape 10 posts and up to 5 comments per post
    try:
        fb = FacebookScraper(fb_url, max_posts=10, max_comments_per_post=5)
        fb.scrape()
    except ValueError as e:
        print(f"Skipping Facebook Scraper due to configuration error: {e}")


    print("\nAll scraping completed successfully!")