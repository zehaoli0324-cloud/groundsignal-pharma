"""Synthetic checks for offline review editing and source preservation."""
from copy import deepcopy
from html.parser import HTMLParser
import json
import shutil
import subprocess
import unittest

from scripts.patient_eval.candidate_review_ui import render_review_workspace


def packet():
    return {"schema_version": "candidate-review/v0.1", "reviewer_id": "A",
            "packet_sha256": "synthetic-packet-identity", "items": [{
                "candidate_id": "C0001", "turns": [
                    {"turn_id": "r0001", "role": "patient", "content": "昨天开始不舒服。"},
                    {"turn_id": "r0002", "role": "doctor", "content": "请问从何时开始？"}],
                "privacy_findings": [], "fact_draft": {"fact_candidates": []},
                "review": {"privacy": {"decision": "unreviewed", "reason": "",
                            "checked_turn_ids": [], "additional_spans": []},
                           "completeness": {"decision": "unreviewed", "reason": "", "evidence_turn_ids": []},
                           "facts": [], "rubrics": []}}]}


class Scripts(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.scripts, self.current, self.tags = [], None, []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag == "script":
            self.current = {"attrs": dict(attrs), "text": ""}

    def handle_data(self, data):
        if self.current is not None:
            self.current["text"] += data

    def handle_endtag(self, tag):
        if tag == "script" and self.current is not None:
            self.scripts.append(self.current)
            self.current = None


class CandidateReviewUITests(unittest.TestCase):
    def test_embedded_sources_are_escaped_and_exactly_recoverable(self):
        source = packet()
        attack = '</script><script>alert("source")</script><img src=x onerror=alert(1)> & \u2028'
        source["items"][0]["turns"][0]["content"] = attack
        source["items"][0]["review"]["privacy"]["reason"] = attack
        source["reviewer_id"] = attack
        original = deepcopy(source)
        page = render_review_workspace(source)
        parsed = Scripts(page)
        self.assertEqual(len(parsed.scripts), 2)
        self.assertEqual(json.loads(parsed.scripts[0]["text"]), source)
        self.assertNotIn(attack, page)
        self.assertNotIn("<", parsed.scripts[0]["text"])
        self.assertEqual(source, original)
        self.assertNotIn("innerHTML", parsed.scripts[1]["text"])

    def test_workspace_has_no_remote_assets_or_persistence(self):
        parsed = Scripts(render_review_workspace(packet()))
        for tag, attrs in parsed.tags:
            self.assertFalse("src" in attrs or "href" in attrs, (tag, attrs))
        script = parsed.scripts[1]["text"]
        for capability in ("fetch(", "XMLHttpRequest", "localStorage", "sessionStorage", "sendBeacon", "eval("):
            self.assertNotIn(capability, script)
        self.assertIn("connect-src 'none'", render_review_workspace(packet()))
        self.assertIn("textContent = turn.content", script)

    def test_rejects_missing_or_duplicate_identity(self):
        for source in ({"items": []}, {"packet_sha256": "id", "items": [{"candidate_id": ""}]}):
            with self.assertRaises(ValueError):
                render_review_workspace(source)
        source = packet()
        source["items"].append(deepcopy(source["items"][0]))
        with self.assertRaises(ValueError):
            render_review_workspace(source)

    @unittest.skipUnless(shutil.which("node"), "Node is optional for offline editor behavior check")
    def test_save_edits_only_mutable_review_and_reviewer_fields(self):
        source = packet()
        source["items"].append(deepcopy(source["items"][0]))
        source["items"][1]["candidate_id"] = "C0002"
        parsed = Scripts(render_review_workspace(source))
        # Minimal DOM exercises the real editor script, without network/browser
        # dependencies or any real patient text.
        harness = r'''
const assert = require('assert');
const elements = new Map(); let downloaded = null;
function element() { return {value:'',textContent:'',hidden:false,children:[],events:{},
 appendChild(c){this.children.push(c);},append(...c){this.children.push(...c);},
 replaceChildren(){this.children=[];},addEventListener(name,fn){this.events[name]=fn;},
 click(){if(this.events.click)this.events.click();},remove(){}}; }
global.document = {getElementById(id){if(!elements.has(id))elements.set(id,element());return elements.get(id);},
 createElement:element,body:element()};
global.window = {addEventListener(){}};
global.URL = {createObjectURL(blob){downloaded=blob;return 'blob:local';},revokeObjectURL(){}};
global.setTimeout = fn => fn();
document.getElementById('packet-data').textContent = INPUT_PACKET;
'''.replace("INPUT_PACKET", json.dumps(parsed.scripts[0]["text"]))
        assertions = r'''
const original = clone(source);
el('reviewer').value = 'Reviewer-B';
el('privacy-reason').value = '已逐条检查，待第二人复核';
el('privacy-turns').value = 'r0001，r0002';
el('facts').value = '{bad json';
el('candidate').value = '1'; el('candidate').events.change();
assert.equal(selected, 0); assert.equal(el('candidate').value, '0');
assert.notEqual(el('error').textContent, ''); assert.equal(downloaded, null);
el('facts').value = '[]'; el('candidate').value = '1'; el('candidate').events.change();
assert.equal(selected, 1); assert.equal(drafts[0].privacy.reason, '已逐条检查，待第二人复核');
el('save').events.click();
(async () => {
 const output = JSON.parse(await downloaded.text());
 assert.equal(output.reviewer_id, 'Reviewer-B');
 assert.equal(output.packet_sha256, original.packet_sha256);
 assert.equal(output.items[0].review.privacy.decision, 'unreviewed');
 assert.deepEqual(output.items[0].review.privacy.checked_turn_ids, ['r0001','r0002']);
 for(let i=0;i<original.items.length;i++) {
   const before=clone(original.items[i]), after=clone(output.items[i]); delete before.review; delete after.review;
   assert.deepEqual(before, after);
 }
 assert.deepEqual(source, original);
 process.stdout.write('editor roundtrip passed');
})().catch(error => {process.stderr.write(String(error));process.exitCode=1;});
'''
        result = subprocess.run([shutil.which("node"), "-"], input=harness + parsed.scripts[1]["text"] + assertions,
                                text=True, capture_output=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("editor roundtrip passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
