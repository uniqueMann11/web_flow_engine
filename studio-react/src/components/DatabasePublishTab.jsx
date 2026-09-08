import { useState, useEffect } from "react";
import {
  Database,
  CheckCircle,
  XCircle,
  AlertCircle,
  Upload,
  RefreshCw,
  RotateCcw,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import {
  getDbConfigStatus,
  testDbConnection,
  publishToDatabase,
} from "../api.js";

/**
 * DatabasePublishTab
 * ==================
 * Review & edit all 15 fields extracted from the generated page,
 * then publish (INSERT / UPDATE) into the PostgreSQL MST_Page table.
 */
export default function DatabasePublishTab({
  components,
  formData,
  logs,
  onToast,
}) {
  // ── Connection state ────────────────────────────────
  const [dbStatus, setDbStatus] = useState(null); // { configured, host, ... }
  const [connResult, setConnResult] = useState(null); // { success, message }
  const [testing, setTesting] = useState(false);

  // ── Publish state ───────────────────────────────────
  const [publishing, setPublishing] = useState(false);
  const [publishResult, setPublishResult] = useState(null);

  // ── Form fields (the 15 editable fields) ────────────
  const [fields, setFields] = useState({
    page_title: "",
    slug: "",
    page_type: "",
    meta_title: "",
    meta_description: "",
    keywords: "",
    og_title: "",
    og_description: "",
    og_image_url: "",
    publish_datetime: "",
    is_active: true,
    html_content: "",
    schema_script: "",
    css_content: "",
    js_content: "",
  });

  // ── Code section accordion ──────────────────────────
  const [openSection, setOpenSection] = useState(null);

  // ── Original fields for reset ───────────────────────
  const [originalFields, setOriginalFields] = useState(null);

  // Load DB config status on mount
  useEffect(() => {
    getDbConfigStatus()
      .then(setDbStatus)
      .catch(() => setDbStatus({ configured: false }));
  }, []);

  // Auto-populate fields when components or formData change
  useEffect(() => {
    if (!components) return;

    const meta = components.extracted_meta || components.meta_and_og || {};
    const metaAndOg = components.meta_and_og || {};

    // Robust client-side fallback parsing from live logs or components.logs
    let logsMeta = {};
    const logsSource =
      (Array.isArray(logs) ? logs.join("\n") : "") ||
      components.logs ||
      "";
    if (logsSource) {
      const titleMatch = logsSource.match(/Meta Title\s*:\s*(.+)$/m);
      const descMatch = logsSource.match(/Meta Description\s*:\s*(.+)$/m);
      const ogTitleMatch = logsSource.match(/OG Title\s*:\s*(.+)$/m);
      const ogDescMatch = logsSource.match(/OG Description\s*:\s*(.+)$/m);
      if (titleMatch && titleMatch[1]) logsMeta.meta_title = titleMatch[1].trim();
      if (descMatch && descMatch[1]) logsMeta.meta_description = descMatch[1].trim();
      if (ogTitleMatch && ogTitleMatch[1]) logsMeta.og_title = ogTitleMatch[1].trim();
      if (ogDescMatch && ogDescMatch[1]) logsMeta.og_description = ogDescMatch[1].trim();
    }

    const now = new Date();
    const localISO = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 16);

    const finalMetaTitle =
      meta.meta_title ||
      metaAndOg.meta_title ||
      logsMeta.meta_title ||
      components.title ||
      formData?.page_title ||
      "";

    const finalMetaDesc =
      meta.meta_description ||
      metaAndOg.meta_description ||
      logsMeta.meta_description ||
      "";

    const finalOgTitle =
      meta.og_title ||
      metaAndOg.og_title ||
      logsMeta.og_title ||
      formData?.page_title ||
      components.title ||
      "";

    const finalOgDesc =
      meta.og_description ||
      metaAndOg.og_description ||
      logsMeta.og_description ||
      finalMetaDesc ||
      "";

    const populated = {
      page_title: finalMetaTitle,
      slug: formData?.url_slug || meta.url_slug || "",
      page_type: formData?.page_type || "",
      meta_title: finalMetaTitle,
      meta_description: finalMetaDesc,
      keywords: meta.keywords || [formData?.primary_keyword, formData?.secondary_keyword].filter(Boolean).join(", ") || "",
      og_title: finalOgTitle,
      og_description: finalOgDesc,
      og_image_url: meta.og_image_url || formData?.og_image_url || "",
      publish_datetime: formData?.publish_date || localISO,
      is_active: true,
      html_content: components.main_html || "",
      schema_script: components.json_ld || "",
      css_content: components.css || "",
      js_content: components.js || "",
    };

    setFields(populated);
    setOriginalFields(populated);
    setPublishResult(null);
  }, [components, formData, logs]);

  function set(key) {
    return (e) => {
      const val =
        e.target.type === "checkbox" ? e.target.checked : e.target.value;
      setFields((f) => ({ ...f, [key]: val }));
    };
  }

  function resetFields() {
    if (originalFields) {
      setFields(originalFields);
      onToast?.("Fields reset to generated values");
    }
  }

  async function handleTestConnection() {
    setTesting(true);
    setConnResult(null);
    try {
      const result = await testDbConnection();
      setConnResult(result);
      onToast?.(result.success ? "✓ Database connected" : `✗ ${result.message}`);
    } catch (e) {
      setConnResult({ success: false, message: e.message });
      onToast?.(`Connection failed: ${e.message}`);
    }
    setTesting(false);
  }

  async function handlePublish() {
    if (!fields.slug.trim()) {
      onToast?.("URL Slug is required!");
      return;
    }
    setPublishing(true);
    setPublishResult(null);
    try {
      const result = await publishToDatabase(fields);
      setPublishResult(result);
      onToast?.(
        `✓ ${result.action === "UPDATE" ? "Updated" : "Inserted"} page '${result.slug}' (ID: ${result.page_id})`
      );
    } catch (e) {
      setPublishResult({ success: false, message: e.message });
      onToast?.(`Publish failed: ${e.message}`);
    }
    setPublishing(false);
  }

  function toggleSection(name) {
    setOpenSection((s) => (s === name ? null : name));
  }

  // ── Connection status pill ──────────────────────────
  function connBadge() {
    if (!dbStatus) return { label: "Checking...", cls: "" };
    if (!dbStatus.configured) return { label: "Unconfigured", cls: "error" };
    if (connResult?.success) return { label: "Connected", cls: "ready" };
    if (connResult && !connResult.success) return { label: "Disconnected", cls: "error" };
    return { label: "Configured", cls: "running" };
  }

  const badge = connBadge();
  const hasData = !!components;
  const charCount = (val, max) => {
    const len = (val || "").length;
    return (
      <span
        className="db-char-count"
        style={{ color: len > max ? "var(--accent-rose)" : "var(--text-dim)" }}
      >
        {len}/{max}
      </span>
    );
  };

  return (
    <div className="db-publish-tab">
      {/* ── Header bar ──────────────────────────────── */}
      <div className="db-header">
        <div className="db-header-left">
          <Database size={14} />
          <span className="db-header-title">Publish to Database</span>
          <span className={`badge ${badge.cls}`}>{badge.label}</span>
        </div>
        <div className="db-header-right">
          <button
            className="icon-btn"
            onClick={handleTestConnection}
            disabled={testing}
          >
            {testing ? <div className="spinner" /> : <RefreshCw size={12} />}
            Test Connection
          </button>
          <button
            className="icon-btn"
            onClick={resetFields}
            disabled={!originalFields}
          >
            <RotateCcw size={12} /> Reset
          </button>
          <button
            className="db-publish-btn"
            onClick={handlePublish}
            disabled={publishing || !hasData || !fields.slug.trim()}
          >
            {publishing ? (
              <>
                <div className="spinner" /> Publishing...
              </>
            ) : (
              <>
                <Upload size={13} /> Publish to Database
              </>
            )}
          </button>
        </div>
      </div>

      {/* ── Publish result banner ───────────────────── */}
      {publishResult && (
        <div
          className={`db-result-banner ${publishResult.success ? "success" : "error"}`}
        >
          {publishResult.success ? (
            <CheckCircle size={14} />
          ) : (
            <XCircle size={14} />
          )}
          <span>{publishResult.message}</span>
        </div>
      )}

      {!hasData ? (
        <div className="db-empty">
          <AlertCircle size={20} />
          <p>No generated page data available.</p>
          <p style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
            Run the pipeline first to generate a page, then review &amp; publish
            here.
          </p>
        </div>
      ) : (
        <div className="db-body">
          {/* ── Left column: Metadata fields ────────── */}
          <div className="db-col db-col-meta">
            <div className="db-col-title">Page Metadata &amp; SEO</div>

            <div className="field">
              <label>
                Page Title <span style={{ color: "var(--accent-rose)" }}>*</span>
              </label>
              <input value={fields.page_title} onChange={set("page_title")} />
            </div>

            <div className="field">
              <label>
                URL Slug <span style={{ color: "var(--accent-rose)" }}>*</span>
              </label>
              <input
                value={fields.slug}
                onChange={set("slug")}
                placeholder="e.g. langchain-vs-llamaindex"
              />
            </div>

            <div className="db-row-2">
              <div className="field">
                <label>Page Type</label>
                <input value={fields.page_type} onChange={set("page_type")} />
              </div>
              <div className="field">
                <label>Status</label>
                <div className="toggle-row" style={{ paddingTop: 2 }}>
                  <span
                    className="toggle-label"
                    style={{ fontSize: "0.72rem" }}
                  >
                    {fields.is_active ? "Active" : "Inactive"}
                  </span>
                  <label className="toggle-switch">
                    <input
                      type="checkbox"
                      checked={fields.is_active}
                      onChange={set("is_active")}
                    />
                    <span className="toggle-slider" />
                  </label>
                </div>
              </div>
            </div>

            <div className="field">
              <label>Publish Date &amp; Time</label>
              <input
                type="datetime-local"
                value={fields.publish_datetime}
                onChange={set("publish_datetime")}
              />
            </div>

            <div className="db-divider" />

            <div className="field">
              <label>
                Meta Title {charCount(fields.meta_title, 60)}
              </label>
              <input
                value={fields.meta_title}
                onChange={set("meta_title")}
                placeholder="50-60 characters"
              />
            </div>

            <div className="field">
              <label>
                Meta Description {charCount(fields.meta_description, 160)}
              </label>
              <textarea
                rows={3}
                value={fields.meta_description}
                onChange={set("meta_description")}
                placeholder="140-160 characters"
              />
            </div>

            <div className="field">
              <label>Meta Keywords</label>
              <input
                value={fields.keywords}
                onChange={set("keywords")}
                placeholder="comma-separated keywords"
              />
            </div>

            <div className="db-divider" />

            <div className="field">
              <label>
                OG Title {charCount(fields.og_title, 65)}
              </label>
              <input
                value={fields.og_title}
                onChange={set("og_title")}
                placeholder="Social sharing title"
              />
            </div>

            <div className="field">
              <label>
                OG Description {charCount(fields.og_description, 150)}
              </label>
              <textarea
                rows={2}
                value={fields.og_description}
                onChange={set("og_description")}
                placeholder="Social sharing description"
              />
            </div>

            <div className="field">
              <label>OG Image URL (TwitterCard)</label>
              <input
                value={fields.og_image_url}
                onChange={set("og_image_url")}
                placeholder="https://example.com/og-image.jpg"
              />
            </div>
          </div>

          {/* ── Right column: Code assets ───────────── */}
          <div className="db-col db-col-code">
            <div className="db-col-title">Code Assets</div>

            {[
              {
                key: "html_content",
                label: "Page Content (HTML)",
                lang: "html",
                lines: (fields.html_content || "").split("\n").length,
              },
              {
                key: "schema_script",
                label: "Schema Script (JSON-LD)",
                lang: "json",
                lines: (fields.schema_script || "").split("\n").length,
              },
              {
                key: "css_content",
                label: "Custom CSS",
                lang: "css",
                lines: (fields.css_content || "").split("\n").length,
              },
              {
                key: "js_content",
                label: "Custom JS",
                lang: "javascript",
                lines: (fields.js_content || "").split("\n").length,
              },
            ].map((sec) => (
              <div key={sec.key} className="db-code-section">
                <button
                  className="db-code-toggle"
                  onClick={() => toggleSection(sec.key)}
                >
                  {openSection === sec.key ? (
                    <ChevronDown size={13} />
                  ) : (
                    <ChevronRight size={13} />
                  )}
                  <span>{sec.label}</span>
                  <span className="db-code-lines">{sec.lines} lines</span>
                </button>
                {openSection === sec.key && (
                  <textarea
                    className="db-code-editor"
                    value={fields[sec.key]}
                    onChange={set(sec.key)}
                    spellCheck={false}
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
