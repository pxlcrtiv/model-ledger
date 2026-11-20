/* Spec-driven ModelRecord renderer — the web adapter of the format spec
 * exported by cli/model_ledger/formatter.py (to_json_spec) and embedded in
 * index.html as <script type="application/json" id="format-spec">.
 *
 * All presentation rules (field order, label width, timestamp style, the
 * empty-URI dash) live in the spec; this file only interprets it.
 * Loadable as a plain browser script and via require() in node tests.
 */
function renderRecord(spec, r) {
  return spec
    .map(function (entry) {
      var value = r[entry.key];
      var text;
      if (entry.type === "timestamp") {
        text =
          new Date(Number(value) * 1000).toISOString().replace("T", " ").slice(0, 19) + " UTC";
      } else {
        text = String(value == null ? "" : value);
        if (text === "" && entry.empty) text = entry.empty;
      }
      return "  " + entry.key.padEnd(entry.width) + text;
    })
    .join("\n");
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { renderRecord: renderRecord };
}
