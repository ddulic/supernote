# mypy Error Inventory: supernote/notebook/ and supernote/cli/

**Date**: 2026-03-15
**Command**: `./script/run-mypy.sh` with `supernote/notebook/` and `supernote/cli/` temporarily un-excluded
**Total**: 383 errors in 11 files (checked 212 source files)

---

## Summary by File

| File | Error Count | Primary Error Types |
|------|-------------|---------------------|
| `supernote/notebook/manipulator.py` | 93 | `no-untyped-call`, `no-untyped-def`, `var-annotated` |
| `supernote/notebook/parser.py` | 78 | `no-untyped-def`, `no-untyped-call`, `assignment`, `arg-type` |
| `supernote/notebook/fileformat.py` | 67 | `no-untyped-def`, `union-attr`, `assignment`, `index` |
| `supernote/notebook/converter.py` | 62 | `no-untyped-def`, `no-untyped-call`, `valid-type` |
| `supernote/cli/notebook.py` | 54 | `no-untyped-def`, `no-untyped-call`, `arg-type` |
| `supernote/notebook/decoder.py` | 32 | `no-untyped-def`, `override`, `var-annotated`, `unreachable` |
| `supernote/cli/client.py` | 19 | `no-untyped-def`, `var-annotated`, `arg-type`, `misc` |
| `supernote/cli/admin.py` | 12 | `no-untyped-def`, `var-annotated`, `no-untyped-call` |
| `supernote/notebook/utils.py` | 10 | `misc`, `type-var`, `no-untyped-call`, `return-value` |
| `supernote/cli/main.py` | 4 | `no-untyped-def`, `no-untyped-call` |
| `supernote/cli/server.py` | 2 | `no-untyped-def`, `no-untyped-call` |

## Summary by Error Code

| Error Code | Count | Fix Strategy |
|-----------|-------|-------------|
| `no-untyped-call` | 153 | Fix callee with `no-untyped-def` errors first; cascade resolves these |
| `no-untyped-def` | 149 | Add type annotations to function signatures (owned code: fix directly) |
| `arg-type` | 19 | Fix argument types; some need `# type: ignore[arg-type]` with justification for `FileObj` protocol mismatch |
| `var-annotated` | 18 | Add explicit type annotations to local variables |
| `union-attr` | 14 | Add None-guards or assert-not-None before attribute access |
| `assignment` | 11 | Fix incompatible assignment targets or add correct annotations |
| `index` | 6 | Add None-guard before indexing |
| `override` | 3 | Align subclass signatures with superclass (decoder.py) |
| `unreachable` | 3 | Remove unreachable code blocks |
| `var-annotated` | 3 | Add type annotation hints |
| `valid-type` | 2 | `PIL.Image` used as type — replace with `Image.Image` |
| `return-value` | 2 | Fix return type to match annotation |
| `misc` | 2 | Async generator / `asynccontextmanager` type mismatch |
| `type-var` | 1 | `Self` type used incorrectly in static method |

---

## Key Patterns

### Pattern 1: `no-untyped-def` cascades into `no-untyped-call` (302 of 383 errors)

The vast majority of errors are `no-untyped-def` on functions in `notebook/` that then cause
`no-untyped-call` errors at every call site. Fixing the function annotations will resolve
both error codes simultaneously.

**Strategy**: Add type annotations to all functions in `notebook/`. Because this is forked
upstream code (`supernote-tool`), use `# type: ignore[no-untyped-call]` with a justification
comment at the one remaining call site if the callee cannot be annotated.

### Pattern 2: `FileObj` protocol mismatch (appears in parser.py, manipulator.py, cli/notebook.py)

```
Argument 1 to "parse_stream" has incompatible type "BufferedReader[_BufferedReaderStream]"; expected "FileObj"
    Expected: def seek(self, offset: int, whence: int) -> None
    Got:      def seek(self, int, int = ..., /) -> int
```

`FileObj` is a protocol defined in the upstream library (`supernote-tool`) that expects
`seek(int, int) -> None` but Python's `BufferedReader.seek` returns `int`.

**Strategy**: Add `# type: ignore[arg-type]` with justification comment: "upstream FileObj
protocol requires seek() -> None but stdlib BufferedReader.seek() returns int; functionally
compatible and this is inherited forked parsing logic"

### Pattern 3: `None`-typed attributes (fileformat.py)

Fields like `keywords`, `titles`, `links` on notebook data objects are typed as `X | None`
but are accessed without None-guards. These stem from how the fileformat classes initialize
fields to `None`.

**Strategy**: Add `assert x is not None` guards or fix the data class field initialization
to always have a non-None default.

### Pattern 4: `PIL.Image` used as a type (converter.py:437, :455)

```
Module "PIL.Image" is not valid as a type
```

**Strategy**: Replace `PIL.Image` with `Image.Image` (the actual `Image` class from `PIL.Image`).

### Pattern 5: `override` incompatibility in decoder.py

`RattaDecoder` and `SFlattDecoder` subclass `BaseDecoder` but override `decode()` with
different signatures (extra `page_width`, `page_height` args).

