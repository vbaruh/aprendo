import threading
import os

thread_state = threading.local()

from aprendo.translations.csv import CsvTranslations


def translations() -> CsvTranslations:
    if hasattr(thread_state, 'csv') and thread_state.csv:
        return thread_state.csv

    csv_dir = os.environ.get('APRENDO_CSV_DIR', './')
    csv_path = os.path.join(csv_dir, 'translations.csv')

    csv = CsvTranslations(csv_path)
    if os.path.exists(csv_path):
        csv.load_translations()
    thread_state.csv = csv

    return csv