from scrapers.website_scraper import WebsiteScraper
from scrapers.linkedin_scraper import LinkedInScraper

if __name__ == "__main__":
    print("Starting Data Collection...")

    website_url = "https://www.slt.lk/home"
    ws = WebsiteScraper(website_url)
    ws.scrape()

    print("\n--- Starting LinkedIn Scraper ---")
    li_url = "https://lk.linkedin.com/company/srilankatelecom"
    li = LinkedInScraper(li_url, max_posts=5)
    li.scrape()

    print("\nAll scraping completed successfully!")