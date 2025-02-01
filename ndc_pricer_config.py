from datetime import datetime, timedelta

# Global Configuration Settings
CONFIG = {
    "base_url": "https://letenky.studentagency.cz/",
    "selectors": {
        # Loader spinner displayed while the page is loading
        "loader": ".loader",
        # The container for the list of offers
        "offers_list": "#airticket-offer-list",
        # Individual offer items within the list
        "offer_item": ".airticketOfferItem",
        # Selector for upsell buttons or elements
        "upsell_class": "tariff-btn.smaller",
    },
    "timeouts": {
        "page_load": 90000,  # 90 seconds
        "selector_wait": 60000,  # 60 seconds
    },
}

def find_next_weekday(start_date, target_weekday):
    """
    Return the date of the first day on or after start_date 
    that has weekday = target_weekday.
    Monday=0, Tuesday=1, Wednesday=2, Thursday=3,
    Friday=4, Saturday=5, Sunday=6
    """
    while start_date.weekday() != target_weekday:
        start_date += timedelta(days=1)
    return start_date

def get_test_dates():
    """
    1) departure_date_1: first Friday >= 30 days from today's date
    2) departure_date_2: the Sunday of the *following* week (9 days after that Friday)
    """
    # Get today's date (no time component)
    today = datetime.now().date()
    
    # Step 1: Jump 30 days ahead
    date_30 = today + timedelta(days=30)
    
    # Step 2: find next (or same) Friday (weekday=4)
    departure_date_1 = find_next_weekday(date_30, 4)
    
    # Step 3: next week's Sunday is +9 days from that Friday
    departure_date_2 = departure_date_1 + timedelta(days=9)
    
    # Format and return strings: YYYY-MM-DD
    return departure_date_1.strftime("%Y-%m-%d"), departure_date_2.strftime("%Y-%m-%d")
