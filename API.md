# Yomu-Server API

The server defaults to port `6969`; the port can be changed in the extension
settings. Start the server from Yomu before making requests. It listens on all
IPv4 interfaces and does not require authentication.

Route parameters are path segments. Trailing slashes are optional where shown.

## Types

```typescript
type Manga = {
  id: number;
  source: number | null;
  title: string;
  description: string | null;
  author: string | null;
  artist: string | null;
  thumbnail: string;
  library: boolean;
  initialized: boolean;
  url: string;
};

type Chapter = {
  id: number;
  number: number;
  manga: number;
  title: string;
  uploaded: number; // Unix timestamp in seconds, or -1 when unknown
  downloaded: boolean;
  read: boolean;
  url: string;
};

type Category = {
  id: number;
  name: string;
};

type RateLimit = {
  rate: number;
  per: number;
  unit: string;
} | null;

type SourceFilter = {
  key: string;
  type: string;
  value: unknown;
  [field: string]: unknown;
};

type Source = {
  id: number;
  name: string;
  base_url: string;
  rate_limit: RateLimit;
  has_filters: boolean;
  filters: SourceFilter[];
  supports_latest: boolean;
  supports_search: boolean;
};

type MangaPage = {
  mangas: Manga[];
  has_next_page: boolean;
};

type PageCount = {
  pages: number;
};

type SourceFilterUpdate =
  | { key: string; type: "LIST"; value: string[] }
  | { key: string; type: "CHECKBOX"; value: unknown };
```

The source filter endpoint accepts a JSON array of `SourceFilterUpdate`. `LIST`
values must be arrays of strings; `CHECKBOX` values are passed through without
additional validation. Other filter types are ignored.

## Library

| Method | Path | Response |
| --- | --- | --- |
| `GET` | `/api/library/` | `Manga[]` |
| `POST` | `/api/library/{manga_id}/` | Empty body |
| `DELETE` | `/api/library/{manga_id}/` | Empty body |

`manga_id: number`. Unknown manga IDs return `404`; a failed library update
returns `500`. Adding an existing library manga or removing a manga that is
already absent succeeds.

## Categories

| Method | Path | Response |
| --- | --- | --- |
| `GET` | `/api/category/` | `Category[]` |
| `POST` | `/api/category/create/{name}/` | `Category` |
| `DELETE` | `/api/category/{category_id}/` | Empty body |
| `GET` | `/api/category/{category_id}/mangas` | `Manga[]` |
| `POST` | `/api/category/{category_id}/manga/{manga_id}/` | Empty body |
| `DELETE` | `/api/category/{category_id}/manga/{manga_id}/` | Empty body |

`category_id: number`, `manga_id: number`, `name: string`. Category operations
return `404` for unknown IDs, `400` when adding or removing a manga that is not
in the library, and `500` when the requested change fails.

## Sources

| Method | Path | Response |
| --- | --- | --- |
| `GET` | `/api/sources/` | `Source[]` |
| `GET` | `/api/sources/{source_id}/icon` | Image bytes; `Content-Type: image/png` |
| `GET` | `/api/sources/{source_id}/latest/{page}/` | `MangaPage` |
| `GET` | `/api/sources/{source_id}/search/{name}/` | `MangaPage` |
| `POST` | `/api/sources/{source_id}/filters` | Empty body |

`source_id: number`, `page: number`, `name: string`. The filters request body is
`SourceFilterUpdate[]`. Unknown source IDs return `404`; failed source requests
return `500`.

## Manga

| Method | Path | Response |
| --- | --- | --- |
| `GET` | `/api/manga/{manga_id}` | `Manga` |
| `GET` | `/api/manga/{manga_id}/chapters` | `Chapter[]` |
| `POST` | `/api/manga/{manga_id}/update` | Empty body |
| `GET` | `/api/manga/{manga_id}/thumbnail` | JPEG image bytes |

`manga_id: number`. Manga lookup returns `404` when the manga does not exist.
The update route returns `500` if both details and chapter updates fail.
Thumbnail retrieval or image processing failures return `500`.

## Chapters

| Method | Path | Response |
| --- | --- | --- |
| `GET` | `/api/chapter/{chapter_id}` | `Chapter` |
| `POST` | `/api/chapter/{chapter_id}/read` | Empty body |
| `POST` | `/api/chapter/{chapter_id}/unread` | Empty body |
| `GET` | `/api/chapter/{chapter_id}/pages` | `PageCount` |
| `GET` | `/api/chapter/{chapter_id}/page/{index}` | JPEG image bytes |

`chapter_id: number`, `index: number` (zero-based). The pages route fetches and
stores source page URLs when needed. Read/unread and chapter lookup currently
return `500` when the chapter does not exist; the pages and page-image routes
return `404` for an unknown chapter or unavailable page. Source, network, and
image-processing failures return `500`.

## Server-sent events

`GET /api/sse` returns `text/event-stream`. SSE `data` values for application
updates are JSON with this type:

```typescript
type YomuEvent =
  | { type: "SOURCE_FILTERS_UPDATED"; data: { id: number; [key: string]: unknown } }
  | { type: "LIBRARY_ADD"; data: Manga }
  | { type: "LIBRARY_REMOVE"; data: { id: number } }
  | {
      type: "MANGA_DETAILS_UPDATE";
      data: {
        id: number;
        title: string;
        description: string | null;
        author: string | null;
        artist: string | null;
        thumbnail: string;
        initialized: boolean;
      };
    }
  | { type: "CHAPTER_LIST_UPDATE"; data: { id: number } }
  | { type: "CHAPTER_READ_STATUS_CHANGED"; data: { id: number } }
  | { type: "CATEGORY_CREATED"; data: Category }
  | { type: "CATEGORY_DELETED"; data: { id: number } }
  | { type: "CATEGORY_MANGA_ADDED"; data: { category_id: number; manga: Manga } }
  | {
      type: "CATEGORY_MANGA_REMOVED";
      data: { category_id: number; manga_id: number };
    };
```

Application updates use the SSE event name `message`. The server also sends an
`open` event with string data and a `heartbeat` event with string data every
approximately 20 seconds.
