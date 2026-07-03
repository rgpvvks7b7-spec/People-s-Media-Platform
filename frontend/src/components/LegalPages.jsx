import React, { useEffect, useMemo, useRef } from "react";
import { getLegalPage, LEGAL_FOOTER_LINKS } from "../legal/index.js";
import {
  IUBENDA_POLICY_EMBED_PAGES,
  isIubendaPolicyEmbedConfigured,
  loadIubendaEmbedScript,
  reloadIubendaEmbeds,
} from "../lib/iubenda.js";
import { getLegalFooterNote, getLegalPageBadge, LEGAL_EFFECTIVE_DATE } from "../lib/legalStatus.js";

function stripDocumentHeader(markdown) {
  return markdown
    .replace(/^# [^\n]+\n+/m, "")
    .replace(/^\*\*Effective date:[^\n]+\n+/m, "")
    .replace(/^\*\*Last updated:[^\n]+\n+/m, "")
    .replace(/^>[^\n]+\n+\n+/m, "")
    .replace(/^---\n+/m, "");
}

function escapeHtml(value) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderInlineMarkdown(text) {
  let html = escapeHtml(text);
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_match, label, href) => {
    const safeHref = href.startsWith("/") || href.startsWith("mailto:") ? href : "#";
    return `<a href="${escapeHtml(safeHref)}">${label}</a>`;
  });
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  return html;
}

function isTableRow(line) {
  return line.trim().startsWith("|");
}

function isTableSeparator(line) {
  return /^\|\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$/.test(line.trim());
}

function parseTableRow(line) {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map(cell => cell.trim());
}

function renderMarkdown(markdown) {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const blocks = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];

    if (!line.trim()) {
      index += 1;
      continue;
    }

    if (line.startsWith("> ")) {
      const quoteLines = [];
      while (index < lines.length && lines[index].startsWith("> ")) {
        quoteLines.push(lines[index].slice(2));
        index += 1;
      }
      blocks.push(
        `<blockquote>${quoteLines.map(item => renderInlineMarkdown(item)).join("<br />")}</blockquote>`
      );
      continue;
    }

    if (line.startsWith("### ")) {
      blocks.push(`<h3>${renderInlineMarkdown(line.slice(4))}</h3>`);
      index += 1;
      continue;
    }

    if (line.startsWith("## ")) {
      blocks.push(`<h2>${renderInlineMarkdown(line.slice(3))}</h2>`);
      index += 1;
      continue;
    }

    if (line.startsWith("# ")) {
      blocks.push(`<h1>${renderInlineMarkdown(line.slice(2))}</h1>`);
      index += 1;
      continue;
    }

    if (line.trim() === "---") {
      blocks.push("<hr />");
      index += 1;
      continue;
    }

    if (isTableRow(line) && index + 1 < lines.length && isTableSeparator(lines[index + 1])) {
      const headers = parseTableRow(line);
      index += 2;
      const rows = [];
      while (index < lines.length && isTableRow(lines[index]) && !isTableSeparator(lines[index])) {
        rows.push(parseTableRow(lines[index]));
        index += 1;
      }
      const headHtml = headers.map(cell => `<th>${renderInlineMarkdown(cell)}</th>`).join("");
      const bodyHtml = rows
        .map(row => `<tr>${row.map(cell => `<td>${renderInlineMarkdown(cell)}</td>`).join("")}</tr>`)
        .join("");
      blocks.push(`<table><thead><tr>${headHtml}</tr></thead><tbody>${bodyHtml}</tbody></table>`);
      continue;
    }

    if (/^[-*]\s+/.test(line.trim())) {
      const items = [];
      while (index < lines.length && /^[-*]\s+/.test(lines[index].trim())) {
        items.push(lines[index].trim().replace(/^[-*]\s+/, ""));
        index += 1;
      }
      blocks.push(
        `<ul>${items.map(item => `<li>${renderInlineMarkdown(item)}</li>`).join("")}</ul>`
      );
      continue;
    }

    if (/^\d+\.\s+/.test(line.trim())) {
      const items = [];
      while (index < lines.length && /^\d+\.\s+/.test(lines[index].trim())) {
        items.push(lines[index].trim().replace(/^\d+\.\s+/, ""));
        index += 1;
      }
      blocks.push(
        `<ol>${items.map(item => `<li>${renderInlineMarkdown(item)}</li>`).join("")}</ol>`
      );
      continue;
    }

    const paragraphLines = [];
    while (
      index < lines.length &&
      lines[index].trim() &&
      !lines[index].startsWith("#") &&
      !lines[index].startsWith("> ") &&
      !isTableRow(lines[index]) &&
      lines[index].trim() !== "---" &&
      !/^[-*]\s+/.test(lines[index].trim()) &&
      !/^\d+\.\s+/.test(lines[index].trim())
    ) {
      paragraphLines.push(lines[index]);
      index += 1;
    }
    blocks.push(`<p>${renderInlineMarkdown(paragraphLines.join(" "))}</p>`);
  }

  return blocks.join("");
}

