---
version: alpha
name: "ClaimShield Nexus"
description: "A dense, evidence-first investigation workspace styled as a calm digital case file."
colors:
  primary: "#2446c2"
  paper: "#e8ecf1"
  surface: "#ffffff"
  ink: "#0e1c33"
  muted: "#4f5d72"
  accent: "#2446c2"
  highlight: "#ffe14d"
  danger: "#b42318"
  success: "#146c3a"
  shared-link: "#2446c2"
  referral-link: "#c2570c"
  owner-link: "#7a3fb0"
  agent-link: "#0f766e"
typography:
  display:
    fontFamily: "Bricolage Grotesque, Segoe UI, system-ui, sans-serif"
  sans:
    fontFamily: "Public Sans, Segoe UI, system-ui, -apple-system, sans-serif"
rounded:
  DEFAULT: "0.5rem"
  sm: "0.25rem"
  lg: "0.875rem"
spacing:
  page-inline: "2rem"
  section-gap: "1rem"
components:
  card: { }
  button: { }
  table: { }
  network-graph: { }
---

# ClaimShield Nexus Design System

## Overview

### Creative North Star

A digital investigator's case file: navy ink, cool paper, precise evidence annotations, and restrained highlighter marks. The interface should feel auditable and operational rather than promotional.

### Product context and register

- **Audience and primary job:** US SIU investigators and India State Anti-Fraud Unit investigators triage synthetic leads, inspect evidence, and record human decisions.
- **Target markets and evidence:** US and India, established by the repository's region-specific datasets, API contract, and queue language.
- **Locales and language policy:** English UI. Region-specific vocabulary, rupee/dollar formatting, and hospital/provider terminology are owned by `frontend/src/region.js` and backend region helpers.
- **Usage scene:** desktop-first, information-dense investigation work with tablet and phone fallbacks.
- **Register:** product application throughout.
- **Memorable signature:** evidence relationships use a stable four-color graph language; highlighter yellow is reserved for “look here” moments.
- **Restraint:** read-only evidence panels remain compact, textual, and comparable; no decorative dashboard graphics.
- **Anti-references:** consumer-fintech gradients, gamified risk scores, and red “guilty” verdict styling, because the product produces leads for human review.
- **Token ownership/runtime mapping:** the existing runtime variables in `frontend/src/styles.css` remain canonical. This file mirrors accepted values; components consume those variables directly.

## Colors

Cool paper and white surfaces carry the case-file identity. Navy is the primary text and app-bar color; blue is the interactive/evidence accent. Yellow is scarce emphasis. Red, amber, gray, and green preserve danger, review, neutral, and verified semantics. Network blue/orange/purple/teal always mean shared members, referrals, ownership, and agents respectively; color is accompanied by text or line style.

## Typography

Bricolage Grotesque is reserved for page and card hierarchy. Public Sans is the working face for prose, controls, tables, and evidence. System fallbacks preserve legibility when web fonts are unavailable. Technical values use tabular numerals where comparisons matter; labels use sentence case.

## Layout

The application uses a maximum-width centered workspace with a sticky 60px app bar and 32px desktop page inset. Case pages use a two-column evidence grid that collapses to one column below 1000px. Cards use a 16px gap; tables retain semantic markup and horizontal overflow when required. Async states reserve enough height to avoid moving adjacent evidence.

## Elevation & Depth

White cards sit on cool paper with a one-pixel, low-opacity shadow. Tonal surfaces and rules establish hierarchy inside cards. A semantic inset rule may identify a special evidence panel; stronger shadows, glass blur, and floating decoration are excluded.

## Shapes

Controls and small annotations use 4px corners, cards 8px, and hero containers 14px. Relationship graphs use circles for providers and compact rectangles for administrative entities. Dividers are thin and cool gray.

## Components

### Foundational visual states

Interactive controls expose hover, visible focus, active, disabled, and busy states. Green means evidence survives or is verified, never that fraud is proven. Initial loading uses a stable, geometry-matched app skeleton; reduced-motion mode disables shimmer and transitions.

### Buttons and actions

Primary blue is reserved for the main safe action. Neutral outlined buttons handle secondary work. Dangerous intent remains separate from routine actions. Labels use explicit verbs and busy text stays within stable button geometry.

### Navigation and data display

The dark app bar owns global navigation and region selection. Tables use native semantics and textual headers. Risk and robustness values always include explanatory copy, component parts, and limitations rather than relying on a single color or number.

### Forms and overlays

Fields use visible labels and inline recovery text. Product dialogs and shared notices replace browser-native dialogs. Read-only disclosures use semantic `details`/`summary` when supplemental methodology would otherwise dominate the investigation view.

### Iconography

Simple inline SVG and geometric marks are preferred. Icons supplement visible labels and never carry an investigation action alone.

### Motion

Short 100–300ms transitions clarify focus and graph tracing. Reduced-motion mode removes animation and smooth scrolling. Routine evidence panels do not animate for decoration.

### Content and data visualization

Copy is cautious, direct, and investigative. The interface says “lead,” “support,” and “recommend review,” never “proven fraud.” Graph legends and robustness tables provide textual alternatives to every visual encoding.

## Do's and Don'ts

- **Do:** keep topology, corroborating evidence, and investigator conclusions visibly distinct.
- **Do:** reuse the shared card, table, status, loading, region, and relationship-color vocabulary.
- **Don't:** change case scores or verdict language from a read-only explanatory panel.
- **Don't:** use visual drama, color alone, or an unexplained composite score to imply guilt.
