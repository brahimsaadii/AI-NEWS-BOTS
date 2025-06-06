"""
Gmail Client - Handles Gmail API authentication and email fetching
"""

import os
import json
import base64
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class GmailClient:
    """Gmail API client for fetching and processing emails."""
    
    # Gmail API scopes
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
    def __init__(self, credentials_path: str, token_path: str):
        """Initialize Gmail client with credentials."""
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self.credentials = None
    
    async def authenticate(self) -> bool:
        """Authenticate with Gmail API."""
        try:
            # Load existing token if available
            if os.path.exists(self.token_path):
                self.credentials = Credentials.from_authorized_user_file(
                    self.token_path, self.SCOPES
                )
            
            # If no valid credentials, run OAuth flow
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_path):
                        logger.error(f"Gmail credentials file not found: {self.credentials_path}")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.SCOPES
                    )
                    self.credentials = flow.run_local_server(port=0)
                
                # Save the credentials for future use
                with open(self.token_path, 'w') as token:
                    token.write(self.credentials.to_json())
            
            # Build the Gmail service
            self.service = build('gmail', 'v1', credentials=self.credentials)
            logger.info("Gmail authentication successful")
            return True
            
        except Exception as e:
            logger.error(f"Gmail authentication failed: {e}")
            return False
    
    async def get_recent_emails(self, 
                               query: str = "", 
                               max_results: int = 10,
                               hours_back: int = 24) -> List[Dict[str, Any]]:
        """Get recent emails based on query."""
        try:
            if not self.service:
                if not await self.authenticate():
                    return []
            
            # Calculate date range
            after_date = datetime.now() - timedelta(hours=hours_back)
            after_timestamp = int(after_date.timestamp())
            
            # Build search query
            search_query = f"after:{after_timestamp}"
            if query:
                search_query += f" {query}"
            
            # Search for messages
            result = self.service.users().messages().list(
                userId='me',
                q=search_query,
                maxResults=max_results
            ).execute()
            
            messages = result.get('messages', [])
            
            # Get full message details
            emails = []
            for message in messages:
                email_data = await self._get_email_details(message['id'])
                if email_data:
                    emails.append(email_data)
            
            logger.info(f"Retrieved {len(emails)} emails")
            return emails
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting recent emails: {e}")
            return []
    
    async def get_newsletter_emails(self, 
                                   sender_filters: List[str] = None,
                                   subject_filters: List[str] = None,
                                   hours_back: int = 24) -> List[Dict[str, Any]]:
        """Get newsletter emails based on filters."""
        try:
            # Build query for newsletters
            query_parts = []
            
            # Add sender filters
            if sender_filters:
                sender_query = " OR ".join([f"from:{sender}" for sender in sender_filters])
                query_parts.append(f"({sender_query})")
            
            # Add subject filters
            if subject_filters:
                subject_query = " OR ".join([f"subject:{subject}" for subject in subject_filters])
                query_parts.append(f"({subject_query})")
            
            # Common newsletter indicators
            newsletter_indicators = [
                "newsletter", "digest", "weekly", "daily", "update", 
                "roundup", "briefing", "summary"
            ]
            newsletter_query = " OR ".join([f"subject:{term}" for term in newsletter_indicators])
            query_parts.append(f"({newsletter_query})")
            
            # Combine all filters
            if query_parts:
                query = " OR ".join(query_parts)
            else:
                query = newsletter_query
            
            return await self.get_recent_emails(query, max_results=20, hours_back=hours_back)
            
        except Exception as e:
            logger.error(f"Error getting newsletter emails: {e}")
            return []
    
    async def _get_email_details(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific email."""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = {}
            for header in message['payload'].get('headers', []):
                headers[header['name'].lower()] = header['value']
            
            # Extract body
            body = await self._extract_email_body(message['payload'])
            
            # Extract date
            date_str = headers.get('date', '')
            received_date = self._parse_email_date(date_str)
            
            email_data = {
                'id': message_id,
                'subject': headers.get('subject', ''),
                'sender': headers.get('from', ''),
                'date': received_date,
                'body': body,
                'snippet': message.get('snippet', ''),
                'thread_id': message.get('threadId', ''),
                'labels': message.get('labelIds', [])
            }
            
            return email_data
            
        except Exception as e:
            logger.error(f"Error getting email details for {message_id}: {e}")
            return None
    
    async def _extract_email_body(self, payload: Dict) -> str:
        """Extract email body from payload."""
        try:
            body = ""
            
            # Check if it's multipart
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data', '')
                        if data:
                            body = base64.urlsafe_b64decode(data).decode('utf-8')
                            break
                    elif part['mimeType'] == 'text/html' and not body:
                        data = part['body'].get('data', '')
                        if data:
                            # For now, store HTML as-is, could parse later
                            body = base64.urlsafe_b64decode(data).decode('utf-8')
            else:
                # Single part message
                if payload['mimeType'] in ['text/plain', 'text/html']:
                    data = payload['body'].get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
            
            return body
            
        except Exception as e:
            logger.error(f"Error extracting email body: {e}")
            return ""
    
    def _parse_email_date(self, date_str: str) -> Optional[datetime]:
        """Parse email date string to datetime object."""
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except Exception as e:
            logger.error(f"Error parsing email date {date_str}: {e}")
            return None
    
    async def mark_as_read(self, message_id: str) -> bool:
        """Mark an email as read."""
        try:
            if not self.service:
                return False
            
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error marking email as read: {e}")
            return False
    
    async def add_label(self, message_id: str, label_name: str) -> bool:
        """Add a label to an email."""
        try:
            if not self.service:
                return False
            
            # Get or create label
            label_id = await self._get_or_create_label(label_name)
            if not label_id:
                return False
            
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': [label_id]}
            ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding label to email: {e}")
            return False
    
    async def _get_or_create_label(self, label_name: str) -> Optional[str]:
        """Get existing label or create new one."""
        try:
            # List existing labels
            result = self.service.users().labels().list(userId='me').execute()
            labels = result.get('labels', [])
            
            # Check if label exists
            for label in labels:
                if label['name'] == label_name:
                    return label['id']
            
            # Create new label
            label_object = {
                'name': label_name,
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }
            
            created_label = self.service.users().labels().create(
                userId='me',
                body=label_object
            ).execute()
            
            return created_label['id']
            
        except Exception as e:
            logger.error(f"Error getting/creating label {label_name}: {e}")
            return None
