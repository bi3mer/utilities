# Rewriting the Utilities in Common Lisp

*Notes from a review on 2026-10-10.*

This report covers a review of `utility-file-server`, the changes made during that review, and an estimate for the planned rewrite. The plan replaces every utility with one Common Lisp program, `util`, that takes the utility name as its first argument (`util timer -m 5`).

## Summary

Six of the nine utilities port directly to Common Lisp. The two PDF tools port by calling Ghostscript, pandoc and Chromium, which are already installed. Orality depends on Stanza, a neural part-of-speech tagger with no Lisp equivalent, so it should stay in Python. The rewrite comes to about 500 lines of Lisp with Quicklisp libraries, or about 800 without them.

## Review of utility-file-server

`utility-file-server` is a 51-line Go program. It serves the current directory over HTTP on port 42069, or on a port given as its only argument. It builds with Go 1.27, and `go vet` reports nothing. It handled every argument tested (`abc`, `70000`, two arguments, `-h`, `-5`), and requests containing `..` return 404.

| # | Problem | Status |
|---|---|---|
| 1 | `.gitignore` line 296 (`*.mod*`, from a kernel-module template) also matches `go.mod`. Commit `bd711ae` therefore has no `go.mod`, and `install.sh` skips the utility on a fresh clone without reporting a failure. Go projects created by `utility-new` have the same problem. | Fixed, not committed |
| 2 | The server listened on every network interface, so anyone on the same network could browse the folder. The startup message printed `0.0.0.0`, which another device cannot use. | Fixed, not committed |
| 3 | It serves hidden files. A test request for `.env` returned its contents. | Accepted as is |
| 4 | It follows symlinks out of the served folder. A test symlink returned a file from outside it. | Accepted as is |
| 5 | The request log omits the status code, so a 404 looks like a success. | Open |
| 6 | It prints "Serving ..." before opening the port. A port conflict shows that message, then an error. | Open |

## Uncommitted Changes

- **`.gitignore`:** a new `!go.mod` line after the `*.mod*` rule. `git status` now lists `utility-file-server/go.mod` as untracked. The line only matters while the repository contains Go code.
- **`utility-file-server/main.go`:** the server now listens on `127.0.0.1` by default. A new `-lan` flag listens on every interface and prints each LAN address, such as `http://192.168.1.92:42069/`. `-lan` must come before the port.

In testing, the default mode answered on `127.0.0.1` and `localhost` and refused connections on `192.168.1.92`. With `-lan`, it answered on `192.168.1.92`. The copy installed in `.venv/bin` stays the old build until `./install.sh` runs again. The Lisp rewrite would replace `main.go`, including this change.

## Common Lisp Toolchain

This machine has SBCL 2.6.8, built with thread support and compressed executables. Quicklisp is installed in `~/.quicklisp`, with only `usocket` downloaded so far. Ghostscript, pandoc, Chromium, `pdftoppm` and ImageMagick are also installed.

A hello-world SBCL executable measured:

| Build | Size | Startup |
|---|---|---|
| Uncompressed | 35 MB | 0.004 s |
| Compressed | 11 MB | 0.029 s |

For comparison, the Go file-server binary is 8.7 MB. Either startup time is fine for a command-line tool, so use compression.

## Porting the File Server

| Approach | Lines | Effort | Needs |
|---|---|---|---|
| Hunchentoot | 60 to 80 | A few hours | Quicklisp |
| `sb-bsd-sockets`, which ships with SBCL | 200 to 250 | About a day | Nothing extra |

Hunchentoot serves files, sets content types and logs status codes. It does not generate directory listings, which take about 20 lines to add. Push `:hunchentoot-no-ssl` onto `*features*` before loading it, so the executable does not need OpenSSL at startup. Its `start` function returns immediately, so the main function has to wait on the server thread.

Without Hunchentoot, you write request parsing, `%` decoding, path mapping, file sending, directory listings, a content-type table and error handling for each connection. A minimal version also drops three features of Go's file server: byte-range requests, keep-alive connections and `If-Modified-Since` caching. Byte ranges matter most. Browsers need them to skip ahead in a video or resume a download. Apple's Safari Web Content Guide also says iOS needs them to play media at all. Supporting ranges takes about 30 more lines.

## The util Rewrite

### Each Utility

