/* Node harness: execute the web viewer's real rendering path against the
 * shared golden fixture (argv[2]).
 *
 * Two executions, both behaviour-only, both consuming the format spec
 * embedded in web/index.html (the export of formatter.to_json_spec()):
 *  - "direct": web/render.js, the exact file the page loads.
 *  - "page": the page's actual inline <script>, run in a vm with minimal
 *    DOM stubs, so the embedded-spec parse + fmtRecord wiring are
 *    exercised exactly as a browser would.
 *
 * Prints {"direct": [...], "page": [...]} — rendered strings per case.
 */
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..", "..");
const { renderRecord } = require(path.join(root, "web", "render.js"));

const html = fs.readFileSync(path.join(root, "web", "index.html"), "utf8");
const specBlock = html.match(
  /<script type="application\/json" id="format-spec">([\s\S]*?)<\/script>/
);
if (!specBlock) {
  console.error("embedded format-spec block not found in web/index.html");
  process.exit(2);
}
const spec = JSON.parse(specBlock[1]);

const fixture = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const direct = fixture.cases.map((c) => renderRecord(spec, c.record));

const blocks = [...html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)];
const inline = blocks.filter((m) => !/\bsrc=/.test(m[1]) && !/\btype=/.test(m[1]));
if (inline.length !== 1) {
  console.error("expected exactly one inline script in web/index.html, got " + inline.length);
  process.exit(2);
}

const outEl = { textContent: "" };
const specEl = { textContent: specBlock[1] };
const sandbox = {
  document: {
    getElementById: (id) => (id === "out" ? outEl : id === "format-spec" ? specEl : { value: "" }),
  },
  location: { search: "" },
  URLSearchParams,
  console,
};
vm.createContext(sandbox);
// Load render.js into the page context, as <script src="render.js"> does.
vm.runInContext(fs.readFileSync(path.join(root, "web", "render.js"), "utf8"), sandbox);
vm.runInContext(inline[0][2] + "\n;globalThis.__fmtRecord = fmtRecord;", sandbox);
const page = fixture.cases.map((c) => sandbox.__fmtRecord(c.record));

process.stdout.write(JSON.stringify({ direct, page }));
