"""Headless render check for the visual-maker and demo-builder helpers (spec section 7).

    python3 -I shot.py <file> <png> [--width 1280] [--height 800] [--dark]

Loads <file> from a file:// URL in headless Chromium through Python Playwright, waits
for the load event, and saves a screenshot to <png>. For HTML the screenshot is the full
page, so a page wider than the window shows up wider in the picture; for an SVG it is
the window. Study pages work offline, so http and https requests are blocked and
reported.

- exit 0: screenshot saved; each console error, page error and blocked request is
  printed as one line, `console: <text>`
- exit 2: bad arguments, or the page failed to load (message on stderr)
- exit 3: Python Playwright or its Chromium is not installed (message on stderr)

Standard library apart from Playwright; runs on Python 3.9.
"""
import argparse
import site
import sys
from pathlib import Path

MAX_LINES = 30
MAX_CHARS = 500
SETTLE_MS = 250
INSTALL_CHROMIUM = "`python3 -m playwright install chromium`"


def size(text):
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a whole number")
    if not 0 < value <= 10000:
        raise argparse.ArgumentTypeError(f"{value} is not between 1 and 10000")
    return value


def parse_args(argv):
    """The arguments; anything wrong exits 2 with a message on stderr."""
    parser = argparse.ArgumentParser(prog="shot.py", description="Render a file in headless Chromium and save a screenshot.")
    parser.add_argument("file", help="the HTML or SVG file to load")
    parser.add_argument("png", help="where to save the screenshot")
    parser.add_argument("--width", type=size, default=1280, help="window width in px (default 1280)")
    parser.add_argument("--height", type=size, default=800, help="window height in px (default 800)")
    parser.add_argument("--dark", action="store_true", help="ask the page for its dark color scheme")
    args = parser.parse_args(argv)
    if not Path(args.file).is_file():
        parser.error(f"{args.file} is not a file")
    png = Path(args.png)
    if png.suffix.lower() != ".png":
        parser.error(f"{args.png} does not end in .png")
    if not png.absolute().parent.is_dir():
        parser.error(f"the folder for {args.png} does not exist")
    return args


def load_playwright():
    """Playwright's sync API module, or None when it is not installed.

    `-I` leaves out the user's site-packages, where `pip install --user` puts
    Playwright, so that folder is tried last.
    """
    try:
        from playwright import sync_api
    except ImportError:
        user_site = site.getusersitepackages()
        if user_site in sys.path or not Path(user_site).is_dir():
            return None
        sys.path.append(user_site)
        try:
            from playwright import sync_api
        except ImportError:
            return None
    return sync_api


def one_line(text):
    text = " ".join(str(text).split())
    return text if len(text) <= MAX_CHARS else text[: MAX_CHARS - 3] + "..."


def main(argv=None):
    args = parse_args(argv)
    api = load_playwright()
    if api is None:
        print(
            "shot.py: Python Playwright is not installed; install it with"
            f" `python3 -m pip install playwright`, then {INSTALL_CHROMIUM}",
            file=sys.stderr,
        )
        return 3

    errors = []

    def on_console(message):
        if message.type == "error":
            errors.append(message.text)

    def on_page_error(error):
        errors.append(getattr(error, "message", error))

    def on_request(route):
        url = route.request.url
        if url.startswith(("http:", "https:")):
            errors.append("blocked network request " + url)
            route.abort()
        else:
            route.continue_()

    with api.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except api.Error as e:
            first = str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
            print(f"shot.py: Chromium did not start ({one_line(first)}); install it with {INSTALL_CHROMIUM}", file=sys.stderr)
            return 3
        try:
            page = browser.new_page(
                viewport={"width": args.width, "height": args.height},
                color_scheme="dark" if args.dark else "light",
            )
            page.on("console", on_console)
            page.on("pageerror", on_page_error)
            page.route("**/*", on_request)
            page.goto(Path(args.file).resolve().as_uri(), wait_until="load")
            page.wait_for_timeout(SETTLE_MS)
            # A full-page shot of an SVG document never finishes (Playwright 1.64).
            html = page.evaluate("document.documentElement instanceof HTMLElement")
            page.screenshot(path=args.png, full_page=html)
        except api.Error as e:
            print(f"shot.py: the page failed to load: {one_line(e)}", file=sys.stderr)
            return 2
        finally:
            browser.close()

    for text in errors[:MAX_LINES]:
        print("console: " + one_line(text))
    if len(errors) > MAX_LINES:
        print(f"console: {len(errors) - MAX_LINES} more not shown")
    return 0


if __name__ == "__main__":
    sys.exit(main())