function IubendaPolicyEmbed({ pageId }) {
  const embedRef = useRef(null);
  const config = IUBENDA_POLICY_EMBED_PAGES[pageId];

  useEffect(() => {
    if (!config?.policyId || !embedRef.current) {
      return undefined;
    }

    let cancelled = false;

    loadIubendaEmbedScript()
      .then(() => {
        if (!cancelled) {
          reloadIubendaEmbeds();
        }
      })
      .catch(() => {
        if (!cancelled) {
          console.warn("IndieFund: Iubenda policy embed failed to load.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [config?.policyId, pageId]);

  if (!config?.policyId) {
    return null;
  }

  return (
    <div
      ref={embedRef}
      className="iubenda-embed iubenda-embed-noiframe legal-iubenda-embed"
      data-iub-link={config.link}
      data-iub-id={config.policyId}
      title={pageId === "privacy" ? "Privacy Policy" : "Cookie Policy"}
    />
  );
}

export function LegalFooter({ onNavigate }) {
  return (
    <footer className="legal-footer legal-footer--dock" aria-label="Legal">
      <nav className="legal-footer-nav">
        {LEGAL_FOOTER_LINKS.map(link => (
          <button key={link.page} type="button" className="legal-footer-link" onClick={() => onNavigate(link.page)}>
            {link.label}
          </button>
        ))}
      </nav>
      <p className="legal-footer-note muted">{getLegalFooterNote()}</p>
    </footer>
  );
}

export function LegalPageView({ pageId, onNavigate }) {
  const page = getLegalPage(pageId);
  const useIubendaEmbed = isIubendaPolicyEmbedConfigured(pageId);
  const fallbackHtml = useMemo(
    () => (page && !useIubendaEmbed ? renderMarkdown(stripDocumentHeader(page.content)) : ""),
    [page, useIubendaEmbed]
  );
  const supplementHtml = useMemo(
    () => (page?.supplement ? renderMarkdown(stripDocumentHeader(page.supplement)) : ""),
    [page]
  );

  if (!page) {
    return (
      <section className="legal-page">
        <h1>Page not found</h1>
        <p className="muted">That legal document could not be loaded.</p>
        <button type="button" className="secondary" onClick={() => onNavigate("listen")}>Back to Listen</button>
      </section>
    );
  }

  return (
    <article className="legal-page">
      <header className="legal-page-header">
        <p className="eyebrow">IndieFund Legal</p>
        {getLegalPageBadge() ? (
          <p className="legal-pre-release-badge">{getLegalPageBadge()}</p>
        ) : null}
        <h1>{page.title}</h1>
        <p className="muted">Effective {page.effectiveDate || LEGAL_EFFECTIVE_DATE}</p>
      </header>

      {useIubendaEmbed ? (
        <>
          <IubendaPolicyEmbed pageId={pageId} />
          {supplementHtml && (
            <section className="legal-page-supplement" aria-label="IndieFund platform-specific disclosures">
              <h2>IndieFund platform-specific disclosures</h2>
              <div
                className="legal-page-body"
                dangerouslySetInnerHTML={{ __html: supplementHtml }}
              />
            </section>
          )}
        </>
      ) : (
        <div
          className="legal-page-body"
          dangerouslySetInnerHTML={{ __html: fallbackHtml }}
        />
      )}

      <nav className="legal-page-links" aria-label="Related legal documents">
        <h2>Related documents</h2>
        <div className="legal-page-link-grid">
          {["privacy", "terms", "community-guidelines", "copyright", "artist-agreement", "fan-agreement", "cookies"]
            .filter(id => id !== pageId)
            .map(id => {
              const related = getLegalPage(id);
              if (!related) return null;
              return (
                <button key={id} type="button" className="secondary compact" onClick={() => onNavigate(id)}>
                  {related.title}
                </button>
              );
            })}
        </div>
      </nav>
    </article>
  );
}
