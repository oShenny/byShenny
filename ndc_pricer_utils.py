import asyncio
import logging
from colorlog import ColoredFormatter

# Logging Configuration
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_logger(log_file="ndc_pricer.log"):
    """
    Set up logging to log both to the console (with colors) and a file.

    :param log_file: Path to the log file
    """
    LOG_FORMAT = "%(asctime)s | %(log_color)s%(levelname)-8s%(reset)s | %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    LOG_COLORS = {
        "DEBUG": "white",
        "INFO": "cyan",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold_red",
    }

    # Configure colored logging for console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ColoredFormatter(LOG_FORMAT, datefmt=DATE_FORMAT, log_colors=LOG_COLORS))

    # Configure file logging without colors
    file_handler = logging.FileHandler(log_file, mode="a")
    file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", datefmt=DATE_FORMAT))

    # Set up the root logger
    logging.basicConfig(
        level=logging.INFO,
        handlers=[console_handler, file_handler],
    )


async def measure_load_time(page, url, config):
    """
    Navigate to the provided URL using the timeout from config["timeouts"]["page_load"].
    Also wait for network to be idle to follow any forced redirect fully.
    """
    try:
        start_time = asyncio.get_event_loop().time()

        # Use the 90s (or whatever you specified) from config
        response = await page.goto(
            url,
            timeout=config["timeouts"]["page_load"],
            wait_until="domcontentloaded"  # or "networkidle" if desired
        )

        # Optionally wait for the network to be idle
        await page.wait_for_load_state("networkidle", timeout=config["timeouts"]["page_load"])

        load_time = asyncio.get_event_loop().time() - start_time
        return round(load_time, 2), response.status
    except Exception as e:
        logging.error(f"Error accessing URL {url}: {e}")
        return None, None


async def apply_airline_filter(page, airline_name):
    """
    Expands filter blocks and clicks on the checkbox with the airline name.
    """
    try:
        await page.locator(".filter-block .toggle-visibility-link").first.click()
        await asyncio.sleep(2)  # small delay for DOM updates
        await page.locator(f".form-check-label:has-text('{airline_name}')").click()
        logging.info(f"Filter applied for airline: {airline_name}")
        # Wait until the offers list updates or is attached
        await page.wait_for_selector("#airticket-offer-list", state="attached", timeout=2000)
        await asyncio.sleep(2)  # small delay for DOM updates
    except Exception as e:
        logging.error(f"Unable to apply filter for {airline_name}: {e}")


def clean_price(price):
    """
    Clean up a price string by removing unnecessary whitespace and standardizing the format.
    """
    return " ".join(price.strip().split()).replace("\u00a0", " ").replace("Kč", "CZK")


def client_friendly_error(note):
    """
    Return a dictionary structure with a standardized error response.
    """
    logging.error(note)
    return {
        "has_upsell": False,
        "upsell_position": None,
        "first_offer_price": None,
        "upsell_prices": [],
        "note": note
    }
