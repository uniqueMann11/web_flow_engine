import { useState, useEffect } from "react";
import { Play, RotateCcw, Sparkles } from "lucide-react";
import { fetchPresets } from "../api.js";

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
  const [presets, setPresets] = useState([]);
  const [selectedPreset, setSelectedPreset] = useState("");

  useEffect(() => {
    fetchPresets()
      .then((data) => {
        if (data && data.presets) {
          setPresets(data.presets);
        }
      })
      .catch((err) => console.warn("Failed to load presets:", err));
  }, []);

  function set(key) {
    return (e) => {
      const val = e.target.type === "checkbox" ? e.target.checked : e.target.value;
      setForm((f) => ({ ...f, [key]: val }));
    };
  }

  function handlePresetChange(e) {
    const val = e.target.value;
    setSelectedPreset(val);
    if (!val) return;
    const preset = presets.find((p) => p.name === val);
    if (preset) {
      setForm((prev) => ({
        ...prev,
        page_title: preset.page_title || "",
        page_type: preset.page_type || "Comparison",
        primary_keyword: preset.primary_keyword || "",
        secondary_keyword: preset.secondary_keyword || "",
        content_angle: preset.content_angle || "",
        model: preset.model || prev.model,
      }));
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    if (!form.page_title.trim()) return;
    onRun(form);
  }

  function reset(e) {
    e.preventDefault();
    setForm(DEFAULTS);
    setSelectedPreset("");
  }

  return (
    <aside className="config-panel">
      <form onSubmit={handleSubmit}>
        {/* Preset Picker */}
        {presets.length > 0 && (
          <div className="panel-section">
            <div className="panel-section-title">
              <Sparkles size={12} style={{ marginRight: "4px" }} /> Quick Presets
            </div>
            <div className="field">
              <select
                id="presetPicker"
                value={selectedPreset}
                onChange={handlePresetChange}
                disabled={running}
              >
                <option value="">-- Load a Page Type Preset --</option>
                {presets.map((p) => (
                  <option key={p.name} value={p.name}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}

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

        {/* Pipeline Settings */}
        <div className="panel-section">
          <div className="panel-section-title">Generation Settings</div>
          
          <div className="field">
            <label htmlFor="inputModel">Model</label>
            <input
              id="inputModel"
              value={form.model}
              onChange={set("model")}
              placeholder="openrouter/deepseek/deepseek-v4-flash"
              disabled={running}
            />
          </div>

          <div className="field">
            <label htmlFor="inputOutputFilename">Custom Output Filename (Optional)</label>
            <input
              id="inputOutputFilename"
              value={form.output_filename}
              onChange={set("output_filename")}
              placeholder="page-custom-title.html"
              disabled={running}
            />
          </div>

          <div className="field-checkbox" style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "8px" }}>
            <input
              type="checkbox"
              id="checkSkipGen"
              checked={form.skip_generate}
              onChange={set("skip_generate")}
              disabled={running}
            />
            <label htmlFor="checkSkipGen" style={{ margin: 0, fontSize: "0.8rem", cursor: "pointer" }}>
              Skip AI generation (compile only)
            </label>
          </div>

          <div className="field-checkbox" style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "6px" }}>
            <input
              type="checkbox"
              id="checkSkipWidget"
              checked={form.skip_widget}
              onChange={set("skip_widget")}
              disabled={running}
            />
            <label htmlFor="checkSkipWidget" style={{ margin: 0, fontSize: "0.8rem", cursor: "pointer" }}>
              Skip hero widget injection
            </label>
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