| Command | Now | Current lines | In Lisp | Lisp lines |
|---|---|---|---|---|
| timer | OCaml | 41 | Direct port | 30 |
| coin-flip | Python | 104 | Direct port | 60 |
| update | Python | 21 | Direct port: `git pull`, then rebuild | 20 |
| file-server | Go | 51 | Hunchentoot, or written by hand | 70 or 225 |
| pretty-print-json | Python | 15 | JSON library (jzon), or a parser written by hand | 20 or 150 |
| new | OCaml | 143 | Mostly unnecessary (see Structure) | 0 to 30 |
| invert-pdf | Python + PyMuPDF | 85 | Call Ghostscript | 40 |
| md-to-pdf | Python + markdown, WeasyPrint, PyMuPDF | 162 | pandoc for HTML, headless Chromium for PDF, Ghostscript to invert | 70 |
| orality | Python + Stanza, cmudict | 322, plus 742 of web files | No Lisp replacement for Stanza | Keep in Python |

The dispatcher, shared argument helpers and build script add about 150 lines.

### Structure

- **Commands:** each command lives in its own file under `src/commands/`. A small `defcommand` macro registers its name, one-line help text and function. Running `util` with no arguments lists the commands.
- **Build:** `build.lisp` loads every file in `src/commands/` and saves one executable. Adding a command means adding a file, so `utility-new` has little left to do.
- **Old names:** `install.sh` links `utility-timer` and the other old names to `util`. `util` checks which name started it, the way BusyBox does, so existing commands and scripts keep working.

### Libraries

With one binary, the decision about libraries applies to the whole project. Quicklisp provides jzon for JSON, Hunchentoot for both web servers, and clingon for subcommand argument parsing. Without Quicklisp, you write the JSON parser and the HTTP server yourself, which accounts for most of the 300-line difference. Quicklisp is already set up here, so use it.

### PDF Commands

This Ghostscript command was tested on a sample PDF:

```
gs -q -o out.pdf -sDEVICE=pdfimage24 -r144 \
  -c "{1 exch sub}{1 exch sub}{1 exch sub}{1 exch sub} setcolortransfer" -f in.pdf
```

It drew each page as a 144 dpi RGB image with inverted colors, which matches the Python version. White became black, and red became cyan. `invert-pdf` only needs to build this command from its arguments.

`md-to-pdf` also needs a CSS layout engine to turn HTML into PDF, and Lisp has none. pandoc can produce the HTML, headless Chromium can print it to PDF, and the Ghostscript command can invert the result. This pipeline is untested.

### Orality

Stanza splits text into sentences and tags each word's part of speech. Common Lisp has no tagger of similar quality. The scoring math, the CMU dictionary lookup and the web server would all port easily, but scores computed with a weaker tagger would change. `util orality` should run the existing Python version.

### Gotchas

- **Ctrl-C:** catch `sb-sys:interactive-interrupt`. Otherwise Ctrl-C opens the SBCL debugger instead of quitting.
- **Errors on threads:** an unhandled error in a standalone executable opens the debugger. A browser closing a connection mid-download causes one. Wrap each connection in `handler-case`, and close the socket in `unwind-protect`.
- **File names:** Lisp pathnames treat `*`, `?` and `[` as wildcards. On this SBCL, `(probe-file "photo[1].jpg")` signals "Can't find the TRUENAME of wild pathname". Pass names through `sb-ext:parse-native-namestring` first.
- **Rebuilding while running:** `util update` rebuilds `util` while it runs. Linux refuses to open a running executable for writing ("Text file busy"). Write the build to a temporary file and rename it over the old one.
- **One build for everything:** an unbalanced parenthesis in any command file stops the whole build, so a half-finished command blocks updates to the others.

## Suggested Order

1. Commit or discard the uncommitted Go changes.
2. Build the dispatcher, `build.lisp` and the `install.sh` changes, with `timer` and `coin-flip` as the first commands.
3. Port `pretty-print-json`, `update` and `file-server`.
4. Port `invert-pdf` with Ghostscript, then `md-to-pdf`.
5. Make `util orality` run the Python version.
6. Delete the old utility directories and the `install.sh` and `uninstall.sh` branches nothing uses anymore.

## Other Finding

`utility-invert-pdf/pyproject.toml` declares no dependencies but imports PyMuPDF (`fitz`). It works today only because `utility-md-to-pdf` installs PyMuPDF into the same venv.
