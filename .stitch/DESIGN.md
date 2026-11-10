---
name: ValorAI
colors:
  surface: '#f5f5f1'
  surface-dim: '#e2e3dd'
  surface-bright: '#ffffff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#fafaf7'
  surface-container: '#ecede7'
  surface-container-high: '#e9eae4'
  surface-container-highest: '#e2e3dd'
  on-surface: '#242830'
  on-surface-variant: '#4b515c'
  inverse-surface: '#242830'
  inverse-on-surface: '#eef0ec'
  outline: '#676d78'
  outline-variant: '#c9ccc4'
  surface-tint: '#7e9f8c'
  primary: '#3c6a53'
  on-primary: '#ffffff'
  primary-container: '#edf3ef'
  on-primary-container: '#335c47'
  inverse-primary: '#a9cbb6'
  secondary: '#7e9f8c'
  on-secondary: '#242830'
  secondary-container: '#edf3ef'
  on-secondary-container: '#335c47'
  tertiary: '#242830'
  on-tertiary: '#eef0ec'
  tertiary-container: '#2e333c'
  on-tertiary-container: '#b9bec6'
  error: '#a23b2c'
  on-error: '#ffffff'
  error-container: '#fbefec'
  on-error-container: '#8a3124'
  primary-fixed: '#edf3ef'
  primary-fixed-dim: '#cbdcd1'
  on-primary-fixed: '#2f5742'
  on-primary-fixed-variant: '#335c47'
  secondary-fixed: '#e2e3dd'
  secondary-fixed-dim: '#c9ccc4'
  on-secondary-fixed: '#242830'
  on-secondary-fixed-variant: '#4b515c'
  tertiary-fixed: '#eef0ec'
  tertiary-fixed-dim: '#b9bec6'
  on-tertiary-fixed: '#242830'
  on-tertiary-fixed-variant: '#2e333c'
  background: '#f5f5f1'
  on-background: '#242830'
  surface-variant: '#e2e3dd'
typography:
  display-lg:
    fontFamily: Instrument Sans
    fontSize: 36px
    fontWeight: '600'
    lineHeight: 41px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Instrument Sans
    fontSize: 19px
    fontWeight: '600'
    lineHeight: 22px
    letterSpacing: -0.02em
  body-base:
    fontFamily: Instrument Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: '0'
  body-bold:
    fontFamily: Instrument Sans
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: '0'
  label-caps:
    fontFamily: Instrument Sans
    fontSize: 12px
    fontWeight: '550'
    lineHeight: 16px
    letterSpacing: '0'
  stat-lg:
    fontFamily: Instrument Sans
    fontSize: 30px
    fontWeight: '600'
    lineHeight: 34px
    letterSpacing: -0.02em
rounded:
  sm: 0.375rem
  DEFAULT: 0.625rem
  md: 0.625rem
  lg: 1rem
  xl: 1.25rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  gutter: 16px
  margin-mobile: 16px
  margin-desktop: 32px
---

# Design System: ValorAI

## 1. Visual Theme & Atmosphere

ValorAI feels like a quiet ledger opened on warm paper. The page is **Warm Paper** (`#f5f5f1`), never stark white and never a cool blue-gray. Graphite type sits on that paper with the same color as the wordmark, and a single forest green carries every commitment the person makes: continue, confirm, save. Sage, the color of the modular V, is the softer brand presence — completed steps, selected goals, success notes — while the forest green does the pressing. The mood is clarity and balance: a personal-finance prototype that explains where each real goes, without neon charts or a trading-desk density.

The interface is calm and task-shaped. Registration is one column of fields beside a dark illustrative panel; the dashboard is a short stack of white cards. Corners are gently rounded, borders are hairlines in warm stone, and shadows appear only when a dialog lifts off the page. Motion is a short fade and a six-pixel rise between steps, and it stops entirely when the person prefers reduced motion. Icons are Lucide outlines, small and quiet, the same weight as the type. Copy is Brazilian Portuguese, set in one variable sans so the product reads as a single voice.

