from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict


if TYPE_CHECKING:
    from yomu.core.models import Category, Chapter, Manga, Source

    class RateLimitDict(TypedDict):
        rate: int
        per: int
        unit: str

    class CategoryDict(TypedDict):
        id: int
        name: str

    class SourceDict(TypedDict):
        id: int
        name: str
        base_url: str
        rate_limit: RateLimitDict
        has_filters: bool
        filters: dict
        supports_latest: bool
        supports_search: bool

    class MangaDict(TypedDict):
        id: int
        source: int | None
        title: str
        description: str | None
        author: str | None
        artist: str | None
        thumbnail: str
        library: bool
        initialized: bool
        url: str

    class ChapterDict(TypedDict):
        id: int
        number: int
        manga: int
        title: str
        uploaded: int
        downloaded: bool
        read: bool
        url: str


def convert_source_to_json(source: Source) -> SourceDict:
    rate_limit = (
        {
            "rate": source.rate_limit.rate,
            "per": source.rate_limit.per,
            "unit": source.rate_limit.unit,
        }
        if source.rate_limit is not None
        else None
    )

    filters = [
        {"key": key, **source_filter} for key, source_filter in source.filters.items()
    ]

    return {
        "id": source.id,
        "name": source.name,
        "base_url": source.BASE_URL,
        "rate_limit": rate_limit,
        "has_filters": source.has_filters,
        "filters": filters,
        "supports_latest": source.supports_latest,
        "supports_search": source.supports_search,
    }


def convert_category_to_json(category: Category) -> CategoryDict:
    return {"id": category.id, "name": category.name}


def convert_manga_to_json(manga: Manga) -> MangaDict:
    return {
        "id": manga.id,
        "source": manga.source.id,
        "title": manga.title,
        "description": manga.description,
        "author": manga.author,
        "artist": manga.artist,
        "thumbnail": manga.thumbnail,
        "library": manga.library,
        "initialized": manga.initialized,
        "url": manga.url,
    }


def convert_chapter_to_json(chapter: Chapter) -> ChapterDict:
    return {
        "id": chapter.id,
        "number": chapter.number,
        "manga": chapter.manga.id,
        "title": chapter.title,
        "uploaded": chapter.uploaded.timestamp(),
        "downloaded": chapter.downloaded,
        "read": chapter.read,
        "url": chapter.url,
    }