**Strategy**: Fix signatures to match `BaseDecoder.decode()` contract or add an overloaded
protocol. May require targeted `# type: ignore[override]` with justification.

### Pattern 6: `asynccontextmanager` type mismatch (cli/client.py:39-40)

```
Argument 1 to "asynccontextmanager" has incompatible type "Callable[[str | None], Supernote]"
expected "Callable[[str | None], AsyncIterator[Never]]"
```

**Strategy**: Fix the async generator to have correct return type annotation `AsyncIterator[Supernote]`.

---

## cli/ Module Analysis

### `supernote/cli/main.py` (4 errors) — LOW COMPLEXITY

All `no-untyped-def`. Straightforward to fix — add `-> None` return types and parameter annotations.

### `supernote/cli/server.py` (2 errors) — LOW COMPLEXITY

Missing `add_parser` return type and one `no-untyped-def`. Easy fix.

### `supernote/cli/admin.py` (12 errors) — MEDIUM COMPLEXITY

Mix of `no-untyped-def` and `var-annotated` for session variables.
`session` vars need type as `AsyncSession | None` pattern.

### `supernote/cli/client.py` (19 errors) — MEDIUM COMPLEXITY

`asynccontextmanager` misuse is the complex part. `var-annotated` for `sn` needs `Supernote`
type. Several `no-untyped-def` for argument types on CLI handlers.

### `supernote/cli/notebook.py` (54 errors) — HIGH COMPLEXITY

Almost entirely `no-untyped-def` and `no-untyped-call`. Once `notebook/` module functions
get type annotations (T013), most of the `no-untyped-call` errors here will resolve automatically.
Should be done AFTER T013.

---

## notebook/ Module Analysis

### `supernote/notebook/utils.py` (10 errors) — HIGH COMPLEXITY

`Self` type used incorrectly in a static method + `WorkaroundPageWrapper.copy()` return type.
This is complex forked-code logic — targeted `# type: ignore` with justification warranted.

### `supernote/notebook/decoder.py` (32 errors) — HIGH COMPLEXITY

`override` incompatibilities and `unreachable` code statements. The decoder signature
mismatch is inherent to the binary-format decoding inheritance hierarchy — targeted ignores
warranted for the override issues.

### `supernote/notebook/fileformat.py` (67 errors) — HIGH COMPLEXITY

Core format data classes. Missing annotations throughout + `None`-attribute access patterns.
Requires careful annotation of all field types.

### `supernote/notebook/parser.py` (78 errors) — HIGH COMPLEXITY

Heavy `no-untyped-def` + `FileObj` protocol mismatch + dict type inference issues.
`params` dict needs explicit `dict[str, str | list[str]]` annotation.

### `supernote/notebook/converter.py` (62 errors) — HIGH COMPLEXITY

`PIL.Image` module-as-type errors + full annotation coverage needed.

### `supernote/notebook/manipulator.py` (93 errors) — HIGH COMPLEXITY

Largest error count. Mostly `no-untyped-call` that will cascade-resolve once
`no-untyped-def` errors in the called functions are fixed.

---

## Recommended Fix Order (T012 and T013)

### T012: Fix supernote/cli/ (89 errors total)

1. `main.py` (4) — add return type annotations
2. `server.py` (2) — add return type annotations
3. `admin.py` (12) — add parameter and local variable annotations
4. `client.py` (19) — fix asynccontextmanager, add arg annotations
5. `notebook.py` (54) — depends on T013; most errors resolve when notebook/ is typed

### T013: Fix supernote/notebook/ (294 errors total)

1. `utils.py` (10) — fix `Self` misuse; targeted ignore for WorkaroundPageWrapper.copy
2. `decoder.py` (32) — add annotations; targeted ignores for `override` + `unreachable`
3. `fileformat.py` (67) — annotate all functions; add None-guards
4. `parser.py` (78) — annotate all functions; targeted `arg-type` ignore for FileObj protocol
5. `converter.py` (62) — annotate; fix `PIL.Image` → `Image.Image`
6. `manipulator.py` (93) — annotate; FileObj ignore; most `no-untyped-call` auto-resolve

---

## Raw Error Output