## 2. Color Palette & Roles

The token sheet in `src/styles/global.css` is explicit: sage `#7E9F8C` and graphite `#242830` come from the product mark (“Ritmo e equilíbrio”). Everything else is a role built from those two hues. Near-duplicate warm grays (`#fafaf7`, `#ecede7`, `#e9eae4`, `#eceee8`) are one stone-wash family used for notes and hovers, not separate brands.

### Primary Foundation

- **Warm Paper** (`#f5f5f1`) — page background, theme color, and the ground behind the confirmation code. Slightly warm, like unbleached paper.
- **Card White** (`#ffffff`) — form controls, cards, dialogs, and the prototype pill. The only pure white surface.
- **Stone Line** (`#e2e3dd`) — hairline borders on cards, the footer, and inactive progress tracks.
- **Stone Edge** (`#c9ccc4`) — the stronger border on inputs, secondary buttons, and unselected goal cards.
- **Graphite** (`#242830`) — wordmark, body text, the dark product preview, and the filled portion of the income split. The darkest neutral in the system.

### Accent & Interactive

- **Forest** (`#3c6a53`) — primary buttons, the current progress step, focus rings, selected goal borders, and checkbox accent. This is the action color.
- **Forest Pressed** (`#2f5742`) — primary button hover.
- **Forest Ink** (`#335c47`) — text links, positive balances, goal icons, and success alert copy. Dark enough to read on paper and on sage tint.
- **Sage** (`#7e9f8c`) — the logo symbol, completed progress, and the dashed demo-inbox border. Brand color, not the main button.
- **Sage Mist** (`#edf3ef`) — selected goal cards, success alerts, guide icons, and the inbox button.
- **Sage Line** (`#cbdcd1`) — success alert borders and the resting underline of text links.
- **Focus Halo** (`#3c6a53` at 15%) — a three-pixel ring around a focused field, paired with a Forest border.

### Typography & Text Hierarchy

- **Graphite** (`#242830`) — headings, labels, primary figures, and selected progress labels.
- **Graphite Soft** (`#4b515c`) — supporting paragraphs, secondary button ghost text, checkbox copy, and figure captions.
- **Graphite Mist** (`#676d78`) — hints, footer, progress idle labels, placeholders’ neighbors, and fine print.
- **Placeholder Gray** (`#8f949c`) — input placeholders only.
- On the dark preview, type shifts to **Preview Mist** (`#eef0ec`) for body, **Preview White** (`#ffffff`) for titles, and **Preview Mute** (`#b9bec6` / `#a5abb4` / `#9aa0aa`) for captions. Treat those three mutes as one cool-gray family.

### Functional States

- **Terracotta** (`#a23b2c`) — errors, invalid field borders, negative balances, and the deactivate action. Warm red, not alarm scarlet.
- **Terracotta Pressed** (`#8a3124`) — danger button hover.
- **Terracotta Wash** (`#fbefec`) with border `#f0d3cc` — error alerts. The danger-link underline is `#e7b9b0`.
- **Sage Mist + Forest Ink** — success alerts. Success reuses the brand greens; it does not introduce a separate emerald.
- **Reserved Amber** (`#8a5a12` on `#fdf4e3`) is declared on the token sheet and unused by components. The illustrative spending-limit panel uses its own warm gold instead: panel `#3a3426`, edge `#5b4d2e`, bar and icon `#e2b35c`, copy `#f1e6cf`. Use that gold only inside the dark preview, for a limit that has been reached.

Income on the dark ledger is **Sage Light** (`#a9cbb6`). Category chips there are **Sage Text** (`#d6e4db`) on **Deep Sage** (`#3b4a43`).

## 3. Typography Rules

