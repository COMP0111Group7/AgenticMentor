# HTTP/1.1 Request Parser & Response Builder — RFC 7230/7231

Implement an HTTP/1.1 request parser and response builder from scratch in Python,
following RFC 7230 (Message Syntax and Routing) and RFC 7231 (Semantics and Content).

## Requirements

Implement these functions in `http_server.py`:

```python
def parse_request(raw: bytes) -> dict:
    """Parse a raw HTTP/1.1 request into a structured dict."""

def build_response(status_code: int, headers: dict[str, str], body: str = "") -> bytes:
    """Build a raw HTTP/1.1 response from components."""

def handle_request(raw: bytes) -> bytes:
    """Parse a request and return an appropriate response.
    
    Supported routes:
      GET /          -> 200, body="Hello, World!"
      GET /echo?msg=X -> 200, body=X (URL-decoded)
      POST /data     -> 200, body=<echoed request body>
      GET /headers   -> 200, body=JSON of request headers
      *              -> 404 for unknown paths, 405 for wrong methods
    """
```

## RFC 7230 — Message Syntax (Key Rules)

### Request Line (Section 3.1.1)
- Format: `METHOD SP request-target SP HTTP-version CRLF`
- Example: `GET /path HTTP/1.1\r\n`
- Method is case-sensitive and consists of token characters.
- HTTP-version: `HTTP/1.1`

### Header Fields (Section 3.2)
- Format: `field-name ":" OWS field-value OWS CRLF`
- Field names are case-insensitive.
- OWS (optional whitespace) = spaces/tabs before and after field-value.
- Leading/trailing whitespace in field-value MUST be stripped.
- Headers end with an empty line (`CRLF CRLF`).

### Message Body (Section 3.3)
- Body length determined by `Content-Length` header.
- If `Content-Length` is present, read exactly that many bytes after headers.
- If absent for requests that may have a body, assume empty.

### Host Header (Section 5.4)
- A client MUST send a `Host` header in all HTTP/1.1 requests.

## RFC 7231 — Semantics (Key Rules)

### Methods (Section 4)
- GET: Retrieve a representation of the target resource.
- POST: Submit data to the target resource.
- HEAD: Same as GET but without response body.

### Status Codes (Section 6)
- 200 OK
- 400 Bad Request — malformed request syntax
- 404 Not Found — unknown path
- 405 Method Not Allowed — valid path, wrong method

### Response Format
- Status line: `HTTP/1.1 SP status-code SP reason-phrase CRLF`
- Headers, then CRLF, then optional body.
- MUST include `Content-Length` header in responses with a body.

## URL Encoding (RFC 3986 basics)
- Query string follows `?` in the request target.
- Parameters separated by `&`, key=value pairs.
- `%XX` encodes a byte in hex (e.g., `%20` = space).
- `+` in query strings represents a space.

## Constraints
- Do NOT use Python's `http` module, `urllib.parse` for the core parsing, or any HTTP library.
- You MAY use standard string/bytes operations.
- Raise `ValueError` for malformed requests (bad request line, missing Host, etc.).
- Use `\r\n` (CRLF) as line terminators in all responses.
- All header field names should be stored/returned in lowercase for consistency.

## Evaluation
Your implementation will be tested against a public test suite. Optimize to pass as many tests as possible.
