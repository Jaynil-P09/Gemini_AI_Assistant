import logging
from livekit.agents import function_tool, RunContext
import requests
from langchain_community.tools import DuckDuckGoSearchRun
import os
import smtplib
from email.mime.multipart import MIMEMultipart  
from email.mime.text import MIMEText
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Gmail API configuration
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.readonly']
GMAIL_CREDENTIALS_FILE = 'gmail_token.pickle'

# Google Calendar API configuration
CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar']
CALENDAR_CREDENTIALS_FILE = 'calender_token.pickle'
CALENDAR_ID = 'primary'

def get_gmail_service():
    """Get authenticated Gmail service."""
    creds = None
    if os.path.exists(GMAIL_CREDENTIALS_FILE):
        with open(GMAIL_CREDENTIALS_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                return None, "Gmail credentials not found. Please ensure credentials.json exists."
            
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)
    
        with open(GMAIL_CREDENTIALS_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    try:
        service = build('gmail', 'v1', credentials=creds)
        return service, None
    except Exception as e:
        return None, f"Failed to build Gmail service: {str(e)}"

def get_google_calendar_service():
    creds = None
    
    if os.path.exists(CALENDAR_CREDENTIALS_FILE):
        with open(CALENDAR_CREDENTIALS_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                return None, "Google Calendar credentials not found. Please ensure credentials.json exists."
            
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', CALENDAR_SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(CALENDAR_CREDENTIALS_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    try:
        service = build('calendar', 'v3', credentials=creds)
        return service, None
    except Exception as e:
        return None, f"Failed to build calendar service: {str(e)}"

@function_tool()
async def get_weather(
    context: RunContext, 
    city: str) -> str:
    """
    Get the current weather for a given city.
    """
    try:
        response = requests.get(
            f"https://wttr.in/{city}?format=3")
        if response.status_code == 200:
            logging.info(f"Weather for {city}: {response.text.strip()}")
            return response.text.strip()   
        else:
            logging.error(f"Failed to get weather for {city}: {response.status_code}")
            return f"Could not retrieve weather for {city}."
    except Exception as e:
        logging.error(f"Error retrieving weather for {city}: {e}")
        return f"An error occurred while retrieving weather for {city}." 

@function_tool()
async def search_web(
    context: RunContext,
    query: str) -> str:
    try:
        results = DuckDuckGoSearchRun().run(tool_input=query)
        logging.info(f"Search results for '{query}': {results}")
        return results
    except Exception as e:
        logging.error(f"Error searching the web for '{query}': {e}")
        return f"An error occurred while searching the web for '{query}'."    

@function_tool()
async def send_email(
    context: RunContext,
    to_email: str,
    subject: str,
    message: str,
    cc_email: Optional[str] = None,
    bcc_email: Optional[str] = None
) -> str:
    try:
        service, error = get_gmail_service()
        if error:
            return f"Gmail API authentication failed: {error}"
        
        # Create email message
        msg = MIMEMultipart()
        msg['to'] = to_email
        msg['subject'] = subject
        
        # Add CC if provided
        if cc_email:
            msg['cc'] = cc_email
        
        # Add BCC if provided
        if bcc_email:
            msg['bcc'] = bcc_email
        
        # Add message body
        msg.attach(MIMEText(message, 'plain'))
        
        # Convert to string and encode
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
        
        # Prepare recipients list
        recipients = [to_email]
        if cc_email:
            recipients.append(cc_email)
        if bcc_email:
            recipients.append(bcc_email)
        
        # Send email via Gmail API
        try:
            message_body = {'raw': raw_message}
            sent_message = service.users().messages().send(userId='me', body=message_body).execute()
            
            logging.info(f"Email sent successfully via Gmail API to {to_email}")
            
            response = f"Email sent successfully via Gmail API\n"
            response += f"To: {to_email}\n"
            response += f"Subject: {subject}\n"
            if cc_email:
                response += f"CC: {cc_email}\n"
            if bcc_email:
                response += f"BCC: {bcc_email}\n"
            response += f"Message ID: {sent_message['id']}"
            
            return response
            
        except HttpError as e:
            logging.error(f"Gmail API error sending email: {e}")
            return f"Failed to send email via Gmail API: {str(e)}"
            
    except Exception as e:
        logging.error(f"Error sending email via Gmail API: {e}")
        return f"An error occurred while sending email via Gmail API: {str(e)}"

@function_tool()
async def read_messages(
    context: RunContext,
    query: str = "",
    max_results: int = 10
) -> str:
    try:
        service, error = get_gmail_service()
        if error:
            return f"Gmail API authentication failed: {error}"
        
        # Get messages
        if query:
            messages_result = service.users().messages().list(
                userId='me', 
                q=query, 
                maxResults=max_results
            ).execute()
        else:
            messages_result = service.users().messages().list(
                userId='me', 
                maxResults=max_results
            ).execute()
        
        messages = messages_result.get('messages', [])
        
        if not messages:
            if query:
                return f"No messages found matching query: '{query}'"
            else:
                return "No messages found in inbox"
        
        result = f"📧 Gmail Messages"
        if query:
            result += f" matching '{query}'"
        result += f" (showing {len(messages)}):\n"
        
        for i, message in enumerate(messages, 1):
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            
            # Extract headers
            headers = msg['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
            
            result += f"\n{i}. {subject}\n"
            result += f"   From: {sender}\n"
            result += f"   Date: {date}\n"
            result += f"   Message ID: {message['id']}\n"
        
        return result
        
    except HttpError as e:
        logging.error(f"Gmail API error reading messages: {e}")
        return f"Gmail API error: {str(e)}"
    except Exception as e:
        logging.error(f"Error reading Gmail messages: {e}")
        return f"An error occurred while reading Gmail messages: {str(e)}"

@function_tool()
async def search_gmail(
    context: RunContext,
    search_query: str,
    max_results: int = 10
) -> str:
    try:
        service, error = get_gmail_service()
        if error:
            return f"Gmail API authentication failed: {error}"
        
        # Search Gmail
        messages_result = service.users().messages().list(
            userId='me', 
            q=search_query, 
            maxResults=max_results
        ).execute()
        
        messages = messages_result.get('messages', [])
        
        if not messages:
            return f"No messages found matching search query: '{search_query}'"
        
        result = f"🔍 Gmail Search Results for '{search_query}' (showing {len(messages)}):\n"
        
        for i, message in enumerate(messages, 1):

            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            
            headers = msg['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
            
            result += f"\n{i}. {subject}\n"
            result += f"   From: {sender}\n"
            result += f"   Date: {date}\n"
            result += f"   Message ID: {message['id']}\n"
        
        return result
        
    except HttpError as e:
        logging.error(f"Gmail API error searching: {e}")
        return f"Gmail API error: {str(e)}"
    except Exception as e:
        logging.error(f"Error searching Gmail: {e}")
        return f"An error occurred while searching Gmail: {str(e)}"

@function_tool()
async def create_google_calendar_event(
    context: RunContext,
    title: str,
    date: str,
    time: str,
    duration_minutes: int = 60,
    description: str = "",
    location: str = "",
    attendees: str = ""
) -> str:
    try:
        service, error = get_google_calendar_service()
        if error:
            return f"Google Calendar authentication failed: {error}"
        
        # Parse date and time
        event_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        end_datetime = event_datetime + timedelta(minutes=duration_minutes)
        
        # Format for Google Calendar API
        start_time = event_datetime.isoformat() + 'Z'
        end_time = end_datetime.isoformat() + 'Z'
        
        # Prepare attendees list
        attendee_list = []
        if attendees:
            for email in attendees.split(','):
                email = email.strip()
                if email:
                    attendee_list.append({'email': email})
        
        # Create event body
        event_body = {
            'summary': title,
            'description': description,
            'location': location,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',
            },
            'attendees': attendee_list,
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                    {'method': 'popup', 'minutes': 30},       # 30 minutes before
                ],
            },
        }
        
        event = service.events().insert(
            calendarId=CALENDAR_ID,
            body=event_body,
            sendUpdates='all' if attendee_list else 'none'
        ).execute()
        
        logging.info(f"Google Calendar event created: {title} on {date} at {time}")
        
        # Format response
        response = f"Event '{title}' created successfully in Google Calendar!\n"
        response += f" Date: {date}\n"
        response += f" Time: {time} ({duration_minutes} minutes)\n"
        if location:
            response += f" Location: {location}\n"
        if attendees:
            response += f" Attendees: {attendees}\n"
        response += f" Event ID: {event['id']}"
        
        return response
        
    except ValueError as e:
        return f"Invalid date/time format. Please use YYYY-MM-DD for date and HH:MM for time. Error: {str(e)}"
    except HttpError as e:
        logging.error(f"Google Calendar API error: {e}")
        return f"Google Calendar API error: {str(e)}"
    except Exception as e:
        logging.error(f"Error creating Google Calendar event: {e}")
        return f"An error occurred while creating the Google Calendar event: {str(e)}"

@function_tool()
async def view_google_calendar(
    context: RunContext,
    date: str = None,
    days_ahead: int = 7,
    max_results: int = 10
) -> str:
    try:
        service, error = get_google_calendar_service()
        if error:
            return f"Google Calendar authentication failed: {error}"
        
        # Calculate time range
        now = datetime.utcnow()
        if date:
            # View events for specific date
            target_date = datetime.strptime(date, "%Y-%m-%d")
            start_time = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            result_title = f"Events for {date}"
        else:
            # View upcoming events
            start_time = now
            end_time = now + timedelta(days=days_ahead)
            result_title = f"Upcoming events (next {days_ahead} days)"
        
        # Format for API
        start_time_str = start_time.isoformat() + 'Z'
        end_time_str = end_time.isoformat() + 'Z'
        
        # Get events from Google Calendar
        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=start_time_str,
            timeMax=end_time_str,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            if date:
                return f"No events found for {date}"
            else:
                return f"No upcoming events in the next {days_ahead} days."
        
        # Format results
        result = f"{result_title}:\n"
        
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            # Parse datetime
            if 'T' in start:  # Has time
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                time_str = f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"
            else:  # All-day event
                start_dt = datetime.fromisoformat(start)
                time_str = "All day"
            
            result += f"\n• {event['summary']}\n"
            result += f"  📅 {start_dt.strftime('%Y-%m-%d')}\n"
            result += f"  🕐 {time_str}\n"
            
            if event.get('location'):
                result += f"  📍 {event['location']}\n"
            if event.get('description'):
                result += f"  📝 {event['description']}\n"
            if event.get('attendees'):
                attendee_emails = [a['email'] for a in event['attendees']]
                result += f"  👥 Attendees: {', '.join(attendee_emails)}\n"
            result += f"  🔗 Event ID: {event['id']}\n"
        
        return result
        
    except ValueError as e:
        return f"Invalid date format. Please use YYYY-MM-DD format. Error: {str(e)}"
    except HttpError as e:
        logging.error(f"Google Calendar API error: {e}")
        return f"Google Calendar API error: {str(e)}"
    except Exception as e:
        logging.error(f"Error viewing Google Calendar: {e}")
        return f"An error occurred while viewing Google Calendar: {str(e)}"

@function_tool()
async def delete_google_calendar_event(
    context: RunContext,  # type: ignore
    event_id: str
) -> str:
    """
    Delete an event from Google Calendar by ID.
    
    Args:
        event_id: ID of the event to delete
    """
    try:
        service, error = get_google_calendar_service()
        if error:
            return f"Google Calendar authentication failed: {error}"
        
        # Get event details before deletion
        try:
            event = service.events().get(calendarId=CALENDAR_ID, eventId=event_id).execute()
            event_title = event.get('summary', 'Unknown Event')
        except HttpError:
            event_title = 'Unknown Event'
        
        # Delete the event
        service.events().delete(
            calendarId=CALENDAR_ID,
            eventId=event_id,
            sendUpdates='all'
        ).execute()
        
        logging.info(f"Google Calendar event deleted: {event_title}")
        return f"Event '{event_title}' deleted successfully from Google Calendar."
        
    except HttpError as e:
        if e.resp.status == 404:
            return f"Event with ID {event_id} not found in Google Calendar."
        logging.error(f"Google Calendar API error: {e}")
        return f"Google Calendar API error: {str(e)}"
    except Exception as e:
        logging.error(f"Error deleting Google Calendar event: {e}")
        return f"An error occurred while deleting the Google Calendar event: {str(e)}"

@function_tool()
async def search_google_calendar_events(
    context: RunContext,  # type: ignore
    search_term: str,
    max_results: int = 10
) -> str:
    """
    Search for events in Google Calendar by title, description, or location.
    
    Args:
        search_term: Text to search for in events
        max_results: Maximum number of events to return (default: 10)
    """
    try:
        service, error = get_google_calendar_service()
        if error:
            return f"Google Calendar authentication failed: {error}"
        
        # Search in Google Calendar
        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            q=search_term,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return f"No events found matching '{search_term}' in Google Calendar."
        
        result = f"Events matching '{search_term}' in Google Calendar:\n"
        
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            
            # Parse datetime
            if 'T' in start:  # Has time
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                time_str = start_dt.strftime('%Y-%m-%d %H:%M')
            else:  # All-day event
                start_dt = datetime.fromisoformat(start)
                time_str = start_dt.strftime('%Y-%m-%d') + " (All day)"
            
            result += f"\n• {event['summary']}\n"
            result += f"  📅 {time_str}\n"
            
            if event.get('location'):
                result += f"  📍 {event['location']}\n"
            if event.get('description'):
                result += f"  📝 {event['description']}\n"
            result += f"  🔗 Event ID: {event['id']}\n"
        
        return result
        
    except HttpError as e:
        logging.error(f"Google Calendar API error: {e}")
        return f"Google Calendar API error: {str(e)}"
    except Exception as e:
        logging.error(f"Error searching Google Calendar events: {e}")
        return f"An error occurred while searching Google Calendar events: {str(e)}"

@function_tool()
async def list_google_calendars(
    context: RunContext  # type: ignore
) -> str:
    """
    List all available Google Calendars for the authenticated user.
    """
    try:
        service, error = get_google_calendar_service()
        if error:
            return f"Google Calendar authentication failed: {error}"
        
        # Get calendar list
        calendar_list = service.calendarList().list().execute()
        calendars = calendar_list.get('items', [])
        
        if not calendars:
            return "No calendars found."
        
        result = "Available Google Calendars:\n"
        
        for calendar in calendars:
            primary = " (Primary)" if calendar.get('primary', False) else ""
            result += f"\n• {calendar['summary']}{primary}\n"
            result += f"  📧 {calendar['id']}\n"
            if calendar.get('description'):
                result += f"  📝 {calendar['description']}\n"
            if calendar.get('accessRole'):
                result += f"  🔐 Access: {calendar['accessRole']}\n"
        
        return result
        
    except HttpError as e:
        logging.error(f"Google Calendar API error: {e}")
        return f"Google Calendar API error: {str(e)}"
    except Exception as e:
        logging.error(f"Error listing Google Calendars: {e}")
        return f"An error occurred while listing Google Calendars: {str(e)}"