One family does all the reading: **Instrument Sans Variable**, with `system-ui, sans-serif` behind it. It is a contemporary humanist sans — open, slightly warm, calm at text sizes and firm at display sizes. The product mark itself is custom vector lettering, not this font. Confirmation codes switch to a monospace stack (`ui-monospace`, Cascadia Mono, Consolas) so six digits stay unmistakable.

### Hierarchy & Weights

| Role | Size | Weight | Tracking | Line height | Where it appears |
|:---|:---|:---|:---|:---|:---|
| Page title | `clamp(28px, 3vw, 36px)`; dashboard up to 40px | 600 | −0.02em | 1.15 | “Seus dados”, “Olá, …” |
| Preview title | `clamp(26px, 2.6vw, 34px)` | 600 | −0.02em | 1.15 | Dark panel headline |
| Stat | `clamp(22px, 2.4vw, 30px)`; 22px on small screens | 600 | −0.02em | tight | Income, expenses, remainder. Tabular figures. |
| Card title | 19px | 600 | −0.02em | 1.15 | Card and dialog headings |
| Dialog subhead | 17px | 600 | −0.02em | 1.15 | Rare section titles inside dialogs |
| Body | 16px | 400 | 0 | 1.5 | Paragraphs under titles. Lesson text opens to 1.7. |
| Button | 15px | 600 | 0 | inherits | Primary, secondary, and ghost actions |
| Field label | 14px | 600 | 0 | normal | Labels above inputs |
| Meta | 13–14px | 400; tags at 550 | 0 | normal | Hints, footer, progress, errors |
| Prototype pill | 12px | 550 | 0 | normal | “Protótipo” chip. Sentence case, not small caps. |
| OTP | 28px field, 36px in the inbox | 600 in the inbox | 0.4em / 0.3em | centered | Six-digit codes |

Headings use `text-wrap: balance`. Currency and countdowns use tabular numbers. There is no uppercase label style and no second display family. Weight 550 is the quiet emphasis between regular and semibold, used on the prototype tag and a few ledger labels.

### Spacing Principles

Body line-height is a comfortable 1.5; display type tightens to 1.15 with a slight negative track so titles feel set, not stretched. Space after a page title is 10px before the supporting sentence, then 28px before the form. Field labels sit 6px above the control. Related fields share a 16px horizontal and 20px vertical gap. Sections inside a card separate with 16–24px, often with a hairline when the topic changes (goal line, danger zone). Codes earn extra letter-spacing because they are read digit by digit; everything else stays at zero.

## 4. Component Stylings

### Buttons

Buttons are 10px rounded rectangles, 44px tall, with 18px of horizontal padding and a 15px semibold label. An 18px Lucide icon may sit in an 8px gap. The press feedback is a 150ms background or border change, nothing else.

- **Primary** — Forest fill, white label. Hover darkens to Forest Pressed. This is the single forward action in a form, and it grows to fill the remaining row.
- **Secondary** — Card White fill, Stone Edge border, Graphite label. Hover darkens the border to Graphite Mist. Used for “Sair” and “Ajustar perfil”.
- **Ghost** — transparent, Graphite Soft label, tighter 12px padding. Hover lays a warm stone wash (`#e9eae4`). Used for “Voltar” and “Sobre o protótipo”.
- **Danger** — Terracotta fill, white label. Hover uses Terracotta Pressed. Reserved for confirming deactivation.
- **Small** — 36px tall, 12px padding, 14px type. Header actions.
- **Text link** — Forest Ink, semibold, underline in Sage Line that turns solid on hover. The deactivate link swaps the color to Terracotta.
- Disabled buttons drop to 55% opacity and lose the pointer. Focus uses the global 2px Forest outline, 3px outside the control.

### Cards & Dialogs

Cards are Card White, 16px corners, a 1px Stone Line, and 24px of padding (20px below 640px). They do not float; the paper behind them is enough separation. A card header pairs a 19px title with a 14px Graphite Mist subtitle, and an optional small secondary button on the right.

