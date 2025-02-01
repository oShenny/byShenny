import asyncio
import logging

from ndc_pricer_utils import (
    measure_load_time,
    apply_airline_filter,
    client_friendly_error,
    clean_price
)

async def detect_first_offer_price(page, config):
    try:
        await page.wait_for_selector(
            f"{config['selectors']['offers_list']} {config['selectors']['offer_item']}",
            timeout=config["timeouts"]["selector_wait"]
        )
        first_offer = page.locator(f"{config['selectors']['offers_list']} {config['selectors']['offer_item']}").nth(0)

        # If there are no offers, return None
        if not await first_offer.count():
            logging.warning("No offers available to detect the first offer price.")
            return None

        first_offer_price_raw = None
        for selector in ["strong.d-inline-block.d-md-block", "strong.text-nowrap"]:
            try:
                price_element = first_offer.locator(selector).nth(0)
                if await price_element.count():
                    first_offer_price_raw = await price_element.text_content()
                    logging.info(f"Price found using selector '{selector}': {first_offer_price_raw}")
                    break
            except Exception as e:
                logging.debug(f"Selector '{selector}' failed: {e}")

        if not first_offer_price_raw:
            logging.warning("No valid price found for the first offer.")
            return None

        first_offer_price = clean_price(first_offer_price_raw)
        logging.info(f"First offer price detected: {first_offer_price}")
        return first_offer_price
    except Exception as e:
        logging.error(f"Error detecting first offer price: {e}")
        return None


async def detect_ndc_offer(page, config):
    try:
        await page.wait_for_selector(
            f"{config['selectors']['offers_list']} {config['selectors']['offer_item']}",
            timeout=config["timeouts"]["selector_wait"]
        )
        offers = await page.locator(f"{config['selectors']['offers_list']} {config['selectors']['offer_item']}").all()

        if not offers:
            logging.info("No offers found on the page.")
            return client_friendly_error("No NDC offers found.")

        for idx, offer in enumerate(offers, start=1):
            logging.info(f"Processing offer {idx}...")

            # Check for flap (OKAMŽITÁ PLATBA)
            has_flap = await offer.locator(".flap.type-lowcost_offer").filter(
                has_text="OKAMŽITÁ PLATBA"
            ).count() > 0

            if has_flap:
                logging.info(f"Offer {idx}: Flap detected. Identified as NDC offer.")

                # --- Fallback approach for price retrieval ---
                ndc_price_raw = None
                for sel in ["strong.d-inline-block.d-md-block", "strong.text-nowrap"]:
                    price_element = offer.locator(sel).nth(0)
                    try:
                        # small wait for this element to attach or become visible
                        await price_element.wait_for(state="attached", timeout=2000)
                        if await price_element.count():
                            ndc_price_raw = await price_element.text_content()
                            logging.info(f"Offer {idx}: Price found using '{sel}': {ndc_price_raw}")
                            break
                    except Exception as e:
                        logging.debug(f"Selector '{sel}' for NDC price failed: {e}")

                if not ndc_price_raw:
                    logging.warning(f"Offer {idx}: Could not find a price element. Skipping.")
                    continue

                # Clean the price
                ndc_price = clean_price(ndc_price_raw)

                # Check for upsells
                upsell_locator = offer.locator(f".{config['selectors']['upsell_class']} strong.text-nowrap")
                upsell_prices_raw = await upsell_locator.all_text_contents()
                upsell_prices_cleaned = [clean_price(p) for p in upsell_prices_raw]

                if upsell_prices_cleaned:
                    logging.info(f"Offer {idx}: NDC offer with upsells detected: {upsell_prices_cleaned}")
                    return {
                        "is_ndc": True,
                        "ndc_position": idx,
                        "ndc_price": ndc_price,
                        "has_upsell": True,
                        "upsell_prices": upsell_prices_cleaned,
                        "note": None,
                    }

                # Flap-only NDC
                logging.info(f"Offer {idx}: Flap-only NDC offer detected.")
                return {
                    "is_ndc": True,
                    "ndc_position": idx,
                    "ndc_price": ndc_price,
                    "has_upsell": False,
                    "upsell_prices": [],
                    "note": "NDC offer detected, but no upsells.",
                }

        logging.info("No NDC offers with OKAMŽITÁ PLATBA found.")
        return client_friendly_error("No NDC offers found.")
    except Exception as e:
        logging.error(f"Error during NDC detection: {e}")
        return client_friendly_error("NDC detection failed.")


async def process_test_set(playwright, test_set_name, urls, config):
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()

    # -------------------------------------------------------
    # NEW: Set default timeouts based on config
    # This ensures all navigations and waits respect these timeouts.
    page.set_default_navigation_timeout(config["timeouts"]["page_load"])
    page.set_default_timeout(config["timeouts"]["selector_wait"])
    # -------------------------------------------------------

    results = {}

    # Example: "Test Set 6: Emirates" -> "Emirates"
    # (Make sure your test_set_name has the pattern "Test Set #: AirlineName")
    airline_name = test_set_name.split(": ")[1] if ": " in test_set_name else test_set_name

    for test_index, url in enumerate(urls, start=1):
        logging.info(f"[{test_set_name} | Test Case {test_index}] Processing URL: {url}")

        # Extract 'from' and 'to' destinations from the URL
        try:
            from_destination = url.split("departure_destination_1=")[1].split("&")[0]
            to_destination = url.split("arrival_destination_1=")[1].split("&")[0]
        except IndexError:
            logging.error(f"[{test_set_name} | Test Case {test_index}] Error parsing 'from' or 'to' from URL.")
            continue

        # Pass config to measure_load_time
        load_time, status_code = await measure_load_time(page, url, config)
        if load_time is None or status_code is None:
            logging.warning(f"[{test_set_name} | Test Case {test_index}] Skipping due to load time or status code failure.")
            continue

        logging.info(f"[{test_set_name} | Test Case {test_index}] Load time: {load_time}s, Status code: {status_code}")

        # Apply airline filter
        await apply_airline_filter(page, airline_name)

        # Detect the first offer price
        first_offer_price = await detect_first_offer_price(page, config)
        logging.info(f"[{test_set_name} | Test Case {test_index}] First offer price: {first_offer_price}")

        # Detect NDC offers
        ndc_details = await detect_ndc_offer(page, config)
        logging.info(f"[{test_set_name} | Test Case {test_index}] NDC details: {ndc_details}")

        # Only populate ndc_price if is_ndc is True
        ndc_price = ndc_details.get("ndc_price") if ndc_details.get("is_ndc", False) else None

        # Store results
        results[f"test_case_{test_index}"] = {
            "airline": airline_name,
            "from": from_destination,
            "to": to_destination,
            "url": url,
            "load_time": load_time,
            "status_code": status_code,
            "first_offer_price": first_offer_price,
            "is_ndc": ndc_details.get("is_ndc", False),
            "ndc_position": ndc_details.get("ndc_position"),
            "ndc_price": ndc_price,
            "has_upsell": ndc_details.get("has_upsell", False),
            "upsell_prices": ndc_details.get("upsell_prices", []),
            "note": ndc_details.get("note"),
        }

    await browser.close()
    return results
