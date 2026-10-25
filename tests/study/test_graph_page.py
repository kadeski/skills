import json
import sys
import tempfile
import unittest
from pathlib import Path

SERVER = Path(__file__).resolve().parents[2] / "plugins" / "study" / "server"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "graph" / "data.json"
sys.path.insert(0, str(SERVER))

import graph_page  # noqa: E402
import store  # noqa: E402

DATA_OPEN = '<script type="application/json" id="graph-data">'


def make_data_folder(root):
    """Writes the fixture's goals, plans, sources and graph ops into `root` through store.Store."""
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    s = store.Store(root)
    for goal in fixture["goals"]:
        s.write_json(s.goal_rel(goal["id"], "goal.json"), goal)
    for goal_id, plan in fixture["plans"].items():
        s.write_plan(goal_id, plan)
    for line in fixture["sources"]:
        s.append_jsonl("graph/sources.jsonl", line)
    for op in fixture["propositions"]:
        s.append_jsonl("graph/propositions.jsonl", op)
    for op in fixture["chains"]:
        s.append_jsonl("graph/chains.jsonl", op)
    return s


def page_data(html):
    """The JSON in the page's data block, read up to the first </script> after it."""
    start = html.index(DATA_OPEN) + len(DATA_OPEN)
    return json.loads(html[start:html.index("</script>", start)])


class GraphPageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.s = make_data_folder(Path(self.tmp.name) / "data")
        self.path = graph_page.build(self.s)
        self.html = self.path.read_text(encoding="utf-8")
        self.data = page_data(self.html)

    def tearDown(self):
        self.tmp.cleanup()

    def prop(self, prop_id):
        return next(p for p in self.data["props"] if p["id"] == prop_id)

    def test_writes_graph_html_in_the_data_folder(self):
        self.assertEqual(self.path, self.s.path("graph.html"))
        self.assertTrue(self.html.startswith("<!doctype html>"))
        self.assertEqual([p.name for p in self.path.parent.glob(".graph.html.*")], [])

    def test_no_http_anywhere(self):
        # The fixture has a URL in an alias; the page must still hold no http.
        self.assertNotIn("http", self.html.lower())
        self.assertEqual(self.prop("p_html")["aliases"][1], "Notes from http://example.com/html-notes")

    def test_live_statements_present_and_deleted_absent(self):
        props, chains = self.s.graph()
        self.assertEqual(
            sorted(p["statement"] for p in self.data["props"]),
            sorted(p["statement"] for p in props.values()),
        )
        self.assertEqual(len(self.data["props"]), 15)
        for p in props.values():
            if "<" not in p["statement"]:
                self.assertIn(p["statement"], self.html)
        self.assertEqual({c["id"] for c in self.data["chains"]}, set(chains))
        self.assertNotIn("Dividing by zero", self.html)
        self.assertNotIn("p_gone", self.html)
        self.assertNotIn("c_gone", self.html)

    def test_script_and_comment_text_cannot_break_the_page(self):
        self.assertEqual(self.prop("p_html")["statement"], "In HTML, </script> ends a script block")
        self.assertEqual(self.prop("p_html")["aliases"][0], "<!-- starts an HTML comment")
        # Only the data block and the page script end in </script>, and no comment opens.
        self.assertEqual(self.html.lower().count("</script"), 2)
        self.assertNotIn("<!--", self.html)

    def test_sources_say_where_each_idea_was_taught(self):
        self.assertEqual(self.prop("p_sub3")["sources"], [{
            "goal": "two-step-equations-k3f9", "date": "2026-10-23", "step": "s3", "stepTitle": "Solve for x",
        }])
        # No plan for the second goal: the step id alone.
        self.assertIsNone(self.prop("p_co2")["sources"][0]["stepTitle"])
        self.assertEqual(self.prop("p_inv1")["sources"][0], {"file": "src_n0t3"})
        self.assertEqual(self.prop("p_inv1")["sources"][1]["goal"], "two-step-equations-k3f9")
        self.assertEqual(self.data["files"], [{
            "id": "src_n0t3", "name": "algebra-notes.md", "path": "/Users/learner/notes/algebra-notes.md",
            "date": "2026-10-21",
        }])
        self.assertEqual(self.prop("p_bal2")["aliases"], ["Whatever you do to one side, do to the other"])

    def test_goals_keep_their_color_by_creation_order(self):
        goals = {g["id"]: g for g in self.data["goals"]}
        self.assertEqual(goals["two-step-equations-k3f9"]["color"], 0)
        self.assertEqual(goals["how-plants-make-sugar-m2x8"]["color"], 1)
        self.assertEqual(goals["how-plants-make-sugar-m2x8"]["title"], "How plants make sugar")
        self.assertIsNone(self.data["selected"])

    def test_goal_id_preselects(self):
        html = graph_page.build(self.s, "how-plants-make-sugar-m2x8").read_text(encoding="utf-8")
        self.assertEqual(page_data(html)["selected"], "how-plants-make-sugar-m2x8")

    def test_newer_format_refuses(self):
        self.s.write_json("format.json", {"format": store.FORMAT + 1})
        with self.assertRaises(store.FormatError):
            graph_page.build(self.s)


class EmptyGraphTest(unittest.TestCase):
    def test_empty_data_folder_builds(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = store.Store(Path(tmp) / "new")
            path = graph_page.build(s)
            html = path.read_text(encoding="utf-8")
            data = page_data(html)
            self.assertEqual((data["props"], data["chains"], data["goals"]), ([], [], []))
            self.assertIn("Your knowledge graph is empty", html)
            self.assertNotIn("http", html.lower())


if __name__ == "__main__":
    unittest.main()
