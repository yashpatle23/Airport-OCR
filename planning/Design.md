# Design — Airport-OCR

> The visual system for Airport-OCR's user-facing surfaces: the offline web UI
> (`webui.py`) and the shareable HTML report (`report.render_html`). Tokens below
> are the **actual values in the code** — keep them in sync when either changes.

> Constraint from [`Rules.md`](Rules.md) §2.5: **no external assets** — no web
> fonts, CDNs, icon packs, or scripts. Everything is inline CSS + system fonts +
> inline SVG. Design decisions must respect offline, zero-dependency rendering.

---

## 1. Design principles

1. **Trust is visible.** Blockers, conflicts, and "review-only" states are
   surfaced with color and copy — never hidden.
2. **Non-operational is unmistakable.** A persistent banner/badge marks every
   surface as research-only.
3. **Calm, data-dense, legible.** A neutral slate palette lets the *data* and its
   *status colors* carry meaning.
4. **Self-contained.** One file opens anywhere, offline, safely.
5. **Accessible.** Sufficient contrast, tabular numerals for figures, semantic
   tables.

## 2. Color palette (as implemented)

### Neutrals (slate)
| Token | Hex | Use |
|-------|-----|-----|
| Ink / header bg | `#0f172a` | Header background, primary value text |
| Slate-600 | `#64748b` | Labels, secondary text, muted keys |
| Slate-400 | `#94a3b8` | Subtitles, `.dim`, CRS/source captions |
| Header text | `#e2e8f0` | Text on dark header |
| Border | `#e2e8f0` | Card border, grid gaps, section dividers |
| Divider | `#eef2f7` | Table row borders |
| Surface | `#ffffff` | Tiles / card body |
| Chip bg | `#f1f5f9` | Taxiway chips |
| AI panel bg | `#f8fafc` | Narrative/summary panel |
| Body text | `#1e293b` | Paragraph copy |

### Status / semantic
| Token | Hex | Meaning |
|-------|-----|---------|
| Success (validation OK) | `#0f766e` | `PASS_WITH_EXPECTED_BLOCKERS` badge |
| Success text | `#ecfeff` | Text on success badge |
| Error | `#b91c1c` | Real validation failure badge |
| Warn text | `#b45309` | Inline warnings (e.g. elevation conflict note) |
| Non-operational badge bg | `#78350f` | `.b-op` badge background |
| Non-operational badge text | `#fde68a` | `.b-op` badge text |
| Footer bg (caveat) | `#fff7ed` | Non-operational footer |
| Footer text | `#9a3412` | Caveat copy |
| Footer border | `#fed7aa` | Footer top border |

> The **elevation-conflict** highlight uses the warn tokens to draw the eye to
> the preserved-but-unresolved `3003 ft` vs `3001 ft` value.

### Domain color reference (data, not UI theme)
These come from the chart's own marking legend and are **documented, not
restyled**: holding marking `#000000`, stop-bar lights `#ff0000`, no-entry
lights `#bf00ff`. See [`Architecture.md`](Architecture.md) §6.

## 3. Typography

- **Font stack (system, no web fonts):**
  `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`
- **Scale (as used):**
  - ICAO title: `28px` / `700`, letter-spacing `.02em`
  - Tile value: `18px` / `600`
  - Body/AI copy: `13.5px`, line-height `1.55`
  - Table: `13px`
  - Labels/keys: `11px` uppercase, letter-spacing `.06em`
  - Chips / captions: `12px`
  - Badges: `11px` / `600`
- **Numerals:** `font-variant-numeric: tabular-nums` on all figures (tiles,
  tables, chips) so columns of numbers align.

## 4. Layout & components

- **Card shell:** `max-width: 920px`, `border: 1px solid #e2e8f0`,
  `border-radius: 14px`, soft shadow `0 1px 4px rgba(0,0,0,.06)`, `overflow:hidden`.
- **Header (`.aoc-h`):** dark slate bar — ICAO + airport name, badge row
  (non-operational + validation), source caption.
- **Badges (`.aoc-badges span`):** pill shape (`border-radius:999px`),
  `3px 10px` padding.
- **Fact grid (`.aoc-grid`):** 4-column grid, 1px gaps over a slate background
  (creates hairline separators); each `.tile` is a white cell with an uppercase
  key (`.k`) + prominent value (`.v`) + optional `.warn` note.
- **Sections (`.aoc-sec`):** `16px 22px` padding, top border divider, uppercase
  `h3` section labels.
- **Runway table:** full-width, collapsed borders, right-aligned numeric columns
  (`td.num`).
- **Taxiway chips (`.chip`):** pill tags on a light surface for the 43 designators.
- **AI/narrative panel (`.aoc-ai`):** distinct light background; renders the
  paraphrase (or deterministic summary) as escaped text.
- **Footer (`.aoc-foot`):** warm amber caveat bar — the non-operational /
  not-for-navigation notice.

## 5. Iconography & imagery

- **No icon fonts / image assets.** Status is conveyed by color + text.
- **Map:** inline **SVG** only (ARP + runway thresholds), no tiles or network.

## 6. Accessibility & safety notes

- Maintain contrast: dark ink text on light surfaces; light text on dark header
  and colored badges.
- Never rely on color alone — pair every status color with a text label
  (e.g. "NON-OPERATIONAL", "conflict: 3003 vs 3001 ft").
- All dynamic values are HTML-escaped ([`Rules.md`](Rules.md) §4.2); styling must
  never require enabling scripts or inline event handlers.

## 7. Change policy

If you restyle a surface, update **both** the code and this doc's token tables in
the same change, and keep the palette within the existing slate + semantic set
unless there's a documented reason (record it in [`Memory.md`](Memory.md)).
