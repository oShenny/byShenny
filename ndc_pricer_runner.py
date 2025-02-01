import asyncio
import json
import logging
import subprocess
from playwright.async_api import async_playwright

from ndc_pricer_config import CONFIG, get_test_dates
from ndc_pricer_tests import process_test_set
from ndc_pricer_utils import setup_logger

# Setup logging to include console output
setup_logger()

async def run_test_set_with_semaphore(semaphore, playwright, test_set_name, urls, config):
    """
    Acquire a slot from the semaphore, then run the existing process_test_set function.
    This ensures we only run up to CONCURRENCY_LIMIT test sets at once.
    """
    async with semaphore:
        return await process_test_set(playwright, test_set_name, urls, config)

async def main():
    logging.info("Starting NDC Pricer Tests...")

    # Generate dynamic test dates
    departure_date_1, departure_date_2 = get_test_dates()
    logging.info(f"Generated test dates: Departure 1: {departure_date_1}, Departure 2: {departure_date_2}")

    # Load test sets from JSON
    try:
        with open("test_urls.json", "r") as file:
            test_sets = json.load(file)
        logging.info(f"Loaded {len(test_sets)} test sets from 'test_urls.json'.")
    except FileNotFoundError:
        logging.error("test_urls.json file not found. Ensure the file is in the correct location.")
        return

    # --------------------------------------------------
    # NEW: Concurrency limit
    # --------------------------------------------------
    CONCURRENCY_LIMIT = 2  # Adjust as needed
    logging.info(f"Using concurrency limit = {CONCURRENCY_LIMIT}")
    # --------------------------------------------------

    # Run the test sets using Playwright
    async with async_playwright() as playwright:
        # Create the semaphore
        semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

        tasks = []
        for test_set_name, urls in test_sets.items():
            logging.info(f"Preparing test set: {test_set_name} with {len(urls)} URLs.")
            # Replace placeholders with your dynamic dates
            final_urls = [
                url.replace("{departure_date_1}", departure_date_1)
                   .replace("{departure_date_2}", departure_date_2)
                for url in urls
            ]
            # Instead of calling process_test_set directly, we wrap it
            tasks.append(
                run_test_set_with_semaphore(semaphore, playwright, test_set_name, final_urls, CONFIG)
            )

        logging.info("Starting tests for all test sets...")

        # Gather results - only two tasks will run concurrently
        results_list = await asyncio.gather(*tasks)

    # Combine results and save to a file
    results = {test_set_name: result for test_set_name, result in zip(test_sets.keys(), results_list)}
    with open("results_pricer.json", "w") as result_file:
        json.dump(results, result_file, indent=4)
    logging.info("All tests completed successfully. Results saved to 'results_pricer.json'.")

    # Run the filtering script
    try:
        logging.info("Running the results filtering script...")
        subprocess.run(["python", "ndc_pricer_filter.py"], check=True)
        logging.info("Results filtering completed successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running the filtering script: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.error("Execution interrupted manually. Exiting gracefully.")