```
supernote/cli/main.py:10: error: Function is missing a return type annotation  [no-untyped-def]
supernote/cli/main.py:30: error: Function is missing a return type annotation  [no-untyped-def]
supernote/cli/main.py:31: error: Function is missing a return type annotation  [no-untyped-def]
supernote/cli/main.py:61: error: Call to untyped function "main" in typed context  [no-untyped-call]
supernote/notebook/fileformat.py:66: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:67: error: Incompatible types in assignment (expression has type "str | None", target has type "None")  [assignment]
supernote/notebook/fileformat.py:74: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:75: error: Incompatible types in assignment (expression has type "str | None", target has type "None")  [assignment]
supernote/notebook/fileformat.py:82: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:83: error: Incompatible types in assignment (expression has type "dict[str, str] | None", target has type "None")  [assignment]
supernote/notebook/fileformat.py:90: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:91: error: Incompatible types in assignment (expression has type "dict[str, str] | None", target has type "None")  [assignment]
supernote/notebook/fileformat.py:98: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:99: error: Incompatible types in assignment (expression has type "list[dict[str, str | list[str]]] | None", target has type "None")  [assignment]
supernote/notebook/fileformat.py:109: error: Argument 1 to "len" has incompatible type "None"; expected "Sized"  [arg-type]
supernote/notebook/fileformat.py:126: error: Value of type "None" is not indexable  [index]
supernote/notebook/fileformat.py:128: error: Incompatible default for argument "indent" (default has type "None", argument has type "int")  [assignment]
supernote/notebook/fileformat.py:149: error: Item "None" of "dict[str, str] | None" has no attribute "get"  [union-attr]
supernote/notebook/fileformat.py:156: error: Item "None" of "dict[str, str] | None" has no attribute "get"  [union-attr]
supernote/notebook/fileformat.py:158: error: Item "None" of "dict[str, str] | None" has no attribute "get"  [union-attr]
supernote/notebook/fileformat.py:158: error: Item "None" of "str | Any | None" has no attribute "__iter__" (not iterable)  [union-attr]
supernote/notebook/fileformat.py:159: error: Argument 1 to "Keyword" has incompatible type "str | Any"; expected "dict[str, str]"  [arg-type]
supernote/notebook/fileformat.py:161: error: Item "None" of "dict[str, str] | None" has no attribute "get"  [union-attr]
supernote/notebook/fileformat.py:163: error: Item "None" of "dict[str, str] | None" has no attribute "get"  [union-attr]
supernote/notebook/fileformat.py:163: error: Item "None" of "str | Any | None" has no attribute "__iter__" (not iterable)  [union-attr]
supernote/notebook/fileformat.py:164: error: Argument 1 to "Title" has incompatible type "str | Any"; expected "dict[str, str]"  [arg-type]
supernote/notebook/fileformat.py:166: error: Item "None" of "dict[str, str] | None" has no attribute "get"  [union-attr]
supernote/notebook/fileformat.py:168: error: Item "None" of "dict[str, str] | None" has no attribute "get"  [union-attr]
supernote/notebook/fileformat.py:168: error: Item "None" of "str | Any | None" has no attribute "__iter__" (not iterable)  [union-attr]
supernote/notebook/fileformat.py:169: error: Argument 1 to "Link" has incompatible type "str | Any"; expected "dict[str, str]"  [arg-type]
supernote/notebook/fileformat.py:173: error: Value of type "list[dict[str, str | list[str]]] | None" is not indexable  [index]
supernote/notebook/fileformat.py:207: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:210: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:211: error: Item "None" of "dict[str, str] | None" has no attribute "get"  [union-attr]
supernote/notebook/fileformat.py:213: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:214: error: Item "None" of "dict[str, str] | None" has no attribute "get"  [union-attr]
supernote/notebook/fileformat.py:216: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:217: error: Value of type "str | None" is not indexable  [index]
supernote/notebook/fileformat.py:224: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:237: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:266: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:298: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:361: error: Call to untyped function "Layer" in typed context  [no-untyped-call]
supernote/notebook/fileformat.py:379: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:382: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:387: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:390: error: Call to untyped function "get_layer" in typed context  [no-untyped-call]
supernote/notebook/fileformat.py:395: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:398: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:404: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:408: error: Item "list[str]" of "str | list[str]" has no attribute "replace"  [union-attr]
supernote/notebook/fileformat.py:410: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:414: error: Item "list[str]" of "str | list[str]" has no attribute "split"  [union-attr]
supernote/notebook/fileformat.py:417: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:420: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:423: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:426: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:427: error: Argument 1 to "int" has incompatible type "str | list[str] | None"; expected "str | Buffer | SupportsInt | SupportsIndex"  [arg-type]
supernote/notebook/fileformat.py:429: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:432: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:435: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:438: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:441: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:446: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:450: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:453: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:456: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:459: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/fileformat.py:462: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/utils.py:30: error: Static methods cannot use Self type  [misc]
supernote/notebook/utils.py:30: error: A function returning TypeVar should receive at least one argument containing the same TypeVar  [type-var]
supernote/notebook/utils.py:33: error: Argument 1 to "set_content" of "Page" has incompatible type "bytes | None"; expected "bytes"  [arg-type]
supernote/notebook/utils.py:34: error: Call to untyped function "set_totalpath" in typed context  [no-untyped-call]
supernote/notebook/utils.py:34: error: Call to untyped function "get_totalpath" in typed context  [no-untyped-call]
supernote/notebook/utils.py:35: error: Call to untyped function "get_layers" in typed context  [no-untyped-call]
supernote/notebook/utils.py:36: error: Call to untyped function "get_layer" in typed context  [no-untyped-call]
supernote/notebook/utils.py:37: error: Incompatible return value type (got "WorkaroundPageWrapper", expected "Self")  [return-value]
supernote/notebook/utils.py:41: error: Call to untyped function "get_layers" in typed context  [no-untyped-call]
supernote/notebook/parser.py:38: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
supernote/notebook/parser.py:67: error: Incompatible types in assignment (expression has type "SupernoteParser", variable has type "SupernoteXParser")  [assignment]
supernote/notebook/parser.py:109: error: Call to untyped function "_get_cover_address" in typed context  [no-untyped-call]
supernote/notebook/parser.py:111: error: Call to untyped function "_get_content_at_address" in typed context  [no-untyped-call]
supernote/notebook/parser.py:115: error: Call to untyped function "_get_keyword_address" in typed context  [no-untyped-call]
supernote/notebook/parser.py:116: error: Call to untyped function "_get_content_at_address" in typed context  [no-untyped-call]
supernote/notebook/parser.py:119: error: Call to untyped function "_get_page_number_from_footer_property" in typed context  [no-untyped-call]
supernote/notebook/parser.py:123: error: Call to untyped function "_get_title_address" in typed context  [no-untyped-call]
supernote/notebook/parser.py:124: error: Call to untyped function "_get_content_at_address" in typed context  [no-untyped-call]
supernote/notebook/parser.py:128: error: Call to untyped function "_get_page_number_from_footer_property" in typed context  [no-untyped-call]
supernote/notebook/parser.py:131: error: Call to untyped function "get_links" in typed context  [no-untyped-call]
supernote/notebook/parser.py:132: error: Call to untyped function "_get_link_address" in typed context  [no-untyped-call]
supernote/notebook/parser.py:133: error: Call to untyped function "_get_content_at_address" in typed context  [no-untyped-call]
supernote/notebook/parser.py:138: error: Call to untyped function "_get_bitmap_address" in typed context  [no-untyped-call]
supernote/notebook/parser.py:140: error: Call to untyped function "_get_content_at_address" in typed context  [no-untyped-call]
supernote/notebook/parser.py:144: error: Call to untyped function "_get_content_at_address" in typed context  [no-untyped-call]
supernote/notebook/parser.py:145: error: Call to untyped function "get_layer" in typed context  [no-untyped-call]
supernote/notebook/parser.py:149: error: Call to untyped function "_get_content_at_address" in typed context  [no-untyped-call]
supernote/notebook/parser.py:150: error: Call to untyped function "set_totalpath" in typed context  [no-untyped-call]
supernote/notebook/parser.py:152: error: Call to untyped function "_get_recogn_file_address" in typed context  [no-untyped-call]
supernote/notebook/parser.py:154: error: Call to untyped function "_get_content_at_address" in typed context  [no-untyped-call]
supernote/notebook/parser.py:155: error: Call to untyped function "set_recogn_file" in typed context  [no-untyped-call]
supernote/notebook/parser.py:157: error: Call to untyped function "_get_recogn_text_address" in typed context  [no-untyped-call]
supernote/notebook/parser.py:159: error: Call to untyped function "_get_content_at_address" in typed context  [no-untyped-call]
supernote/notebook/parser.py:160: error: Call to untyped function "set_recogn_text" in typed context  [no-untyped-call]
supernote/notebook/parser.py:164: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/parser.py:186: error: Argument 1 to "load" has incompatible type "BufferedReader[_BufferedReaderStream]"; expected "FileObj"  [arg-type]
supernote/notebook/parser.py:190: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/parser.py:199: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/parser.py:216: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/parser.py:227: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/parser.py:238: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/parser.py:249: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/parser.py:280: error: Value of type "list[dict[str, str | list[str]]] | None" is not indexable  [index]
supernote/notebook/parser.py:281: error: Value of type "list[dict[str, str | list[str]]] | None" is not indexable  [index]
supernote/notebook/parser.py:281: error: Argument 1 to "int" has incompatible type "str | list[str] | Any"; expected "str | Buffer | SupportsInt | SupportsIndex"  [arg-type]
supernote/notebook/parser.py:287: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/parser.py:302: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/parser.py:317: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/parser.py:360: error: Argument 1 to "parse_stream" of "SupernoteParser" has incompatible type "BufferedReader[_BufferedReaderStream]"; expected "FileObj"  [arg-type]
supernote/notebook/parser.py:416: error: Incompatible types in assignment (expression has type "dict[str, str | list[str]]", variable has type "dict[str, str] | None")  [assignment]
supernote/notebook/parser.py:417: error: Incompatible types in assignment (expression has type "dict[str, str | list[str]]", variable has type "dict[str, str] | None")  [assignment]
supernote/notebook/parser.py:479: error: Argument 1 to "int" has incompatible type "str | list[str] | None"; expected "str | Buffer | SupportsInt | SupportsIndex"  [arg-type]
supernote/notebook/parser.py:496: error: Argument 2 to "map" has incompatible type "str | list[str] | None"; expected "Iterable[str]"  [arg-type]
supernote/notebook/parser.py:498: error: Argument 1 to "int" has incompatible type "str | list[str] | None"; expected "str | Buffer | SupportsInt | SupportsIndex"  [arg-type]
supernote/notebook/parser.py:561: error: Need type annotation for "params" (hint: "params: dict[<type>, <type>] = ...")  [var-annotated]
supernote/notebook/parser.py:577: error: Incompatible types in assignment (expression has type "str | Any", target has type "list[Any]")  [assignment]
supernote/notebook/parser.py:578: error: Incompatible return value type (got "dict[str | Any, list[Any]]", expected "dict[str, str | list[str]]")  [return-value]
supernote/notebook/parser.py:601: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/parser.py:604: error: Call to untyped function "_get_keyword_addresses" in typed context  [no-untyped-call]
supernote/notebook/parser.py:606: error: Call to untyped function "_parse_keyword_block" in typed context  [no-untyped-call]
supernote/notebook/parser.py:611: error: Call to untyped function "_get_title_addresses" in typed context  [no-untyped-call]
supernote/notebook/parser.py:613: error: Call to untyped function "_parse_title_block" in typed context  [no-untyped-call]
supernote/notebook/parser.py:618: error: Call to untyped function "_get_link_addresses" in typed context  [no-untyped-call]
supernote/notebook/parser.py:620: error: Call to untyped function "_parse_link_block" in typed context  [no-untyped-call]
supernote/notebook/parser.py:626: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/parser.py:636: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/parser.py:639: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/parser.py:649: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/parser.py:652: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/parser.py:662: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/parser.py:679: error: Argument 1 to "int" has incompatible type "str | list[str]"; expected "str | Buffer | SupportsInt | SupportsIndex"  [arg-type]
supernote/notebook/parser.py:682: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/parser.py:698: error: Call to untyped function "_get_layer_addresses" in typed context  [no-untyped-call]
supernote/notebook/parser.py:700: error: Call to untyped function "_parse_layer_block" in typed context  [no-untyped-call]
supernote/notebook/parser.py:705: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/parser.py:722: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/decoder.py:31: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/decoder.py:52: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/decoder.py:52: error: Signature of "decode" incompatible with supertype "BaseDecoder"  [override]
supernote/notebook/decoder.py:126: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/decoder.py:126: error: Signature of "decode" incompatible with supertype "BaseDecoder"  [override]
supernote/notebook/decoder.py:163: error: Call to untyped function "_create_colormap" in typed context  [no-untyped-call]
supernote/notebook/decoder.py:174: error: Need type annotation for "waiting"  [var-annotated]
supernote/notebook/decoder.py:181: error: Statement is unreachable  [unreachable]
supernote/notebook/decoder.py:200: error: Incompatible types in assignment (expression has type "tuple[Any, Any]", variable has type "tuple[()]")  [assignment]
supernote/notebook/decoder.py:209: error: Call to untyped function "_create_color_bytearray" in typed context  [no-untyped-call]
supernote/notebook/decoder.py:214: error: Statement is unreachable  [unreachable]
supernote/notebook/decoder.py:230: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/decoder.py:243: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/decoder.py:261: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/decoder.py:282: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/decoder.py:297: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/decoder.py:324: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/decoder.py:324: error: Signature of "decode" incompatible with supertype "BaseDecoder"  [override]
supernote/notebook/decoder.py:373: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
supernote/notebook/decoder.py:389: error: Statement is unreachable  [unreachable]
supernote/notebook/manipulator.py:24: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/manipulator.py:29: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/manipulator.py:32: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/manipulator.py:34: error: Value of type "Any | None" is not indexable  [index]
supernote/notebook/manipulator.py:39: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/manipulator.py:45: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/manipulator.py:48: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/manipulator.py:72: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/manipulator.py:75: error: Function is missing a return type annotation  [no-untyped-def]
supernote/notebook/manipulator.py:81: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/manipulator.py:92: error: Call to untyped function "NotebookBuilder" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:93: error: Call to untyped function "_pack_type" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:94: error: Call to untyped function "_pack_signature" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:95: error: Call to untyped function "_pack_header" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:96: error: Call to untyped function "_pack_cover" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:97: error: Call to untyped function "_pack_keywords" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:98: error: Call to untyped function "_pack_titles" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:99: error: Call to untyped function "_pack_links" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:100: error: Call to untyped function "_pack_backgrounds" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:101: error: Call to untyped function "_pack_pages" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:102: error: Call to untyped function "_pack_footer" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:103: error: Call to untyped function "_pack_tail" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:104: error: Call to untyped function "_pack_footer_address" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:105: error: Call to untyped function "build" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:110: error: Argument 1 to "parse_stream" of "SupernoteParser" has incompatible type "BytesIO"; expected "FileObj"  [arg-type]
supernote/notebook/manipulator.py:118: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/manipulator.py:137: error: Call to untyped function "_verify_header_property" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:138: error: Call to untyped function "_verify_header_property" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:139: error: Call to untyped function "_verify_header_property" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:140: error: Call to untyped function "_verify_header_property" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:141: error: Call to untyped function "_verify_header_property" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:142: error: Call to untyped function "_verify_header_property" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:143: error: Call to untyped function "_verify_header_property" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:145: error: Call to untyped function "NotebookBuilder" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:146: error: Call to untyped function "_pack_type" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:147: error: Call to untyped function "_pack_signature" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:148: error: Call to untyped function "_pack_header" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:149: error: Call to untyped function "_pack_cover" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:150: error: Call to untyped function "_pack_keywords" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:151: error: Call to untyped function "_pack_keywords" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:152: error: Call to untyped function "_pack_titles" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:153: error: Call to untyped function "_pack_titles" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:154: error: Call to untyped function "_pack_links" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:155: error: Call to untyped function "_pack_links" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:156: error: Call to untyped function "_pack_backgrounds" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:157: error: Call to untyped function "_pack_backgrounds" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:158: error: Call to untyped function "_pack_pages" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:159: error: Call to untyped function "_pack_pages" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:160: error: Call to untyped function "_pack_footer" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:161: error: Call to untyped function "_pack_tail" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:162: error: Call to untyped function "_pack_footer_address" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:163: error: Call to untyped function "build" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:168: error: Argument 1 to "parse_stream" of "SupernoteParser" has incompatible type "BytesIO"; expected "FileObj"  [arg-type]
supernote/notebook/manipulator.py:176: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/manipulator.py:181: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/manipulator.py:188: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/manipulator.py:190: error: Call to untyped function "_construct_metadata_block" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:194: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/manipulator.py:200: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/manipulator.py:220: error: Call to untyped function "_construct_metadata_block" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:226: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/manipulator.py:245: error: Call to untyped function "_construct_metadata_block" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:251: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/manipulator.py:268: error: Call to untyped function "_construct_metadata_block" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:274: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/manipulator.py:280: error: Call to untyped function "_find_background_content_from_page" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:285: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/manipulator.py:291: error: Need type annotation for "layers"  [var-annotated]
supernote/notebook/manipulator.py:297: error: Need type annotation for "style"  [var-annotated]
supernote/notebook/manipulator.py:305: error: Call to untyped function "_construct_metadata_block" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:319: error: Call to untyped function "_construct_metadata_block" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:324: error: Need type annotation for "totalpath_block"  [var-annotated]
supernote/notebook/manipulator.py:328: error: Need type annotation for "page_metadata"  [var-annotated]
supernote/notebook/manipulator.py:336: error: Call to untyped function "_construct_metadata_block" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:340: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/manipulator.py:341: error: Need type annotation for "metadata_footer" (hint: "metadata_footer: dict[<type>, <type>] = ...")  [var-annotated]
supernote/notebook/manipulator.py:381: error: Call to untyped function "_construct_metadata_block" in typed context  [no-untyped-call]
supernote/notebook/manipulator.py:385: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/manipulator.py:389: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/manipulator.py:396: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/manipulator.py:401: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/manipulator.py:412: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/converter.py:40: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/converter.py:59: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/converter.py:63: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/converter.py:79: error: Call to untyped function "_convert_layered_page" in typed context  [no-untyped-call]
supernote/notebook/converter.py:83: error: Call to untyped function "_convert_nonlayered_page" in typed context  [no-untyped-call]
supernote/notebook/converter.py:90: error: Call to untyped function "_make_transparent" in typed context  [no-untyped-call]
supernote/notebook/converter.py:93: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/converter.py:103: error: Call to untyped function "find_decoder" in typed context  [no-untyped-call]
supernote/notebook/converter.py:104: error: Call to untyped function "_create_image_from_decoder" in typed context  [no-untyped-call]
supernote/notebook/converter.py:106: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/converter.py:111: error: Need type annotation for "imgs" (hint: "imgs: dict[<type>, <type>] = ...")  [var-annotated]
supernote/notebook/converter.py:120: error: Call to untyped function "find_decoder" in typed context  [no-untyped-call]
supernote/notebook/converter.py:139: error: Call to untyped function "_create_image_from_decoder" in typed context  [no-untyped-call]
supernote/notebook/converter.py:147: error: Call to untyped function "_flatten_layers" in typed context  [no-untyped-call]
supernote/notebook/converter.py:149: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/converter.py:152: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/converter.py:164: error: Call to untyped function "_get_layer_visibility" in typed context  [no-untyped-call]
supernote/notebook/converter.py:181: error: Call to untyped function "_whiten_transparent" in typed context  [no-untyped-call]
supernote/notebook/converter.py:182: error: Call to untyped function "flatten" in typed context  [no-untyped-call]
supernote/notebook/converter.py:185: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/converter.py:191: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/converter.py:198: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/converter.py:223: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/converter.py:228: error: Call to untyped function "_get_mark_layer_visibility" in typed context  [no-untyped-call]
supernote/notebook/converter.py:246: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/converter.py:254: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/converter.py:282: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/converter.py:285: error: Call to untyped function "ImageConverter" in typed context  [no-untyped-call]
supernote/notebook/converter.py:289: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/converter.py:316: error: Call to untyped function "build_visibility_overlay" in typed context  [no-untyped-call]
supernote/notebook/converter.py:323: error: Call to untyped function "convert" in typed context  [no-untyped-call]
supernote/notebook/converter.py:337: error: Call to untyped function "build_visibility_overlay" in typed context  [no-untyped-call]
supernote/notebook/converter.py:338: error: Call to untyped function "convert" in typed context  [no-untyped-call]
supernote/notebook/converter.py:340: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/converter.py:359: error: Call to untyped function "generate_color_mask" in typed context  [no-untyped-call]
supernote/notebook/converter.py:389: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
supernote/notebook/converter.py:393: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/converter.py:397: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/converter.py:428: error: Call to untyped function "ImageConverter" in typed context  [no-untyped-call]
supernote/notebook/converter.py:437: error: Module "PIL.Image" is not valid as a type  [valid-type]
supernote/notebook/converter.py:448: error: Call to untyped function "convert" in typed context  [no-untyped-call]
supernote/notebook/converter.py:455: error: Module "PIL.Image" is not valid as a type  [valid-type]
supernote/notebook/converter.py:464: error: Call to untyped function "get_pageid" in typed context  [no-untyped-call]
supernote/notebook/converter.py:466: error: Call to untyped function "get_orientation" in typed context  [no-untyped-call]
supernote/notebook/converter.py:473: error: Call to untyped function "draw" in typed context  [no-untyped-call]
supernote/notebook/converter.py:482: error: Call to untyped function "_calc_link_rect" in typed context  [no-untyped-call]
supernote/notebook/converter.py:483: error: Call to untyped function "get_scale" in typed context  [no-untyped-call]
supernote/notebook/converter.py:489: error: Call to untyped function "get_pageid" in typed context  [no-untyped-call]
supernote/notebook/converter.py:492: error: Call to untyped function "_add_links" in typed context  [no-untyped-call]
supernote/notebook/converter.py:492: error: Call to untyped function "get_scale" in typed context  [no-untyped-call]
supernote/notebook/converter.py:496: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/converter.py:497: error: Call to untyped function "get_links" in typed context  [no-untyped-call]
supernote/notebook/converter.py:505: error: Call to untyped function "get_fileid" in typed context  [no-untyped-call]
supernote/notebook/converter.py:508: error: Call to untyped function "_calc_link_rect" in typed context  [no-untyped-call]
supernote/notebook/converter.py:513: error: Call to untyped function "_calc_link_rect" in typed context  [no-untyped-call]
supernote/notebook/converter.py:516: error: Function is missing a type annotation  [no-untyped-def]
supernote/notebook/converter.py:529: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
supernote/notebook/converter.py:546: error: Call to untyped function "is_realtime_recognition" in typed context  [no-untyped-call]
supernote/notebook/converter.py:549: error: Call to untyped function "get_recogn_status" in typed context  [no-untyped-call]
supernote/notebook/converter.py:551: error: Call to untyped function "get_recogn_text" in typed context  [no-untyped-call]
supernote/cli/notebook.py:41: error: Function is missing a type annotation  [no-untyped-def]
supernote/cli/notebook.py:51: error: Function is missing a type annotation  [no-untyped-def]
supernote/cli/notebook.py:63: error: Function is missing a type annotation  [no-untyped-def]
supernote/cli/notebook.py:64: error: Call to untyped function "ImageConverter" in typed context  [no-untyped-call]
supernote/cli/notebook.py:70: error: Call to untyped function "build_visibility_overlay" in typed context  [no-untyped-call]
supernote/cli/notebook.py:72: error: Function is missing a type annotation  [no-untyped-def]
supernote/cli/notebook.py:77: error: Call to untyped function "convert_all" in typed context  [no-untyped-call]
supernote/cli/notebook.py:79: error: Call to untyped function "convert" in typed context  [no-untyped-call]
supernote/cli/notebook.py:80: error: Call to untyped function "save" in typed context  [no-untyped-call]
supernote/cli/notebook.py:83: error: Function is missing a type annotation  [no-untyped-def]
supernote/cli/notebook.py:84: error: Call to untyped function "SvgConverter" in typed context  [no-untyped-call]
supernote/cli/notebook.py:90: error: Call to untyped function "build_visibility_overlay" in typed context  [no-untyped-call]
supernote/cli/notebook.py:92: error: Function is missing a type annotation  [no-untyped-def]
supernote/cli/notebook.py:101: error: Call to untyped function "convert_all" in typed context  [no-untyped-call]
supernote/cli/notebook.py:103: error: Call to untyped function "convert" in typed context  [no-untyped-call]
supernote/cli/notebook.py:104: error: Call to untyped function "save" in typed context  [no-untyped-call]
supernote/cli/notebook.py:107: error: Function is missing a type annotation  [no-untyped-def]
supernote/cli/notebook.py:112: error: Function is missing a type annotation  [no-untyped-def]
supernote/cli/notebook.py:123: error: Call to untyped function "save" in typed context  [no-untyped-call]
supernote/cli/notebook.py:128: error: Call to untyped function "save" in typed context  [no-untyped-call]
supernote/cli/notebook.py:131: error: Function is missing a type annotation  [no-untyped-def]
supernote/cli/notebook.py:134: error: Function is missing a type annotation  [no-untyped-def]
supernote/cli/notebook.py:143: error: Call to untyped function "convert_and_concat_all" in typed context  [no-untyped-call]
supernote/cli/notebook.py:148: error: Call to untyped function "save" in typed context  [no-untyped-call]
supernote/cli/notebook.py:151: error: Function is missing a type annotation  [no-untyped-def]
supernote/cli/notebook.py:152: error: Call to untyped function "load_notebook" in typed context  [no-untyped-call]
supernote/cli/notebook.py:156: error: Call to untyped function "parse_color" in typed context  [no-untyped-call]
supernote/cli/notebook.py:162: error: Call to untyped function "convert_to_png" in typed context  [no-untyped-call]
supernote/cli/notebook.py:164: error: Call to untyped function "convert_to_svg" in typed context  [no-untyped-call]
supernote/cli/notebook.py:166: error: Call to untyped function "convert_to_pdf" in typed context  [no-untyped-call]
supernote/cli/notebook.py:168: error: Call to untyped function "convert_to_txt" in typed context  [no-untyped-call]
supernote/cli/notebook.py:171: error: Function is missing a type annotation  [no-untyped-def]
supernote/cli/notebook.py:174: error: Argument 1 to "parse_metadata" has incompatible type "BufferedReader[_BufferedReaderStream]"; expected "FileObj"  [arg-type]
supernote/cli/notebook.py:178: error: Function is missing a type annotation  [no-untyped-def]
supernote/cli/notebook.py:181: error: Call to untyped function "load_notebook" in typed context  [no-untyped-call]
supernote/cli/notebook.py:182: error: Call to untyped function "reconstruct" in typed context  [no-untyped-call]
supernote/cli/notebook.py:190: error: Argument 1 to "load" has incompatible type "BytesIO"; expected "FileObj"  [arg-type]
supernote/cli/notebook.py:191: error: Call to untyped function "load_notebook" in typed context  [no-untyped-call]
supernote/cli/notebook.py:192: error: Call to untyped function "merge" in typed context  [no-untyped-call]
supernote/cli/notebook.py:197: error: Function is missing a type annotation  [no-untyped-def]
supernote/cli/notebook.py:198: error: Call to untyped function "load_notebook" in typed context  [no-untyped-call]
supernote/cli/notebook.py:199: error: Call to untyped function "reconstruct" in typed context  [no-untyped-call]
supernote/cli/notebook.py:204: error: Function is missing a type annotation  [no-untyped-def]
supernote/cli/notebook.py:215: error: Function is missing a type annotation  [no-untyped-def]
supernote/cli/client.py:39: error: Argument 1 to "asynccontextmanager" has incompatible type "Callable[[str | None], Supernote]"; expected "Callable[[str | None], AsyncIterator[Never]]"  [arg-type]
supernote/cli/client.py:40: error: The return type of an async generator function should be "AsyncGenerator" or one of its supertypes  [misc]
supernote/cli/client.py:114: error: Argument 1 to "save_credentials" of "FileCacheAuth" has incompatible type "str | None"; expected "str"  [arg-type]
supernote/cli/client.py:211: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
supernote/cli/client.py:225: error: Need type annotation for "sn"  [var-annotated]
supernote/cli/client.py:250: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
supernote/cli/client.py:269: error: Need type annotation for "sn"  [var-annotated]
supernote/cli/client.py:278: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
supernote/cli/client.py:298: error: Need type annotation for "sn"  [var-annotated]
supernote/cli/client.py:310: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
supernote/cli/client.py:326: error: Need type annotation for "sn"  [var-annotated]
supernote/cli/client.py:335: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
supernote/cli/client.py:345: error: Need type annotation for "sn"  [var-annotated]
supernote/cli/client.py:359: error: Need type annotation for "sn"  [var-annotated]
supernote/cli/client.py:419: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
supernote/cli/client.py:424: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
supernote/cli/client.py:440: error: Need type annotation for "sn"  [var-annotated]
supernote/cli/client.py:477: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
supernote/cli/client.py:491: error: Function is missing a type annotation  [no-untyped-def]
supernote/cli/admin.py:14: error: Function is missing a return type annotation  [no-untyped-def]
supernote/cli/admin.py:18: error: Need type annotation for "session"  [var-annotated]
supernote/cli/admin.py:54: error: Function is missing a return type annotation  [no-untyped-def]
supernote/cli/admin.py:56: error: Need type annotation for "session"  [var-annotated]
supernote/cli/admin.py:91: error: Function is missing a type annotation  [no-untyped-def]
supernote/cli/admin.py:100: error: Function is missing a type annotation  [no-untyped-def]
supernote/cli/admin.py:101: error: Call to untyped function "list_users_async" in typed context  [no-untyped-call]
supernote/cli/admin.py:104: error: Function is missing a return type annotation  [no-untyped-def]
supernote/cli/admin.py:106: error: Need type annotation for "session"  [var-annotated]
supernote/cli/admin.py:120: error: Function is missing a type annotation  [no-untyped-def]
supernote/cli/admin.py:132: error: Function is missing a type annotation  [no-untyped-def]
supernote/cli/server.py:55: error: Function is missing a type annotation  [no-untyped-def]
supernote/cli/server.py:80: error: Call to untyped function "add_parser" in typed context  [no-untyped-call]
Found 383 errors in 11 files (checked 212 source files)
```
