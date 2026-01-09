"""
Web Scraping Action Executor for Multiple Sources
Handles car search requests from AutoMaritea and AutoScout24 (via Piloterr)
Sends results via email

File location: pareto_agents/web_scraping_action_executor.py
"""

import logging
import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from pareto_agents.automaritea_scraper_client import AutomariteasScraperClient, CarListing as AutomariteasListing
from pareto_agents.piloterr_autoscout24_scraper import PiloterAutoscout24Scraper, CarListing as PiloterListing
from pareto_agents.google_email_client import GoogleEmailClient

logger = logging.getLogger(__name__)


@dataclass
class CarSearchParams:
    """Car search parameters"""
    brand: Optional[str] = None
    model: Optional[str] = None
    max_mileage: Optional[int] = None
    fuel_type: Optional[str] = None
    max_price: Optional[int] = None
    min_year: Optional[int] = None
    color: Optional[str] = None
    location: Optional[str] = None
    free_search: Optional[str] = None


class WebScrapingActionExecutor:
    """
    Executor for web scraping actions
    Searches for vehicles from multiple sources and sends results via email
    """
    
    def __init__(self, email_client: GoogleEmailClient, recipient_email: str = None):
        """
        Initialize the executor
        
        Args:
            email_client (GoogleEmailClient): Email client for sending results
            recipient_email (str): Email address to send results to
        """
        self.email_client = email_client
        self.recipient_email = recipient_email
        self.automaritea_scraper = AutomariteasScraperClient()
        
        # Initialize Piloterr scraper if API key is available
        piloterr_key = os.getenv('PILOTERR_API_KEY')
        self.piloterr_scraper = None
        if piloterr_key:
            try:
                self.piloterr_scraper = PiloterAutoscout24Scraper(api_key=piloterr_key)
                logger.info("✅ Piloterr AutoScout24 scraper initialized")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Piloterr scraper: {str(e)}")
        else:
            logger.warning("⚠️ PILOTERR_API_KEY not set - AutoScout24 search disabled")
    
    def get_listings(self, params: Dict[str, Any], sources: List[str] = None) -> list:
        """
        Get car listings from specified sources
        
        Args:
            params (dict): Search parameters
            sources (list): List of sources to search ('automaritea', 'autoscout24')
            
        Returns:
            list: List of CarListing objects
        """
        try:
            if sources is None:
                sources = ['automaritea', 'autoscout24']
            
            logger.info(f"Getting listings from sources: {sources}")
            
            # Normalize parameters
            search_params = self._normalize_params(params)
            
            # Collect listings from all sources
            all_listings = []
            
            # Search AutoMaritea
            if 'automaritea' in sources:
                logger.info("Searching AutoMaritea...")
                automaritea_results = self.automaritea_scraper.search_cars(search_params, ['automaritea'])
                for website, results in automaritea_results.items():
                    all_listings.extend(results)
                logger.info(f"Found {len(all_listings)} listings from AutoMaritea")
            
            # Search AutoScout24 via Piloterr
            if 'autoscout24' in sources and self.piloterr_scraper:
                logger.info("Searching AutoScout24...")
                try:
                    autoscout24_results = self.piloterr_scraper.search(
                        brand=search_params.brand,
                        model=search_params.model,
                        max_price=search_params.max_price,
                        max_mileage=search_params.max_mileage,
                        min_year=search_params.min_year,
                        fuel_type=search_params.fuel_type,
                        country=os.getenv('AUTOSCOUT24_COUNTRY', 'de')
                    )
                    all_listings.extend(autoscout24_results)
                    logger.info(f"Found {len(autoscout24_results)} listings from AutoScout24")
                except Exception as e:
                    logger.error(f"Error searching AutoScout24: {str(e)}")
            elif 'autoscout24' in sources:
                logger.warning("AutoScout24 search requested but Piloterr scraper not initialized")
            
            logger.info(f"✅ Total {len(all_listings)} listings found")
            return all_listings
        
        except Exception as e:
            logger.error(f"❌ Error getting listings: {str(e)}", exc_info=True)
            return []
    
    def execute_car_search(self, params: Dict[str, Any], recipient_email: str = None, sources: List[str] = None) -> bool:
        """
        Execute a car search and send results via email
        
        Args:
            params (dict): Search parameters
            recipient_email (str): Email to send results to
            sources (list): List of sources to search
            
        Returns:
            bool: True if successful
        """
        try:
            # Use provided email or fallback to instance email
            email = recipient_email or self.recipient_email
            if not email:
                logger.error("No recipient email provided")
                return False
            
            logger.info(f"🔍 Starting car search with parameters: {params}")
            
            # Get listings
            listings = self.get_listings(params, sources)
            
            logger.info(f"✅ Found {len(listings)} total listings")
            
            # Format and send email
            email_body = self._format_email_body(listings, params)
            subject = f"Vehicle Search Results: {params.get('brand', 'All')} {params.get('model', '')}"
            
            # Send email
            self.email_client.send_email(
                to=email,
                subject=subject,
                body=email_body
            )
            
            logger.info(f"✅ Results emailed to {email}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Error in car search: {str(e)}", exc_info=True)
            return False
    
    def _normalize_params(self, params: Dict[str, Any]) -> CarSearchParams:
        """
        Normalize parameters to CarSearchParams
        
        Args:
            params (dict): Raw parameters
            
        Returns:
            CarSearchParams: Normalized parameters
        """
        return CarSearchParams(
            brand=params.get('brand'),
            model=params.get('model'),
            max_mileage=params.get('maxMileage') or params.get('max_mileage'),
            fuel_type=params.get('fuelType') or params.get('fuel_type'),
            max_price=params.get('maxPrice') or params.get('max_price'),
            min_year=params.get('minYear') or params.get('min_year'),
            color=params.get('color'),
            location=params.get('location'),
            free_search=params.get('free_search')
        )
    
    def _format_email_body(self, listings: List, params: Dict[str, Any]) -> str:
        """
        Format search results as plain text email
        
        Args:
            listings (list): List of car listings
            params (dict): Search parameters
            
        Returns:
            str: Formatted email body
        """
        lines = []
        
        # Header
        lines.append("=" * 80)
        lines.append("🚗 VEHICLE SEARCH RESULTS")
        lines.append("=" * 80)
        lines.append("")
        
        # Search parameters
        lines.append("SEARCH PARAMETERS:")
        lines.append("-" * 80)
        if params.get('brand'):
            lines.append(f"  Brand: {params.get('brand')}")
        if params.get('model'):
            lines.append(f"  Model: {params.get('model')}")
        if params.get('maxPrice'):
            lines.append(f"  Max Price: € {params.get('maxPrice'):,}")
        if params.get('maxMileage'):
            lines.append(f"  Max Mileage: {params.get('maxMileage'):,} km")
        if params.get('minYear'):
            lines.append(f"  Min Year: {params.get('minYear')}")
        if params.get('fuelType'):
            lines.append(f"  Fuel Type: {params.get('fuelType')}")
        if params.get('location'):
            lines.append(f"  Location: {params.get('location')}")
        
        lines.append("")
        lines.append("=" * 80)
        lines.append("")
        
        # Results
        if not listings:
            lines.append("❌ No vehicles found matching your criteria.")
        else:
            lines.append(f"📍 FOUND {len(listings)} VEHICLE(S)")
            lines.append("-" * 80)
            lines.append("")
            
            for idx, listing in enumerate(listings, 1):
                lines.append(f"{idx}. {listing.title}")
                lines.append(f"   Price: {listing.price or 'N/A'}")
                if listing.mileage:
                    lines.append(f"   Mileage: {listing.mileage}")
                if listing.year:
                    lines.append(f"   Year: {listing.year}")
                if listing.fuel_type:
                    lines.append(f"   Fuel: {listing.fuel_type}")
                if listing.location:
                    lines.append(f"   Location: {listing.location}")
                if hasattr(listing, 'seller_name') and listing.seller_name:
                    lines.append(f"   Seller: {listing.seller_name}")
                lines.append(f"   Link: {listing.url}")
                lines.append("")
        
        # Footer
        lines.append("=" * 80)
        lines.append("Search completed via AutoMaritea and AutoScout24")
        lines.append("=" * 80)
        
        return "\n".join(lines)