Dialogs share the card shape, cap at 520px wide, and are the only elevated surface: a soft Graphite shadow (`0 24px 64px` at 20% opacity) over a Graphite scrim at 60%. The header is separated by a hairline; the body is 15px Graphite Soft with 16px between blocks. Clicking the scrim or the close icon dismisses it.

The dark **product preview** is the exception: Graphite fill, 20px corners, 40px padding, sticky near the top of the registration view. Inside it, the sample ledger and the limit callout are darker nested panels with 14px corners. That panel is an illustration of the future product, not a chrome pattern for forms.

### Navigation

There is no app sidebar. A 72px header (64px on small screens) holds the wordmark at 118px wide (100px on small screens), a pill that says “Protótipo”, and small secondary or ghost actions aligned to the end. The pill is a full capsule: 12px type, Card White, Stone Line, 2px by 10px padding. The footer is a hairline-topped bar with the company mark and a text link. A skip link rests off-screen and drops into view on focus.

Registration progress is four columns. Each step is a 4px track — Stone Line when waiting, Sage when complete, Forest when current — with a 13px label underneath. The current label turns Graphite and semibold.

### Inputs & Forms

Fields are a label stacked 6px above a 48px control. Controls are Card White, 10px corners, 1px Stone Edge, 14px of horizontal padding, 16px type. Hover darkens the border to Graphite Mist. Focus replaces the border with Forest and adds the Focus Halo; the browser outline is suppressed on the control because the halo does that job. Errors replace the border with Terracotta and show a 13px Terracotta message with a small alert icon.

Money fields prefix a Graphite Mist “R$” and indent the value. Password fields keep a 40px icon button inside the trailing edge. Checkboxes are 18px with a Forest accent. Goal choices are two-column cards: 14px padding, Stone Edge, and on selection a Sage Mist fill plus a double Forest border (1px border and a 1px inset ring). Password rules are a wrapping row of 13px items; a met rule turns Forest Ink and fills its 16px circle with Forest.

The one-time code field is wider in spirit than in chrome: 64px tall, 28px monospace, 0.4em tracking, centered. The demo inbox is a full-width dashed Sage button on Sage Mist, turning solid on hover.

Alerts are 10px rounded, 14px type, tinted wash plus a 1px border: Terracotta for errors, Sage for success. A quieter note uses the stone wash `#ecede7` with no colored border, for prototype caveats.

### Ledger, Limits & Profile Figures

The sample ledger lists a title, a tabular amount (Sage Light when money comes in), and a small category chip with 6px corners. The limit block is the warm brown/gold panel described above: a 6px track, a full gold bar, and a sentence that the alert informs and does not block payment.

On the dashboard, three figures sit in a row separated by Graphite Mist operators. The remainder is Forest Ink, or Terracotta when it is negative. Under them, a 12px split bar fills with Graphite (or Terracotta when overspent) against Sage Mist. Guide rows are full-bleed inside the card, hairline-separated, with a 40px Sage Mist icon tile at 10px radius. The account card ends in a danger zone: a hairline, then a Terracotta text link.

## 5. Layout Principles

### Grid & Structure

The shell is a column, at most **1280px**, centered. Registration is a two-column grid: the form takes the wider share, the preview about 0.92 of that, with a **48px** gap. The form itself never exceeds **480px** and is centered in its column. Fields are two columns at a 16px gap, with full-width rows for name, email, passwords, and consent. The dashboard is about **1.7fr + 1fr** with a **20px** gap: profile and guides on the left, roadmap and account on the right.

Breakpoints are desktop-first: **1080px** stacks the dashboard and tightens the auth gap; **900px** hides the preview and collapses auth to one column; **640px** narrows the page, stacks fields, stacks goal cards, and turns the three figures into a vertical list.

### Whitespace Strategy

