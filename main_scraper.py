from scrapers.website_scraper import WebsiteScraper
from scrapers.linkedin_scraper import LinkedInScraper
from scrapers.facebook_scraper import FacebookScraper 
from scrapers.tiktok_scraper import TikTokScraper 
from scrapers.product_scraper import scrape_catalog 
from src.api.services.config_manager import load_config
from src.api.services.neo4j_service import run_neo4j_ingestion
import asyncio 

# IMPORT LOGGER
try:
    from src.utils.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

async def main_scraper(): 
    logger.info("Starting Data Collection Pipeline...")
    
    config = load_config()
    
    if not config:
        logger.error("Exiting due to missing or empty config.json.")
        return 

    # Website Scraper 
    website_url = config.get("website_url")
    if website_url:
        logger.info(f"Starting Website Scraper for {website_url}")
        try:
            ws = WebsiteScraper(website_url)
            ws.scrape()
        except Exception as e:
            logger.error(f"Website Scraper Error: {e}", exc_info=True)
    else:
        logger.warning("Skipping Website Scraper: 'website_url' not found in config.json")

    # LinkedIn Scraper 
    li_url = config.get("linkedin_url")
    if li_url:
        logger.info(f"Starting LinkedIn Scraper for {li_url}")
        try:
            li = LinkedInScraper(li_url, max_posts=20)
            li.scrape()
        except Exception as e:
            logger.error(f"LinkedIn Scraper Error: {e}", exc_info=True)
    else:
        logger.warning("Skipping LinkedIn Scraper: 'linkedin_url' not found in config.json")
    
    # Facebook Scraper 
    fb_url = config.get("facebook_url")
    if fb_url:
        logger.info(f"Starting Facebook Scraper (via Apify) for {fb_url}")
        try:
            fb = FacebookScraper(fb_url, max_posts=20, max_comments_per_post=10)
            fb.scrape()
        except ValueError as e:
            logger.warning(f"Skipping Facebook Scraper due to configuration error: {e}")
        except Exception as e:
            logger.error(f"Facebook Scraper Error: {e}", exc_info=True)
    else:
        logger.warning("Skipping Facebook Scraper: 'facebook_url' not found in config.json")

    # TikTok Scraper 
    tiktok_url = config.get("tiktok_url")  
    if tiktok_url:
        logger.info(f"Starting TikTok Scraper for {tiktok_url}")
        try:
            tt = TikTokScraper(tiktok_url, max_posts=20)
            tt.scrape()
        except ValueError as e:
            logger.warning(f"Skipping TikTok Scraper due to configuration error: {e}")
        except Exception as e:
            logger.error(f"TikTok Scraper Error: {e}", exc_info=True)
    else:
        logger.warning("Skipping TikTok Scraper: 'tiktok_url' not found in config.json")

    # Product Scraper (UPDATED FOR SELENIUM)
    logger.info("Starting Product Scraper (Selenium)")
    try:
        # Run the selenium scraper (it runs synchronously, so it pauses here until done)
        scrape_catalog()
        
        # Automatically ingest into Neo4j after scraping
        logger.info("Starting Neo4j Product Ingestion...")
        try:
            ingested_count = run_neo4j_ingestion()
            logger.info(f"Successfully ingested {ingested_count} products into Neo4j")
        except Exception as e:
            logger.error(f"Neo4j Ingestion Error: {e}", exc_info=True)
            
    except Exception as e:
        logger.error(f"Product Scraper Error: {e}", exc_info=True)

    logger.info("All scraping completed successfully!")

if __name__ == "__main__":
    asyncio.run(main_scraper())