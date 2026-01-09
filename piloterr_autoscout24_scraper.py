"""
Piloterr AutoScout24 Scraper Client
Integrates with Piloterr API to search and scrape AutoScout24 vehicle listings

API Documentation: https://www.piloterr.com/library/autoscout24-search
File location: pareto_agents/piloterr_autoscout24_scraper.py
"""

import logging
import requests
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


@dataclass
class CarListing:
    """Car listing data structure"""
    title: str
    price: str
    year: Optional[str] = None
    mileage: Optional[str] = None
    fuel_type: Optional[str] = None
    location: Optional[str] = None
    url: str = ""
    image: Optional[str] = None
    seller_name: Optional[str] = None
    seller_type: Optional[str] = None
    transmission: Optional[str] = None
    power: Optional[str] = None


class PiloterAutoscout24Scraper:
    """
    Scraper for AutoScout24 using Piloterr API
    Searches for vehicles on AutoScout24 based on criteria
    """
    
    # Piloterr API endpoint
    API_ENDPOINT = "https://piloterr.com/api/v2/autoscout24/search"
    
    # AutoScout24 base URLs for different countries
    AUTOSCOUT24_URLS = {
        'de': 'https://www.autoscout24.de',
        'at': 'https://www.autoscout24.at',
        'ch': 'https://www.autoscout24.ch',
        'fr': 'https://www.autoscout24.fr',
        'it': 'https://www.autoscout24.it',
        'es': 'https://www.autoscout24.es',
        'nl': 'https://www.autoscout24.nl',
        'be': 'https://www.autoscout24.be',
        'se': 'https://www.autoscout24.se',
        'pl': 'https://www.autoscout24.pl',
        'cz': 'https://www.autoscout24.cz',
        'hr': 'https://www.autoscout24.hr',
    }
    
    def __init__(self, api_key: str):
        """
        Initialize Piloterr AutoScout24 scraper
        
        Args:
            api_key (str): Piloterr API key
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'x-api-key': api_key,
            'Content-Type': 'application/json'
        })
        logger.info("✅ Piloterr AutoScout24 scraper initialized")
    
    def search(self, 
               brand: Optional[str] = None,
               model: Optional[str] = None,
               max_price: Optional[int] = None,
               max_mileage: Optional[int] = None,
               min_year: Optional[int] = None,
               fuel_type: Optional[str] = None,
               country: str = 'de') -> List[CarListing]:
        """
        Search for vehicles on AutoScout24
        
        Args:
            brand (str): Vehicle brand/make
            model (str): Vehicle model
            max_price (int): Maximum price in EUR
            max_mileage (int): Maximum mileage in km
            min_year (int): Minimum year of manufacture
            fuel_type (str): Fuel type (petrol, diesel, hybrid, electric)
            country (str): Country code (de, at, ch, fr, it, es, nl, be, se, pl, cz, hr)
            
        Returns:
            list: List of CarListing objects
        """
        try:
            logger.info(f"🔍 Searching AutoScout24 ({country.upper()}) for {brand or 'all'} {model or ''}")
            
            # Build search URL
            base_url = self.AUTOSCOUT24_URLS.get(country.lower(), self.AUTOSCOUT24_URLS['de'])
            search_url = self._build_search_url(
                base_url=base_url,
                brand=brand,
                model=model,
                max_price=max_price,
                max_mileage=max_mileage,
                min_year=min_year,
                fuel_type=fuel_type
            )
            
            logger.info(f"Search URL: {search_url[:100]}...")
            
            # Call Piloterr API
            listings = self._call_piloterr_api(search_url)
            
            logger.info(f"✅ Found {len(listings)} listings from AutoScout24")
            return listings
        
        except Exception as e:
            logger.error(f"❌ Error searching AutoScout24: {str(e)}", exc_info=True)
            return []
    
    def _build_search_url(self,
                         base_url: str,
                         brand: Optional[str] = None,
                         model: Optional[str] = None,
                         max_price: Optional[int] = None,
                         max_mileage: Optional[int] = None,
                         min_year: Optional[int] = None,
                         fuel_type: Optional[str] = None) -> str:
        """
        Build AutoScout24 search URL with parameters
        
        Args:
            base_url (str): Base AutoScout24 URL for country
            brand (str): Vehicle brand
            model (str): Vehicle model
            max_price (int): Maximum price
            max_mileage (int): Maximum mileage
            min_year (int): Minimum year
            fuel_type (str): Fuel type
            
        Returns:
            str: Complete search URL
        """
        params = {
            'sort': 'standard',
            'desc': '0',
            'atype': 'C',  # Car type
        }
        
        # Add brand if specified
        if brand:
            params['make'] = brand.lower()
        
        # Add model if specified
        if model:
            params['model'] = model.lower()
        
        # Add price filter
        if max_price:
            params['priceto'] = max_price
        
        # Add mileage filter
        if max_mileage:
            params['kmto'] = max_mileage
        
        # Add year filter
        if min_year:
            params['yearfrom'] = min_year
        
        # Add fuel type filter
        if fuel_type:
            fuel_mapping = {
                'petrol': 'B',
                'benzin': 'B',
                'diesel': 'D',
                'hybrid': 'H',
                'electric': 'E',
                'lpg': 'L',
                'cng': 'C',
            }
            fuel_code = fuel_mapping.get(fuel_type.lower(), fuel_type)
            params['fueltype'] = fuel_code
        
        # Build URL
        query_string = urlencode(params)
        search_url = f"{base_url}/lst?{query_string}"
        
        return search_url
    
    def _call_piloterr_api(self, search_url: str) -> List[CarListing]:
        """
        Call Piloterr API to scrape AutoScout24
        
        Args:
            search_url (str): AutoScout24 search URL
            
        Returns:
            list: List of CarListing objects
        """
        try:
            # Prepare API request
            params = {
                'query': search_url
            }
            
            logger.info(f"Calling Piloterr API...")
            
            # Make API request
            response = self.session.get(self.API_ENDPOINT, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse results
            listings = []
            results = data.get('results', [])
            
            logger.info(f"API returned {len(results)} results")
            
            for item in results:
                try:
                    listing = self._parse_listing(item)
                    if listing:
                        listings.append(listing)
                except Exception as e:
                    logger.warning(f"Error parsing listing: {str(e)}")
                    continue
            
            return listings
        
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Piloterr API request failed: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"❌ Error calling Piloterr API: {str(e)}", exc_info=True)
            return []
    
    def _parse_listing(self, item: Dict[str, Any]) -> Optional[CarListing]:
        """
        Parse API response item into CarListing
        
        Args:
            item (dict): API response item
            
        Returns:
            CarListing: Parsed listing or None
        """
        try:
            # Extract vehicle info
            vehicle = item.get('vehicle', {})
            make = vehicle.get('make', 'Unknown')
            model = vehicle.get('model', 'Unknown')
            
            # Extract price
            price_info = item.get('price', {})
            price = price_info.get('price_formatted', 'N/A')
            
            # Extract location
            location_info = item.get('location', {})
            city = location_info.get('city', '')
            country = location_info.get('country_code', '')
            location = f"{city}, {country}".strip(', ')
            
            # Extract seller info
            seller_info = item.get('seller', {})
            seller_name = seller_info.get('company_name', seller_info.get('contact_name', 'Private'))
            seller_type = seller_info.get('type', 'Unknown')
            
            # Extract vehicle details
            details = item.get('vehicle_details', {})
            year = details.get('calendar', item.get('tracking', {}).get('first_registration', 'N/A'))
            mileage = details.get('mileage_road', item.get('tracking', {}).get('mileage', 'N/A'))
            fuel_type = details.get('gas_pump', 'N/A')
            transmission = details.get('transmission', 'N/A')
            power = details.get('speedometer', 'N/A')
            
            # Extract URL and image
            url = item.get('url', '')
            image = item.get('image', '')
            
            # Create title
            title = f"{make} {model}"
            
            # Create listing
            listing = CarListing(
                title=title,
                price=price,
                year=year,
                mileage=mileage,
                fuel_type=fuel_type,
                location=location,
                url=url,
                image=image,
                seller_name=seller_name,
                seller_type=seller_type,
                transmission=transmission,
                power=power
            )
            
            return listing
        
        except Exception as e:
            logger.error(f"Error parsing listing item: {str(e)}")
            return None
