"""Open Library metadata provider."""

import asyncio
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import aiohttp
from rapidfuzz import fuzz

from ..core.models import AudiobookSet, ProviderIdentity
from .base import MetadataProvider


class OpenLibraryProvider(MetadataProvider):
    """Metadata provider using Open Library API."""

    BASE_URL = "https://openlibrary.org"
    API_TIMEOUT = 30
    RATE_LIMIT_DELAY = 0.1  # 100ms between requests

    def __init__(self):
        super().__init__("Open Library")
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_request_time = 0.0

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.API_TIMEOUT)
            headers = {
                'User-Agent': 'BookBot/0.1.0 (https://github.com/itsbryanman/BookBot)',
                'Accept': 'application/json'
            }
            self._session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _rate_limit(self) -> None:
        """Ensure we don't exceed rate limits."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self.RATE_LIMIT_DELAY:
            await asyncio.sleep(self.RATE_LIMIT_DELAY - time_since_last)
        self._last_request_time = asyncio.get_event_loop().time()

    async def search(
        self,
        title: Optional[str] = None,
        author: Optional[str] = None,
        series: Optional[str] = None,
        isbn: Optional[str] = None,
        year: Optional[int] = None,
        language: Optional[str] = None,
        limit: int = 10
    ) -> List[ProviderIdentity]:
        """Search Open Library for books."""
        await self._rate_limit()

        # If we have an ISBN, try that first
        if isbn:
            isbn_result = await self._search_by_isbn(isbn)
            if isbn_result:
                return [isbn_result]

        # Build search query
        query_parts = []
        if title:
            query_parts.append(f'title:"{title}"')
        if author:
            query_parts.append(f'author:"{author}"')

        if not query_parts:
            return []

        query = " AND ".join(query_parts)
        url = f"{self.BASE_URL}/search.json"
        params = {
            'q': query,
            'limit': min(limit, 100),  # Open Library max is 100
            'fields': 'key,title,author_name,first_publish_year,isbn,cover_i,publisher,language,subject'
        }

        if language:
            params['language'] = language

        try:
            session = await self._get_session()
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return []

                data = await response.json()
                docs = data.get('docs', [])

                identities = []
                for doc in docs:
                    identity = self._parse_search_result(doc)
                    if identity:
                        identities.append(identity)

                return identities

        except Exception:
            return []

    async def _search_by_isbn(self, isbn: str) -> Optional[ProviderIdentity]:
        """Search by ISBN using the books API."""
        clean_isbn = re.sub(r'[^0-9X]', '', isbn.upper())
        if not clean_isbn:
            return None

        url = f"{self.BASE_URL}/api/books"
        params = {
            'bibkeys': f'ISBN:{clean_isbn}',
            'format': 'json',
            'jscmd': 'data'
        }

        try:
            session = await self._get_session()
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                if not data:
                    return None

                # The response key format is "ISBN:xxxx"
                for key, book_data in data.items():
                    if key.startswith('ISBN:'):
                        return self._parse_book_data(book_data, key.split(':', 1)[1])

        except Exception:
            pass

        return None

    async def get_by_id(self, external_id: str) -> Optional[ProviderIdentity]:
        """Get a book by Open Library ID."""
        await self._rate_limit()

        if not external_id.startswith('/works/'):
            external_id = f'/works/{external_id}'

        url = f"{self.BASE_URL}{external_id}.json"

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status != 200:
                    return None

                work_data = await response.json()

                # Get the best edition for this work
                editions_url = f"{self.BASE_URL}{external_id}/editions.json"
                async with session.get(editions_url) as editions_response:
                    if editions_response.status == 200:
                        editions_data = await editions_response.json()
                        editions = editions_data.get('entries', [])

                        if editions:
                            # Pick the edition with the most complete data
                            best_edition = self._pick_best_edition(editions)
                            return self._parse_work_and_edition(work_data, best_edition)

                # Fallback to work data only
                return self._parse_work_data(work_data)

        except Exception:
            return None

    def _parse_search_result(self, doc: Dict[str, Any]) -> Optional[ProviderIdentity]:
        """Parse a search result document into a ProviderIdentity."""
        try:
            key = doc.get('key', '')
            if not key.startswith('/works/'):
                return None

            external_id = key

            title = doc.get('title', '')
            if not title:
                return None

            authors = doc.get('author_name', [])
            year = doc.get('first_publish_year')
            isbn_list = doc.get('isbn', [])
            cover_id = doc.get('cover_i')
            publishers = doc.get('publisher', [])
            languages = doc.get('language', [])

            # Extract ISBN-10 and ISBN-13
            isbn_10 = None
            isbn_13 = None
            for isbn in isbn_list:
                clean_isbn = re.sub(r'[^0-9X]', '', isbn.upper())
                if len(clean_isbn) == 10:
                    isbn_10 = clean_isbn
                elif len(clean_isbn) == 13:
                    isbn_13 = clean_isbn

            # Build cover URLs
            cover_urls = []
            if cover_id:
                cover_urls = [
                    f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg",
                    f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg",
                    f"https://covers.openlibrary.org/b/id/{cover_id}-S.jpg"
                ]

            return ProviderIdentity(
                provider=self.name,
                external_id=external_id,
                title=title,
                authors=authors,
                year=year,
                isbn_10=isbn_10,
                isbn_13=isbn_13,
                publisher=publishers[0] if publishers else None,
                language=languages[0] if languages else None,
                cover_urls=cover_urls,
                raw_data=doc
            )

        except Exception:
            return None

    def _parse_book_data(self, book_data: Dict[str, Any], isbn: str) -> Optional[ProviderIdentity]:
        """Parse book data from the books API."""
        try:
            title = book_data.get('title', '')
            if not title:
                return None

            authors = []
            if 'authors' in book_data:
                authors = [author.get('name', '') for author in book_data['authors']]

            # Extract publication info
            publish_date = book_data.get('publish_date', '')
            year = None
            if publish_date:
                year_match = re.search(r'\b(19|20)\d{2}\b', publish_date)
                if year_match:
                    year = int(year_match.group())

            publishers = []
            if 'publishers' in book_data:
                publishers = [pub.get('name', '') for pub in book_data['publishers']]

            # Cover URLs
            cover_urls = []
            if 'cover' in book_data:
                cover_urls = [
                    book_data['cover'].get('large', ''),
                    book_data['cover'].get('medium', ''),
                    book_data['cover'].get('small', '')
                ]
                cover_urls = [url for url in cover_urls if url]

            # Determine ISBN-10 vs ISBN-13
            isbn_10 = None
            isbn_13 = None
            clean_isbn = re.sub(r'[^0-9X]', '', isbn.upper())
            if len(clean_isbn) == 10:
                isbn_10 = clean_isbn
            elif len(clean_isbn) == 13:
                isbn_13 = clean_isbn

            return ProviderIdentity(
                provider=self.name,
                external_id=book_data.get('url', ''),
                title=title,
                authors=authors,
                year=year,
                isbn_10=isbn_10,
                isbn_13=isbn_13,
                publisher=publishers[0] if publishers else None,
                cover_urls=cover_urls,
                raw_data=book_data
            )

        except Exception:
            return None

    def _pick_best_edition(self, editions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Pick the best edition from a list based on data completeness."""
        def score_edition(edition: Dict[str, Any]) -> int:
            score = 0

            # Prefer editions with ISBN
            if 'isbn_13' in edition or 'isbn_10' in edition:
                score += 10

            # Prefer editions with publication date
            if 'publish_date' in edition:
                score += 5

            # Prefer editions with more complete metadata
            for field in ['subtitle', 'publishers', 'physical_format', 'covers']:
                if field in edition and edition[field]:
                    score += 1

            return score

        return max(editions, key=score_edition)

    def _parse_work_and_edition(self, work_data: Dict[str, Any], edition_data: Dict[str, Any]) -> ProviderIdentity:
        """Combine work and edition data into a ProviderIdentity."""
        # Start with work data
        identity = self._parse_work_data(work_data)
        if not identity:
            return None

        # Enhance with edition data
        if 'isbn_13' in edition_data:
            identity.isbn_13 = edition_data['isbn_13'][0] if isinstance(edition_data['isbn_13'], list) else edition_data['isbn_13']

        if 'isbn_10' in edition_data:
            identity.isbn_10 = edition_data['isbn_10'][0] if isinstance(edition_data['isbn_10'], list) else edition_data['isbn_10']

        if 'publish_date' in edition_data:
            year_match = re.search(r'\b(19|20)\d{2}\b', edition_data['publish_date'])
            if year_match:
                identity.year = int(year_match.group())

        if 'publishers' in edition_data and edition_data['publishers']:
            identity.publisher = edition_data['publishers'][0]

        if 'covers' in edition_data and edition_data['covers']:
            cover_id = edition_data['covers'][0]
            identity.cover_urls = [
                f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg",
                f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg",
                f"https://covers.openlibrary.org/b/id/{cover_id}-S.jpg"
            ]

        return identity

    def _parse_work_data(self, work_data: Dict[str, Any]) -> Optional[ProviderIdentity]:
        """Parse work data into a ProviderIdentity."""
        try:
            key = work_data.get('key', '')
            title = work_data.get('title', '')

            if not key or not title:
                return None

            # Parse authors
            authors = []
            if 'authors' in work_data:
                for author_ref in work_data['authors']:
                    if 'author' in author_ref and 'key' in author_ref['author']:
                        # This would require another API call to get author name
                        # For now, we'll skip detailed author resolution
                        pass

            return ProviderIdentity(
                provider=self.name,
                external_id=key,
                title=title,
                authors=authors,
                description=work_data.get('description'),
                raw_data=work_data
            )

        except Exception:
            return None

    def calculate_match_score(self, audiobook_set: AudiobookSet, identity: ProviderIdentity) -> float:
        """Calculate match score between audiobook set and Open Library identity."""
        score = 0.0
        total_weight = 0.0

        # Title similarity (highest weight)
        if audiobook_set.raw_title_guess and identity.title:
            title_similarity = fuzz.ratio(
                audiobook_set.raw_title_guess.lower(),
                identity.title.lower()
            ) / 100.0
            score += title_similarity * 0.4
            total_weight += 0.4

        # Author similarity
        if audiobook_set.author_guess and identity.authors:
            best_author_score = 0.0
            for author in identity.authors:
                author_similarity = fuzz.ratio(
                    audiobook_set.author_guess.lower(),
                    author.lower()
                ) / 100.0
                best_author_score = max(best_author_score, author_similarity)

            score += best_author_score * 0.3
            total_weight += 0.3

        # Series similarity
        if audiobook_set.series_guess and identity.series_name:
            series_similarity = fuzz.ratio(
                audiobook_set.series_guess.lower(),
                identity.series_name.lower()
            ) / 100.0
            score += series_similarity * 0.2
            total_weight += 0.2

        # Language match
        if audiobook_set.language_guess and identity.language:
            if audiobook_set.language_guess.lower() == identity.language.lower():
                score += 0.1
            total_weight += 0.1

        # Normalize score by total weight
        if total_weight > 0:
            score = score / total_weight
        else:
            score = 0.0

        return min(1.0, max(0.0, score))