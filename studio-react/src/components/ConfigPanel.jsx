import { useState } from "react";
import { Play, RotateCcw } from "lucide-react";

const PAGE_TYPES = [
  "Comparison",
  "Service x Industry",
  "Glossary / Definition",
  "Hire-a-Role",
  "Technology / Integration",
  "Editorial Blog (Discover)",
];

const DEFAULTS = {
  page_title: "LangChain vs LlamaIndex: The Definitive Framework Comparison",
  page_type: "Comparison",
  primary_keyword: "LangChain vs LlamaIndex",
  secondary_keyword: "RAG framework comparison, LLM agent orchestration",
  content_angle: "Hands-on engineering reality: LangGraph multi-step agent graphs vs LlamaIndex hierarchical index retrieval speed, memory overhead, and hybrid production architecture in 2026.",
  model: "openrouter/deepseek/deepseek-v4-flash",
  output_filename: "",
  skip_generate: false,
  skip_widget: false,
};

export default function ConfigPanel({ running, onRun }) {
  const [form, setForm] = useState(DEFAULTS);

  function set(key) {
    return (e) => {
      const val = e.target.type === "checkbox" ? e.target.checked : e.target.value;
      setForm((f) => ({ ...f, [key]: val }));
    };
  }

  function handleSubmit(e) {
    e.preventDefault();
    if (!form.page_title.trim()) return;
    onRun(form);
  }

  function reset(e) {
    e.preventDefault();
    setForm(DEFAULTS);
  }

  return (
    <aside className="config-panel">
      <form onSubmit={handleSubmit}>
        {/* Page Configuration */}
        <div className="panel-section">
          <div className="panel-section-title">Page Configuration</div>
          
          <div className="field">
            <label htmlFor="inputTitle">
              Page Title <span style={{ color: "var(--accent-rose)" }}>*</span>
            </label>
            <input
              id="inputTitle"
              value={form.page_title}
              onChange={set("page_title")}
              placeholder="e.g. LangChain vs LlamaIndex Comparison"
              required
              disabled={running}
            />
          </div>

          <div className="field">
            <label htmlFor="inputType">
              Page Type <span style={{ color: "var(--accent-rose)" }}>*</span>
            </label>
            <select
              id="inputType"
              value={form.page_type}
              onChange={set("page_type")}
              disabled={running}
            >
              {PAGE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>

          <div className="field">
            <label htmlFor="inputPrimaryKw">Primary Keyword (SEO)</label>
            <input
              id="inputPrimaryKw"
              value={form.primary_keyword}
              onChange={set("primary_keyword")}
              placeholder="e.g. LangChain vs LlamaIndex"
              disabled={running}
            />
          </div>

          <div className="field">
            <label htmlFor="inputSecondaryKw">Secondary Keyword(s)</label>
            <input
              id="inputSecondaryKw"
              value={form.secondary_keyword}
              onChange={set("secondary_keyword")}
              placeholder="e.g. RAG frameworks, LLM agent architecture"
              disabled={running}
            />
          </div>
        </div>

        {/* Content Strategy */}
        <div className="panel-section">
          <div className="panel-section-title">Content Differentiator</div>
          <div className="field">
            <label htmlFor="inputAngle">
              Content Angle / Notes
              <span style={{ display: "block", fontSize: "0.72rem", color: "var(--muted)", fontWeight: "normal", marginTop: "2px" }}>
                Crucial differentiator to prevent thin-content territory.
              </span>
            </label>
            <textarea
              id="inputAngle"
              rows={4}
              value={form.content_angle}
              onChange={set("content_angle")}
              placeholder="Provide specific architectural trade-offs, real-world benchmarks, nuances, pricing realities, and concrete takeaways..."
              disabled={running}
            />
          </div>
        </div>

        {/* Actions */}
        <div className="panel-section">
          <button
            type="submit"
            className="run-btn"
            disabled={running || !form.page_title.trim()}
          >
            {running ? (
              <>
                <div className="spinner" /> Generating Website...
              </>
            ) : (
              <>
                <Play size={13} /> Run Pipeline
              </>
            )}
          </button>
          <button
            type="button"
            className="icon-btn"
            style={{ width: "100%", justifyContent: "center", marginTop: "6px" }}
            onClick={reset}
            disabled={running}
          >
            <RotateCcw size={12} /> Reset Form
          </button>
        </div>
      </form>
    </aside>
  );
}
