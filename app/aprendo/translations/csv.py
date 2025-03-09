import csv
import sqlite3
import logging

from typing import List, Tuple


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

    def record_translation_attempt(self, source_word: str, user_input: str, source_lang: str, target_lang: str, correct: bool) -> None:
        '''Record a translation attempt in the translation history.

        Args:
            source_word: The word being translated
            user_input: The translation provided by the user
            source_lang: Source language code ('es' or 'bg')
            target_lang: Target language code ('es' or 'bg')
            correct: Whether the translation was correct
        '''
        logger.debug('Recording attempt %s', (source_lang, target_lang, source_word, user_input, correct))
        with self._conn:
            self._conn.execute('''
                INSERT INTO translation_history
                    (source_language, target_language, source_word, user_input, correct)
                VALUES (?, ?, ?, ?, ?)
            ''', (source_lang, target_lang, source_word, user_input, correct))

    def get_translation_history(self) -> List[Tuple]:
        '''Get the translation history.
        Returns list of tuples with the following items:
          * source_language
          * source_word
          * user_input
          * correct
          * valid_translations
        '''

        cursor = self._conn.execute('''
            SELECT source_language, source_word, user_input, correct FROM translation_history
            ORDER BY timestamp DESC
        ''')
        for row in cursor.fetchall():
            source_language = row[0]
            source_word = row[1]
            user_input = row[2]
            correct = row[3]
            valid_translations = self.get_bulgarian_translations(source_word) if source_language == 'es' else self.get_spanish_translations(source_word)
            item = (source_language, source_word, user_input, correct, valid_translations)
            logger.debug(f'item: {item}')
            yield item

    def get_word_for_translation(self, source_lang: str) -> str:
        '''Get a random word that hasn\'t been used in translation exercises.

        Args:
            source_lang: Source language code ('es' or 'bg')

        Returns:
            A random word from the specified language that hasn\'t been tested yet
        '''
        # Select from appropriate table based on source language
        word_table = 'spanish_words' if source_lang == 'es' else 'bulgarian_words'

        cursor = self._conn.execute(f'''
            SELECT word
            FROM {word_table}
            WHERE word NOT IN (
                SELECT source_word
                FROM translation_history
                WHERE source_language = ?
            )
            ORDER BY RANDOM()
            LIMIT 1
        ''', (source_lang,))

        result = cursor.fetchone()
        if result is None:
            # If all words have been tested, return a random word
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
                spanish_id INTEGER,
                bulgarian_id INTEGER,
                FOREIGN KEY (spanish_id) REFERENCES spanish_words (id),
                FOREIGN KEY (bulgarian_id) REFERENCES bulgarian_words (id),
                PRIMARY KEY (spanish_id, bulgarian_id)
            );

            CREATE TABLE IF NOT EXISTS translation_history (
                id INTEGER PRIMARY KEY,
                source_language TEXT NOT NULL CHECK (source_language IN ('es', 'bg')),
                target_language TEXT NOT NULL CHECK (target_language IN ('es', 'bg')),
                source_word TEXT NOT NULL,
                user_input TEXT NOT NULL,
                correct BOOLEAN NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_spanish_word ON spanish_words(word);
            CREATE INDEX IF NOT EXISTS idx_bulgarian_word ON bulgarian_words(word);
            CREATE INDEX IF NOT EXISTS idx_history_source ON translation_history(source_language, source_word);
            CREATE INDEX IF NOT EXISTS idx_history_timestamp ON translation_history(timestamp);
        ''')