The rhythm is a **4px** unit, with a few in-between steps (6, 10, 14, 18) where type and controls need air that an 8px step would overshoot. Page padding is **32px** on the sides and **16px** below 640px. Header content is vertically centered in 72px. Major blocks — title group, form actions, card sections — step by **24–32px**. Cards gap by **20px**. Nothing is packed; nothing is luxurious. The empty state page is a 480px column with 72px of space above the title.

### Alignment & Visual Balance

Titles and body are left-aligned. Form switch lines (“Já tem conta?”) are centered under the form. Amounts in the ledger and definition lists are right-aligned and tabular. The dark preview balances the long form so the first screen does not feel like a bare questionnaire; when it hides, the form stands alone, still capped at 480px. Visual weight sits in Forest buttons and Graphite titles. Sage is a wash and a completed track, not a large field of color. The wordmark is the only decorative graphic.

### Responsive Behavior & Touch

Primary controls are **44px** tall; inputs are **48px**; icon buttons are **40px**; the small header button is **36px**. The one-time code control is **64px**, sized for a thumb and for six widely tracked digits. Below 640px the operators between figures disappear, each figure becomes a label-and-value row, and the footer stacks. The preview is removed rather than squeezed. Hover styles are additive; focus-visible rings remain the keyboard path. A fixed skip link is the first focus stop.

## 6. Design System Notes for Stitch Generation

### Language to Use

Warm paper, graphite ink, sage brand, forest actions. Quiet personal finance. Hairline stone borders, soft 10px and 16px corners, almost no shadow. One humanist sans. Brazilian Portuguese interface copy. Clarity and balance — a ledger, not a trading terminal. Say “paper”, “sage”, “forest”, and “graphite”. Avoid glass, neon, gradients, and heavy elevation.

### Color References

- Warm Paper `#f5f5f1` — page
- Card White `#ffffff` — cards, fields, dialogs
- Graphite `#242830` — text and the dark preview
- Graphite Soft `#4b515c` — secondary text
- Graphite Mist `#676d78` — hints
- Stone Line `#e2e3dd` — card borders
- Stone Edge `#c9ccc4` — input borders
- Forest `#3c6a53` — primary buttons and focus
- Forest Ink `#335c47` — links and positive money
- Sage `#7e9f8c` — logo and completed steps
- Sage Mist `#edf3ef` — selected and success washes
- Terracotta `#a23b2c` — errors and destructive actions
- Terracotta Wash `#fbefec` — error alerts
- Limit Gold `#e2b35c` on `#3a3426` — only inside the dark preview, when a limit is reached

### Component Prompts

- “A registration step on warm paper. Left side: a 480px form with a four-step progress track (sage for done, forest for the current step), a 36px semibold graphite title, 16px soft-graphite support text, and two-column 48px fields with 10px corners and stone borders. One forest primary button, 44px tall, labeled in white with a small arrow. Right side: a graphite panel with 20px corners showing a sample monthly ledger and a warm gold limit alert.”
- “A client home on the same paper. A greeting in 40px semibold graphite. A white card with a 16px corner and a hairline border holds three tabular figures — income, fixed expenses, remainder in forest — above a thin split bar. A second card lists short reading guides with sage-tinted icon tiles.”
- “A confirmation dialog: white, 16px corners, soft graphite shadow, a hairline header, and a terracotta full-width button for a destructive confirm. Body copy is 15px graphite-soft.”

### Incremental Iteration

Keep Forest for the one forward action and Sage for selection, progress, and success. Do not fill large areas with Sage; it is a mist and a mark. Keep the page on Warm Paper and reserve Graphite fills for the illustrative preview. When adding transactions, imports, or receipt capture, reuse the ledger row, the category chip, and the limit bar rather than inventing a new chrome. Alerts inform; they do not become blocking banners. Stay with Instrument Sans, 600 for titles, and tabular numbers for money. On small screens, drop the preview and stack the figures before shrinking type below 16px in fields.
