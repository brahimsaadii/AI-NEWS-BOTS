"""
Job Monitor Bot - Monitors job boards for new job postings and generates tweets
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .base_bot import BaseBot
from utils.job_monitor import JobMonitor
from utils.text_generator import TextGenerator

logger = logging.getLogger(__name__)

class JobMonitorBot(BaseBot):
    """Job Monitor Bot for tracking job postings and generating tweets."""
    
    def __init__(self, bot_config: Dict[str, Any]):
        """Initialize Job Monitor bot with configuration."""
        super().__init__(bot_config)
        
        # Job monitor-specific configuration
        self.job_config = bot_config.get("job_config", {})
        self.search_queries = self.job_config.get("search_queries", [])
        self.location = self.job_config.get("location", "")
        self.job_boards = self.job_config.get("job_boards", ["indeed"])
        self.filters = self.job_config.get("filters", {})
        self.last_search_time = datetime.now() - timedelta(hours=24)
        
        # Initialize job monitor
        self.job_monitor = JobMonitor()
        
        # Initialize text generator
        self.text_generator = TextGenerator()
        
        # Processed jobs tracking
        self.processed_jobs = set()
        
        logger.info(f"Job Monitor Bot initialized for {len(self.search_queries)} queries")
    
    def get_bot_type(self) -> str:
        """Return the bot type identifier."""
        return "job_monitor"
    
    async def fetch_content(self) -> List[Dict[str, Any]]:
        """Fetch new job postings from configured sources."""
        try:
            if not self.search_queries:
                logger.warning(f"No search queries configured for bot {self.name}")
                return []
            
            all_jobs = []
            
            # Search for each configured query
            for query_config in self.search_queries:
                try:
                    query = query_config.get("query", "")
                    if not query:
                        logger.warning(f"Empty query in configuration: {query_config}")
                        continue
                    
                    logger.info(f"Searching for jobs: {query}")
                    
                    # Create search configuration
                    search_config = {
                        "query": query,
                        "location": query_config.get("location", self.location),
                        "job_boards": query_config.get("job_boards", self.job_boards),
                        "filters": {
                            **self.filters,
                            **query_config.get("filters", {})
                        }
                    }
                    
                    # Search for jobs
                    jobs = await self.job_monitor.search_jobs(search_config)
                    
                    # Filter out already processed jobs
                    new_jobs = [
                        job for job in jobs 
                        if job.get('id') not in self.processed_jobs
                    ]
                    
                    # Add query context to jobs
                    for job in new_jobs:
                        job['search_query'] = query
                        job['query_config'] = query_config
                        self.processed_jobs.add(job.get('id'))
                        self.job_monitor.mark_as_processed(job.get('id'))
                    
                    all_jobs.extend(new_jobs)
                    logger.info(f"Found {len(new_jobs)} new jobs for query: {query}")
                    
                except Exception as e:
                    logger.error(f"Error searching for jobs with query '{query_config.get('query', 'unknown')}': {str(e)}")
                    continue
            
            # Update last search time
            self.last_search_time = datetime.now()
            
            # Sort by relevance/recency
            all_jobs.sort(key=lambda x: x.get('scraped_at', datetime.min), reverse=True)
            
            logger.info(f"Job Monitor bot {self.name} found {len(all_jobs)} new jobs total")
            return all_jobs
            
        except Exception as e:
            logger.error(f"Error in Job Monitor bot {self.name} fetch_content: {str(e)}")
            return []
    
    async def process_content(self, content: Dict[str, Any]) -> Optional[str]:
        """Process job posting and generate tweet text."""
        try:
            # Extract key information
            title = content.get('title', '').strip()
            company = content.get('company', '').strip()
            location = content.get('location', '').strip()
            url = content.get('url', '')
            summary = content.get('summary', '').strip()
            search_query = content.get('search_query', '')
            
            if not title or not company:
                logger.warning(f"Missing title or company in job posting: {content}")
                return None
            
            # Prepare content for text generation
            processed_content = {
                'title': title,
                'company': company,
                'location': location,
                'content': summary[:300] if summary else f"{title} at {company}",  # Limit content length
                'url': url,
                'search_query': search_query,
                'type': 'job_posting'
            }
            
            # Generate tweet text
            tweet_text = await self.text_generator.generate_job_tweet(processed_content)
            
            if tweet_text:
                logger.info(f"Generated tweet for job: {title} at {company}")
                return tweet_text
            else:
                logger.warning(f"Failed to generate tweet for job: {title} at {company}")
                return None
                
        except Exception as e:
            logger.error(f"Error processing job content in Job Monitor bot {self.name}: {str(e)}")
            return None
    
    async def get_status_info(self) -> Dict[str, Any]:
        """Get current status information for this bot."""
        try:
            return {
                "type": self.get_bot_type(),
                "name": self.name,
                "running": self.running,
                "search_queries_count": len(self.search_queries),
                "job_boards_count": len(self.job_boards),
                "processed_jobs_count": len(self.processed_jobs),
                "last_search": self.last_search_time.strftime("%Y-%m-%d %H:%M:%S") if self.last_search_time else "Never",
                "location": self.location or "Any",
                "frequency": f"{self.frequency} hours",
                "auto_post": self.auto_post
            }
        except Exception as e:
            logger.error(f"Error getting status info for Job Monitor bot {self.name}: {str(e)}")
            return {}
    
    async def get_configuration_summary(self) -> str:
        """Get a human-readable configuration summary."""
        try:
            summary = f"💼 *Job Monitor Bot: {self.name}*\n\n"
            summary += f"📊 *Status:* {'Running' if self.running else 'Stopped'}\n"
            summary += f"⏰ *Frequency:* Every {self.frequency} hours\n"
            summary += f"🚀 *Auto-post:* {'Enabled' if self.auto_post else 'Disabled'}\n"
            summary += f"📍 *Location:* {self.location or 'Any'}\n\n"
            
            summary += f"🔍 *Search Queries ({len(self.search_queries)}):*\n"
            for i, query_config in enumerate(self.search_queries[:5], 1):  # Show first 5
                query = query_config.get('query', 'Unknown')
                summary += f"  {i}. {query}\n"
            
            if len(self.search_queries) > 5:
                summary += f"  ... and {len(self.search_queries) - 5} more\n"
            
            summary += f"\n🌐 *Job Boards ({len(self.job_boards)}):*\n"
            board_names = {
                'indeed': 'Indeed',
                'linkedin': 'LinkedIn',
                'glassdoor': 'Glassdoor'
            }
            for board in self.job_boards:
                summary += f"  • {board_names.get(board, board.title())}\n"
            
            if self.filters:
                summary += f"\n🎯 *Filters:*\n"
                if self.filters.get('required_keywords'):
                    summary += f"  • Required: {', '.join(self.filters['required_keywords'][:3])}\n"
                if self.filters.get('exclude_keywords'):
                    summary += f"  • Exclude: {', '.join(self.filters['exclude_keywords'][:3])}\n"
            
            summary += f"\n📈 *Stats:*\n"
            summary += f"  • Processed jobs: {len(self.processed_jobs)}\n"
            summary += f"  • Last search: {self.last_search_time.strftime('%Y-%m-%d %H:%M') if self.last_search_time else 'Never'}\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating configuration summary for Job Monitor bot {self.name}: {str(e)}")
            return f"Error generating summary for {self.name}"
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test job search connection and return results."""
        try:
            if not self.search_queries:
                return {
                    "success": False,
                    "message": "No search queries configured",
                    "details": {}
                }
            
            # Test first search query only for quick test
            query_config = self.search_queries[0]
            query = query_config.get('query', '')
            
            if not query:
                return {
                    "success": False,
                    "message": "Invalid search query configuration",
                    "details": {}
                }
            
            try:
                # Test job search
                test_result = await self.job_monitor.test_search(
                    query=query,
                    location=query_config.get('location', self.location)
                )
                
                return {
                    "success": test_result.get("success", False),
                    "message": "Job search test completed",
                    "details": {
                        "test_query": test_result.get("test_query"),
                        "test_location": test_result.get("test_location"),
                        "jobs_found": test_result.get("jobs_found", 0),
                        "sample_jobs": [
                            {
                                "title": job.get("title", ""),
                                "company": job.get("company", ""),
                                "source": job.get("source", "")
                            }
                            for job in test_result.get("sample_jobs", [])
                        ],
                        "error": test_result.get("error") if not test_result.get("success") else None
                    }
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "message": f"Job search test failed: {str(e)}",
                    "details": {"error": str(e)}
                }
            
        except Exception as e:
            logger.error(f"Error testing Job Monitor bot connection: {str(e)}")
            return {
                "success": False,
                "message": f"Test failed: {str(e)}",
                "details": {}
            }
