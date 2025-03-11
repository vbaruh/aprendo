import csv
import sqlite3
import logging

from typing import List, Tuple, Optional

from aprendo.translations.types import TranslationIdRange


logger = logging.getLogger(__name__)


class CsvTranslations:

    def __init__(self, csv_path: str) -> None:
        self._csv_path = csv_path
        self._conn = None

    def load_translations(self) -> None:
        if self._conn:
            return
        # Create in-memory database
        self._conn = sqlite3.connect(':memory:')
        self._init_db()

        # Read CSV file
        with open(self._csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header row

            # Use a transaction for better performance
            with self._conn:
                for spanish, bulgarian in reader:
                    # Clean the words
                    spanish = spanish.strip()
                    bulgarian = bulgarian.strip()

                    if not spanish or not bulgarian:
                        continue

                    # Insert Spanish word if not exists
                    self._conn.execute(
                        'INSERT OR IGNORE INTO spanish_words (word) VALUES (?)',
                        (spanish,)
                    )
                    spanish_id = self._conn.execute(
                        'SELECT id FROM spanish_words WHERE word = ?',
                        (spanish,)
                    ).fetchone()[0]

                    # Insert Bulgarian word if not exists
                    self._conn.execute(
                        'INSERT OR IGNORE INTO bulgarian_words (word) VALUES (?)',
                        (bulgarian,)
                    )
                    bulgarian_id = self._conn.execute(
                        'SELECT id FROM bulgarian_words WHERE word = ?',
                        (bulgarian,)
                    ).fetchone()[0]

                    # Create translation mapping
                    self._conn.execute(
                        'INSERT OR IGNORE INTO translations (spanish_id, bulgarian_id) VALUES (?, ?)',
                        (spanish_id, bulgarian_id)
                    )

    def get_translations(self, source_lang: str, target_lang: str) -> List[Tuple[int, str, str]]:
        """Get all translations as tuples of (id, source word, target word).

        Args:
            source_lang: Source language code ('es' or 'bg')
            target_lang: Target language code ('es' or 'bg')

        Returns:
            List of tuples containing (id, source word, target translation)
            ordered by id
        """
        if source_lang == 'es':
            cursor = self._conn.execute("""
                SELECT
                    tr.id,
                    s.word as source_word,
                    b.word as target_word
                FROM spanish_words s
                JOIN translations tr ON tr.spanish_id = s.id
                JOIN bulgarian_words b ON tr.bulgarian_id = b.id
                ORDER BY s.id
            """)
        else:
            cursor = self._conn.execute("""
                SELECT
                    tr.id,
                    b.word as source_word,
                    s.word as target_word
                FROM bulgarian_words b
                JOIN translations tr ON tr.bulgarian_id = b.id
                JOIN spanish_words s ON tr.spanish_id = s.id
                ORDER BY b.id
            """)

        return [(row[0], row[1], row[2]) for row in cursor.fetchall()]

    def get_bulgarian_translations(self, spanish_word: str) -> List[str]:
        '''Get all Bulgarian translations for a Spanish word'''
        cursor = self._conn.execute('''
            SELECT b.word
            FROM bulgarian_words b
            JOIN translations t ON t.bulgarian_id = b.id
            JOIN spanish_words s ON t.spanish_id = s.id
            WHERE s.word = ?
        ''', (spanish_word,))

        result = [row[0] for row in cursor.fetchall()]
        logger.debug('Bulgarian translations for %s: %s', spanish_word, result)
        return result


    def get_spanish_translations(self, bulgarian_word: str) -> List[str]:
        '''Get all Spanish translations for a Bulgarian word'''
        cursor = self._conn.execute('''
            SELECT s.word
            FROM spanish_words s
            JOIN translations t ON t.spanish_id = s.id
            JOIN bulgarian_words b ON t.bulgarian_id = b.id
            WHERE b.word = ?
        ''', (bulgarian_word,))

        result = [row[0] for row in cursor.fetchall()]
        logger.debug('Spanish translations for %s: %s', bulgarian_word, result)
        return result


    def get_word_for_translation(self, source_lang: str, id_ranges: Optional[List[TranslationIdRange]] = None) -> str:
        '''Get a random word from translations table.

        Args:
            source_lang: Source language code ('es' or 'bg')
            id_ranges: Optional list of TranslationIdRange objects to restrict word selection
                       to specific translation IDs

        Returns:
            A random word from the specified language within the given ID ranges if specified
        '''
        # Process ID ranges if provided
        if id_ranges:
            # Convert TranslationIdRange objects to SQL conditions on translations.id
            range_conditions = []
            for id_range in id_ranges:
                if id_range.start == id_range.end:
                    range_conditions.append(f'(t.id = {id_range.start})')
                else:
                    range_conditions.append(f'(t.id BETWEEN {id_range.start} AND {id_range.end})')

            if range_conditions:
                # Build query with ID range restrictions on translations.id
                id_condition = ' OR '.join(range_conditions)

                if source_lang == 'es':
                    query = f'''
                        SELECT s.word
                        FROM spanish_words s
                        JOIN translations t ON t.spanish_id = s.id
                        WHERE {id_condition}
                        ORDER BY RANDOM()
                        LIMIT 1
                    '''
                else:
                    query = f'''
                        SELECT b.word
                        FROM bulgarian_words b
                        JOIN translations t ON t.bulgarian_id = b.id
                        WHERE {id_condition}
                        ORDER BY RANDOM()
                        LIMIT 1
                    '''

                cursor = self._conn.execute(query)
                result = cursor.fetchone()

                if result is not None:
                    return result[0]

        # Fall back to selecting any random word if no ranges specified or no matches found
        if source_lang == 'es':
            query = '''
                SELECT s.word
                FROM spanish_words s
                JOIN translations t ON t.spanish_id = s.id
                ORDER BY RANDOM()
                LIMIT 1
            '''
        else:
            query = '''
                SELECT b.word
                FROM bulgarian_words b
                JOIN translations t ON t.bulgarian_id = b.id
                ORDER BY RANDOM()
                LIMIT 1
            '''

        cursor = self._conn.execute(query)
        result = cursor.fetchone()

        # If still no result (unlikely), just get any word from the table
        if result is None:
            word_table = 'spanish_words' if source_lang == 'es' else 'bulgarian_words'
            cursor = self._conn.execute(f'''
                SELECT word
                FROM {word_table}
                ORDER BY RANDOM()
                LIMIT 1
            ''')
            result = cursor.fetchone()

        return result[0]

    def dump_db_info(self) -> None:
        queries = (
            'select count(*) from spanish_words',
            'select count(*) from bulgarian_words',
            'select count(*) from translations',
        )
        for q in queries:
            cursor = self._conn.execute(q)
            logger.debug('query: %s', q)
            for row in cursor.fetchall():
                logger.debug('    result: %s', row)

    def _init_db(self) -> None:
        '''Initialize the database schema'''
        self._conn.executescript('''
            CREATE TABLE IF NOT EXISTS spanish_words (
                id INTEGER PRIMARY KEY,
                word TEXT UNIQUE NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bulgarian_words (
                id INTEGER PRIMARY KEY,
                word TEXT UNIQUE NOT NULL
            );

            CREATE TABLE IF NOT EXISTS translations (
                id INTEGER PRIMARY KEY,
                spanish_id INTEGER,
                bulgarian_id INTEGER,
                FOREIGN KEY (spanish_id) REFERENCES spanish_words (id),
                FOREIGN KEY (bulgarian_id) REFERENCES bulgarian_words (id)
            );

            CREATE INDEX IF NOT EXISTS idx_spanish_word ON spanish_words(word);
            CREATE INDEX IF NOT EXISTS idx_bulgarian_word ON bulgarian_words(word);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_translations ON translations(spanish_id, bulgarian_id);
        ''')
