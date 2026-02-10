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
        if entry.get('ff:impact', '').lower() == 'high':
            news_events.append({
                'title': entry.title,
                'currency': entry.get('ff:symbol', ''),
                # Parse FF time format: 'Fri Sep 20 08:30:00'
                'time': datetime.strptime(entry.get('ff:date', '') + " " + entry.get('ff:time', ''),
                                          '%a %b %d %Y %I:%M%p').replace(tzinfo=timezone.utc)
            })
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
