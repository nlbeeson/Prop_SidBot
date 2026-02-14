from datetime import datetime, timezone

import feedparser

from config import NEWS_BUFFER_MINUTES


def fetch_high_impact_news():
    """Fetches high-impact news events from Forex Factory RSS."""
    # Forex Factory high-impact RSS feed
    url = "https://www.forexfactory.com/ff_calendar_thisweek.xml"
    feed = feedparser.parse(url)

    news_events = []
    for entry in feed.entries:
        # High impact events are usually marked 'High' or 'Critical'
        if entry.get('ff_impact', '').lower() == 'high':
            try:
                # ff_date: '09-18-2024' (or similar), ff_time: '8:30am'
                date_str = entry.get('ff_date', '')
                time_str = entry.get('ff_time', '')
                
                if not date_str or not time_str:
                    continue

                full_time_str = f"{date_str} {time_str}"
                # Adjust format based on typical FF RSS output: 'MM-DD-YYYY h:mmam'
                event_time = datetime.strptime(full_time_str, '%m-%d-%Y %I:%M%p').replace(tzinfo=timezone.utc)

                news_events.append({
                    'title': entry.title,
                    'currency': entry.get('ff_symbol', ''),
                    'time': event_time
                })
            except Exception as e:
                continue
    return news_events


def is_trading_blocked(symbol_currency, buffer_minutes=NEWS_BUFFER_MINUTES):
    """Checks if current time is within the buffer zone of a news event."""
    events = fetch_high_impact_news()
    now = datetime.now(timezone.utc)

    for event in events:
        # Only block if the currency matches the instrument being traded
        if event['currency'] in symbol_currency:
            time_diff = abs((event['time'] - now).total_seconds() / 60)
            if time_diff <= buffer_minutes:
                return True, event['title']

    return False, None
