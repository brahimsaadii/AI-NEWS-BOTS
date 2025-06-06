"""
Job Monitor - Monitors job boards for new job postings
"""

import asyncio
import logging
import re
import requests
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, quote_plus
from bs4 import BeautifulSoup
import time

logger = logging.getLogger(__name__)

class JobMonitor:
    """Monitors job boards for new job postings based on search criteria."""
    
    def __init__(self):
        """Initialize the job monitor."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Cache to avoid re-processing same job postings
        self.processed_jobs = set()
        self.last_check_time = {}
        
        # Supported job boards with their API/scraping configurations
        self.job_boards = {
            'indeed': {
                'base_url': 'https://www.indeed.com/jobs',
                'search_params': {'q': '{query}', 'l': '{location}', 'sort': 'date'},
                'selectors': {
                    'job_cards': '[data-jk]',
                    'title': 'h2.jobTitle a span',
                    'company': '.companyName',
                    'location': '.companyLocation',
                    'summary': '.job-snippet',
                    'date': '.date',
                    'link': 'h2.jobTitle a'
                }
            },
            'linkedin': {
                'base_url': 'https://www.linkedin.com/jobs/search',
                'search_params': {'keywords': '{query}', 'location': '{location}', 'sortBy': 'DD'},
                'selectors': {
                    'job_cards': '.job-search-card',
                    'title': '.base-search-card__title',
                    'company': '.base-search-card__subtitle',
                    'location': '.job-search-card__location',
                    'summary': '.job-search-card__summary',
                    'date': 'time',
                    'link': '.base-card__full-link'
                }
            },
            'glassdoor': {
                'base_url': 'https://www.glassdoor.com/Job/jobs.htm',
                'search_params': {'sc.keyword': '{query}', 'locT': 'C', 'locId': '1147401', 'jobType': ''},
                'selectors': {
                    'job_cards': '[data-test="job-listing"]',
                    'title': '[data-test="job-title"]',
                    'company': '[data-test="employer-name"]',
                    'location': '[data-test="job-location"]',
                    'summary': '[data-test="job-description"]',
                    'date': '[data-test="job-age"]',
                    'link': '[data-test="job-title"] a'
                }
            }
        }
    
    async def search_jobs(self, search_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for jobs based on configuration."""
        try:
            query = search_config.get('query', '')
            location = search_config.get('location', '')
            job_boards = search_config.get('job_boards', ['indeed'])
            filters = search_config.get('filters', {})
            
            if not query:
                logger.warning("No search query provided")
                return []
            
            all_jobs = []
            
            # Search each specified job board
            for board_name in job_boards:
                if board_name not in self.job_boards:
                    logger.warning(f"Unsupported job board: {board_name}")
                    continue
                
                try:
                    board_jobs = await self._search_job_board(board_name, query, location, filters)
                    all_jobs.extend(board_jobs)
                    logger.info(f"Found {len(board_jobs)} jobs from {board_name}")
                    
                    # Rate limiting between job boards
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error searching {board_name}: {str(e)}")
                    continue
            
            # Remove duplicates and filter results
            unique_jobs = self._deduplicate_jobs(all_jobs)
            filtered_jobs = self._filter_jobs(unique_jobs, filters)
            
            logger.info(f"Total jobs found: {len(all_jobs)}, unique: {len(unique_jobs)}, after filtering: {len(filtered_jobs)}")
            return filtered_jobs
            
        except Exception as e:
            logger.error(f"Error in job search: {str(e)}")
            return []
    
    async def _search_job_board(self, board_name: str, query: str, location: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search a specific job board."""
        try:
            board_config = self.job_boards[board_name]
            
            # Build search URL
            base_url = board_config['base_url']
            search_params = {}
            
            for param, template in board_config['search_params'].items():
                if '{query}' in template:
                    search_params[param] = template.format(query=quote_plus(query))
                elif '{location}' in template:
                    search_params[param] = template.format(location=quote_plus(location))
                else:
                    search_params[param] = template
            
            # Make request
            response = self.session.get(base_url, params=search_params, timeout=30)
            response.raise_for_status()
            
            # Parse results
            soup = BeautifulSoup(response.text, 'html.parser')
            jobs = await self._parse_job_listings(soup, board_config, board_name)
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error searching {board_name}: {str(e)}")
            return []
    
    async def _parse_job_listings(self, soup: BeautifulSoup, board_config: Dict[str, Any], board_name: str) -> List[Dict[str, Any]]:
        """Parse job listings from HTML."""
        try:
            jobs = []
            selectors = board_config['selectors']
            
            # Find all job cards
            job_cards = soup.select(selectors['job_cards'])
            
            for card in job_cards[:20]:  # Limit to first 20 results
                try:
                    job_data = {
                        'source': board_name,
                        'scraped_at': datetime.now()
                    }
                    
                    # Extract job details
                    title_elem = card.select_one(selectors['title'])
                    if title_elem:
                        job_data['title'] = title_elem.get_text(strip=True)
                    
                    company_elem = card.select_one(selectors['company'])
                    if company_elem:
                        job_data['company'] = company_elem.get_text(strip=True)
                    
                    location_elem = card.select_one(selectors['location'])
                    if location_elem:
                        job_data['location'] = location_elem.get_text(strip=True)
                    
                    summary_elem = card.select_one(selectors['summary'])
                    if summary_elem:
                        job_data['summary'] = summary_elem.get_text(strip=True)[:500]
                    
                    date_elem = card.select_one(selectors['date'])
                    if date_elem:
                        job_data['posted_date'] = date_elem.get_text(strip=True)
                    
                    link_elem = card.select_one(selectors['link'])
                    if link_elem:
                        href = link_elem.get('href', '')
                        if href:
                            if href.startswith('/'):
                                href = urljoin(board_config['base_url'], href)
                            elif not href.startswith('http'):
                                href = urljoin(board_config['base_url'], href)
                            job_data['url'] = href
                    
                    # Generate unique job ID
                    job_id = self._generate_job_id(job_data)
                    job_data['id'] = job_id
                    
                    # Only add if we have essential data
                    if job_data.get('title') and job_data.get('company'):
                        jobs.append(job_data)
                    
                except Exception as e:
                    logger.debug(f"Error parsing job card: {str(e)}")
                    continue
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error parsing job listings: {str(e)}")
            return []
    
    def _generate_job_id(self, job_data: Dict[str, Any]) -> str:
        """Generate a unique ID for a job posting."""
        title = job_data.get('title', '')
        company = job_data.get('company', '')
        source = job_data.get('source', '')
        
        # Create a simple hash-like ID
        job_string = f"{title}_{company}_{source}".lower()
        job_string = re.sub(r'[^a-zA-Z0-9_]', '', job_string)
        return job_string[:50]
    
    def _deduplicate_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate job postings."""
        seen_ids = set()
        unique_jobs = []
        
        for job in jobs:
            job_id = job.get('id')
            if job_id and job_id not in seen_ids:
                seen_ids.add(job_id)
                unique_jobs.append(job)
        
        return unique_jobs
    
    def _filter_jobs(self, jobs: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter jobs based on criteria."""
        try:
            filtered_jobs = []
            
            exclude_keywords = filters.get('exclude_keywords', [])
            required_keywords = filters.get('required_keywords', [])
            max_age_days = filters.get('max_age_days', 7)
            
            for job in jobs:
                # Check exclude keywords
                if exclude_keywords:
                    job_text = f"{job.get('title', '')} {job.get('summary', '')}".lower()
                    if any(keyword.lower() in job_text for keyword in exclude_keywords):
                        continue
                
                # Check required keywords
                if required_keywords:
                    job_text = f"{job.get('title', '')} {job.get('summary', '')}".lower()
                    if not any(keyword.lower() in job_text for keyword in required_keywords):
                        continue
                
                # Check if already processed
                if job.get('id') in self.processed_jobs:
                    continue
                
                filtered_jobs.append(job)
            
            return filtered_jobs
            
        except Exception as e:
            logger.error(f"Error filtering jobs: {str(e)}")
            return jobs
    
    def mark_as_processed(self, job_id: str):
        """Mark a job as processed."""
        self.processed_jobs.add(job_id)
    
    def get_processed_count(self) -> int:
        """Get count of processed jobs."""
        return len(self.processed_jobs)
    
    async def test_search(self, query: str, location: str = "") -> Dict[str, Any]:
        """Test job search functionality."""
        try:
            test_config = {
                'query': query,
                'location': location,
                'job_boards': ['indeed'],  # Use only Indeed for testing
                'filters': {
                    'max_age_days': 7,
                    'required_keywords': [],
                    'exclude_keywords': []
                }
            }
            
            jobs = await self.search_jobs(test_config)
            
            return {
                'success': True,
                'jobs_found': len(jobs),
                'sample_jobs': jobs[:3] if jobs else [],
                'test_query': query,
                'test_location': location
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'jobs_found': 0,
                'sample_jobs': [],
                'test_query': query,
                'test_location': location
            }
