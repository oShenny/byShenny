import json
import os
import csv
from datetime import datetime
import logging

def save_filtered_results(results_file, output_folder="csv_results"):
    """
    Filter results from a JSON file and save filtered results into a timestamped CSV.

    :param results_file: Path to the JSON results file.
    :param output_folder: Directory to store the CSV results.
    """
    try:
        # Load results
        with open(results_file, "r") as file:
            results = json.load(file)

        # Prepare filtered results
        filtered_results = []
        for test_set_name, test_cases in results.items():
            for test_case, details in test_cases.items():
                issue = None

                # Case 1: is_ndc is False
                if not details.get("is_ndc", False):
                    issue = "No NDC offers found"

                # Case 2: is_ndc is True but ndc_position > 1
                elif details.get("is_ndc", False) and details.get("ndc_position") and details["ndc_position"] > 1:
                    issue = f"NDC offer found but at position {details['ndc_position']}"

                if issue:
                    filtered_results.append({
                        "airline": details.get("airline"),
                        "from": details.get("from"),
                        "to": details.get("to"),
                        "issue": issue
                    })

        # Ensure output folder exists
        os.makedirs(output_folder, exist_ok=True)

        # Generate timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_folder, f"filtered_results_{timestamp}.csv")

        # Save to CSV
        with open(output_file, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=["airline", "from", "to", "issue"])
            writer.writeheader()
            writer.writerows(filtered_results)

        logging.info(f"Filtered results saved to {output_file}.")
    except Exception as e:
        logging.error(f"Error saving filtered results: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
    results_file = "results_pricer.json"
    save_filtered_results(results_file)
