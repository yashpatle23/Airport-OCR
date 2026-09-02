# Python heap, stack, garbage collection, and Airport-OCR

This study applies Python runtime concepts to the local FastAPI/PyMuPDF
application. It is an engineering guide, not a claim that the current local
profile is suitable for hostile public traffic.

## 1. Heap and stack are not a simple two-box model

### Python-managed heap

Most objects used by a request live on the Python-managed heap:

- multipart/parser and `UploadFile` objects;
- the bounded upload `bytearray` and final immutable `bytes` payload;
- page dictionaries, positioned-word lists, and vector-segment tuples;
- observations, normalized values, GeoJSON, validation, package, and summary;
- Pydantic models and JSON serialization buffers;
- coroutine objects, suspended frames, tasks, and exception objects.

CPython's small-object allocator (`pymalloc`) obtains arenas from the process
allocator. Releasing Python objects does not guarantee that resident set size
(RSS) immediately falls: freed blocks and arenas can remain available for reuse.

### Native allocations

PyMuPDF/MuPDF allocates memory outside Python's tracked heap for parsed PDF
objects, decompressed streams, fonts, page data, and drawing/text structures.
`tracemalloc` does not see all of this memory. Process RSS/cgroup memory is the
right final measurement for container sizing.

Starlette may spool multipart content to `/tmp`. In Compose `/tmp` is a 64 MiB
tmpfs, so spooled data consumes the same 512 MiB container memory budget even
though it appears as a file.

### Stacks and frames

The process has an event-loop thread and worker threads used by
`asyncio.to_thread`; each native thread reserves stack address space. Normal
Python calls create interpreter frames. Suspended `async` functions keep their
frames and referenced local variables alive on the heap while awaiting.

Airport-OCR uses iterative page/feature loops rather than deep recursion, so
recursion depth and Python call-stack exhaustion are not the primary risk. Heap
objects, native PDF expansion, worker-thread stacks, and response serialization
are more important.

## 2. Request memory lifetime

A successful request can overlap these allocations:

1. multipart parser buffers/spool file;
2. controller `bytearray` up to 5 MiB;
3. final immutable `bytes` copy passed to PyMuPDF;
4. MuPDF's parsed/decompressed native document structures;
5. full page word lists and bounded black vector segments;
6. observations plus normalized/GeoJSON/validation/package dictionaries;
7. Pydantic response objects and encoded JSON bytes.

The fixed 5 MiB compressed file limit therefore does **not** imply a 5 MiB memory
cost. A compact PDF can expand into large text/vector/native structures. The
application additionally sets page, word, drawing, vector-segment, and
concurrency rejection thresholds. PyMuPDF's page APIs materialize complete word
and drawing results before their counts can be checked, so these thresholds stop
continued/retained work but are not hard per-page allocation limits. The defaults
must still be measured against the actual corpus; hostile parsing requires a
killable process boundary.

## 3. CPython reference counting and cyclic GC

CPython normally reclaims an acyclic object as soon as its reference count
reaches zero. At request completion, local references to payloads and result
structures are dropped; this handles most request objects.

Reference counting alone cannot reclaim cycles (for example, A references B and
B references A). CPython's generational cyclic garbage collector periodically
finds unreachable container cycles. Useful inspection APIs include:

```python
import gc

print(gc.get_threshold())
print(gc.get_count())
print(gc.get_stats())
```

Calling `gc.collect()` after every request is not a sound memory policy. It adds
latency, scans tracked objects, does not release live objects, cannot free an
active native MuPDF document, and does not guarantee RSS returns to the OS.
Manual collection is appropriate only after measurement demonstrates a specific
cycle-related problem.

## 4. Deterministic cleanup still matters

Garbage collection is not a substitute for closing external resources:

- the route executes `await file.close()` in `finally`;
- the PDF service executes `document.close()` in `finally`;
- browser object URLs are revoked after JSON download;
- the ASGI lifespan waits for tracked extraction tasks at shutdown.

These boundaries release spool-file handles and native document resources at a
predictable point. They remain necessary even though Python would eventually
reclaim wrapper objects.

## 5. Async tasks, cancellation, and memory

`asyncio.to_thread` runs synchronous code in a worker thread. Cancelling the
awaiting request does not terminate that thread. If capacity were released on
request cancellation, abandoned workers could accumulate and exceed the stated
concurrency limit.

Airport-OCR uses a process-local bounded token queue for non-blocking admission
before controller file reads. Requests receive a retryable `503` when every slot
is active, so the application does not retain an unbounded queue of complete PDF
payloads. An admitted tracked extraction task owns its token and is shielded from
request cancellation. A disconnected request can therefore continue to consume
payload/native/result memory until extraction returns, but it remains one of the
fixed admitted slots. Shutdown awaits active tasks.

Admission capacity is process-local. With concurrency `C` and Uvicorn workers
`W`, up to `C × W` native extractions can run. The supplied runtime fixes `W=1`.
Raising concurrency increases not only CPU contention but simultaneous payload,
intermediate, response, and thread-stack memory.

Threads are not isolation. A parser crash or severe native allocation still
affects the process. Public/adversarial processing should use bounded worker
processes whose memory/CPU/time can be enforced and whose termination is safe.

## 6. Measurement

### Python allocation tracing

Use `tracemalloc` in a development-only harness around representative extraction
calls:

```python
import tracemalloc

tracemalloc.start()
# run representative extraction(s)
current, peak = tracemalloc.get_traced_memory()
print({"current_bytes": current, "peak_bytes": peak})
for stat in tracemalloc.take_snapshot().statistics("lineno")[:10]:
    print(stat)
tracemalloc.stop()
```

This identifies Python allocation sites but undercounts PyMuPDF/native and tmpfs
memory.

### Process/container measurements

On Linux, record peak RSS and container memory while testing 1 and then 2
concurrent requests:

```bash
/usr/bin/time -v airport-ocr-api --host 127.0.0.1 --port 8000
docker stats airport-ocr-local
docker inspect airport-ocr-local --format '{{.State.OOMKilled}}'
```

Also record request latency, PDF bytes/pages/word/drawing/segment counts, output
JSON size, `gc.get_stats()`, and whether the cgroup reports OOM pressure. Use
small, typical, maximum-boundary, malformed, text-heavy, and vector-heavy PDFs
that the project has permission to process.

## 7. Capacity guidance

Do not derive container memory as `5 MiB × concurrency`. Instead measure peak
RSS with a safety margin:

```text
baseline interpreter/framework/native libraries
+ concurrent multipart/spool/payload peaks
+ concurrent expanded PDF/intermediate peaks
+ concurrent response-serialization peaks
+ thread stacks and allocator headroom
```

Keep the default concurrency at 2 or lower until measurements support more. A
512 MiB local limit is a guardrail, not a proven production capacity target. If
OOM occurs, first reduce concurrency and complexity limits; do not merely force
GC or increase memory without identifying the allocation source.

## 8. Practical conclusions

- Python frames for suspended coroutines can retain large locals; keep request
  scopes and task tracking explicit.
- Reference counting reclaims most completed request graphs promptly, while
  cyclic GC handles unreachable cycles.
- Native PyMuPDF memory and tmpfs usage require RSS/cgroup measurement.
- `finally` cleanup is mandatory for uploads and documents.
- `gc.collect()` per request is neither necessary nor a fix for live/native
  memory.
- Exact file-byte, complexity, concurrency, and process limits address different
  risks; no one limit replaces the others.
