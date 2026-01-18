# Regex Inverter

This directory contains a web-based Regex Inverter tool powered by [PyScript](https://pyscript.net/) and `pyparsing`.

## Overview

The Regex Inverter allows you to enter a regular expression and generate all possible strings that match it. It is particularly useful for visualizing the expansion of character classes, repetitions, and alternatives.

### Key Features:
- **Expansion of Regex Patterns:** Generates matching strings for patterns like `[A-Z]{3}\d{3}`.
- **Client-Side Processing:** All computations happen in your browser using PyScript, so no data is sent to a server.
- **Progress Tracking:** Shows the total count of possible matches, even if they exceed the display limit.

### Supported Syntax:
- Character sets: `[a-z]`, `[0-9A-F]`, `[^0-9]`
- Repetitions: `{n}`, `{min,max}`, `{,max}`
- Alternatives: `apple|orange`
- Groups: `(abc|def)`
- Macros: `\d`, `\w`, `\s`, `\D`, `\W`, `\S`
- Dot: `.` (matches printable characters)

### Constraints:
- **Unbounded operators `+` and `*` are not supported.** You must use explicit range repetitions like `{1,10}` instead of `+` to prevent infinite or excessively large result sets that would crash the browser.

## Files

- `index.html`: The web interface and PyScript configuration.
- `inv_regex.py`: The core inversion logic using `pyparsing`.

## How to Run Locally

To run the Regex Inverter on your own machine:

1.  Open a terminal or command prompt.
2.  Navigate to this directory:
    ```bash
    cd examples/regex_inverter
    ```
3.  Start a local Python web server:
    ```bash
    python -m http.server
    ```
4.  Open your web browser and go to:
    [http://localhost:8000](http://localhost:8000)

## Deployment

To deploy this to a web server:

1.  Upload both `index.html` and `inv_regex.py` to the same directory on your web server.
2.  Ensure your server is configured to serve `.html` files (most are by default).
3.  Access the `index.html` file through its URL.

Since this is a static site (using PyScript to run Python in the browser), you can even host it on GitHub Pages or any other static site hosting service.
