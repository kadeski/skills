import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SHOT = Path(__file__).resolve().parents[2] / "plugins" / "study" / "scripts" / "shot.py"

# Runs shot.py the way `python3 -I` does, with Playwright hidden: a None entry in
# sys.modules makes `import playwright` raise ImportError even where it is installed.
HIDDEN = (
    "import runpy, sys\n"
    "sys.modules['playwright'] = None\n"
    "sys.modules['playwright.sync_api'] = None\n"
    "sys.argv = sys.argv[1:]\n"
    "runpy.run_path(sys.argv[0], run_name='__main__')\n"
)

PAGE = """<!doctype html>
<meta charset="utf-8">
<title>shot test</title>
<p>shot test</p>
<script>
console.log("not an error");
console.error("boom " + innerWidth + " " + (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
fetch("https://example.com/x.js").catch(function () {});
setTimeout(function () { throw new Error("late failure"); }, 0);
</script>
"""


def run(*args, hide=False):
    cmd = [sys.executable, "-I"] + (["-c", HIDDEN] if hide else []) + [str(SHOT)] + [str(a) for a in args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120)


class ShotTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.page = self.dir / "page.html"
        self.page.write_text(PAGE, encoding="utf-8")
        self.png = self.dir / "shot.png"

    def tearDown(self):
        self.tmp.cleanup()

    def assertExit(self, result, code):
        self.assertEqual(result.returncode, code, result.stderr)


class ArgumentsTest(ShotTest):
    def test_bad_arguments_exit_2(self):
        cases = [
            [],
            [self.page],
            [self.dir / "missing.html", self.png],
            [self.dir, self.png],
            [self.page, self.dir / "shot.jpg"],
            [self.page, self.dir / "no-folder" / "shot.png"],
            [self.page, self.png, "--width", "0"],
            [self.page, self.png, "--width", "wide"],
            [self.page, self.png, "--height", "-5"],
            [self.page, self.png, "--colour"],
        ]
        for args in cases:
            with self.subTest(args=args):
                result = run(*args)
                self.assertExit(result, 2)
                self.assertTrue(result.stderr.strip())
                self.assertEqual(result.stdout, "")
        self.assertFalse(self.png.exists())


class MissingPlaywrightTest(ShotTest):
    def test_exit_3_without_playwright(self):
        result = run(self.page, self.png, hide=True)
        self.assertExit(result, 3)
        self.assertIn("Playwright", result.stderr)
        self.assertIn("playwright install chromium", result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertFalse(self.png.exists())

    def test_bad_arguments_win_over_missing_playwright(self):
        self.assertExit(run(self.page, hide=True), 2)


class RenderTest(ShotTest):
    def render(self, *extra):
        result = run(self.page, self.png, *extra)
        if result.returncode == 3:
            self.skipTest("Playwright or its Chromium is not installed: " + result.stderr.strip())
        self.assertExit(result, 0)
        self.assertEqual(self.png.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        return result.stdout.splitlines()

    def test_console_and_page_errors(self):
        lines = self.render()
        self.assertIn("console: boom 1280 light", lines)
        self.assertIn("console: blocked network request https://example.com/x.js", lines)
        self.assertTrue(any(l.startswith("console: ") and "late failure" in l for l in lines), lines)
        self.assertFalse(any("not an error" in l for l in lines), lines)
        self.assertTrue(all(l.startswith("console: ") for l in lines), lines)

    def test_width_and_dark(self):
        self.assertIn("console: boom 390 dark", self.render("--width", "390", "--dark"))

    def test_svg(self):
        self.page = self.dir / "picture.svg"
        self.page.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">'
            '<rect width="200" height="100" fill="#fff"/><text x="10" y="50">A label</text></svg>',
            encoding="utf-8",
        )
        self.assertEqual(self.render(), [])


if __name__ == "__main__":
    unittest.main()
