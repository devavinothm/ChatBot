# Project Requirement

## Original request
Make a web-based chatbot using Python that responds to questions related to
enterprise policy documents.

## Decisions made

- **LLM backend**: Anthropic Claude API (`claude-sonnet-5`), via `ANTHROPIC_API_KEY`.
- **Web framework**: Flask, serving a REST API plus a plain HTML/CSS/JS frontend.
- **Document ingestion**: both a local `documents/` folder (drop files + reindex)
  and in-browser upload.
- **Retrieval approach**: local sentence-transformer embeddings
  (`all-MiniLM-L6-v2`) with cosine-similarity search over chunked document
  text, persisted in a local ChromaDB collection (`data/chroma/`).
- **Supported document types**: PDF, DOCX, TXT, Markdown.

See [README.md](README.md) for setup/run instructions and project structure,
and [TECHNICAL_SPEC.md](TECHNICAL_SPEC.md) for the detailed architecture,
data flow, and API reference.

## Functional Requirements

The application is organized into four bot tiers, each surfaced as a tab in
the UI: **Information Bot** (Information Escort), **Guidance Bot** (Guidance
Guru), **Solution Bot** (Solution Mate), and **Utility Bot** (Utility
Minion).

### 6.1 Information Bot — Functional Requirements

| ID | Requirement | Description | Priority |
|---|---|---|---|
| FR-IB-01 | Domain Q&A | The bot shall answer user questions covering what, why, who, when, and how, using content from its assigned knowledge domain. | Must Have |
| FR-IB-02 | Source Grounding | The bot shall ground answers in approved content sources and avoid fabricating information outside its knowledge domain. | Must Have |
| FR-IB-03 | Conversational Follow-up | The bot shall support follow-up/clarifying questions within the same conversation without losing context. | Must Have |
| FR-IB-04 | Unknown Query Handling | The bot shall recognize when a query falls outside its knowledge domain and respond accordingly rather than guessing. | Must Have |
| FR-IB-05 | Escalation Trigger | The bot shall detect when a user's query is actually a progress/goal question or an ambiguous reasoning question, and offer to route it to a Guidance or Solution bot. | Should Have |
| FR-IB-06 | Content Freshness | The bot's answers shall reflect the latest version of the source content, with a defined refresh/sync cadence. | Should Have |

### 6.2 Guidance Bot — Functional Requirements

| ID | Requirement | Description | Priority |
|---|---|---|---|
| FR-GB-01 | Target State Definition | The system shall allow a target state/goal (e.g., KPI, milestone, completion criteria) to be defined for a user or account. | Must Have |
| FR-GB-02 | Current State Assessment | The bot shall retrieve or infer the user's current state relevant to the defined goal. | Must Have |
| FR-GB-03 | Progress Comparison | The bot shall compare current state to target state and communicate progress in clear, understandable terms (e.g., percentage, milestone, gap). | Must Have |
| FR-GB-04 | "Are We There Yet" Query | The bot shall directly answer whether the goal has been achieved, is on track, or is at risk, when asked. | Must Have |
| FR-GB-05 | Continuous Guidance | The bot shall proactively provide guidance/nudges as the user's state changes, not only when explicitly asked. | Should Have |
| FR-GB-06 | Goal Achievement Notification | The bot shall notify the user (or relevant stakeholder) when the target state has been achieved. | Should Have |
| FR-GB-07 | Escalation to Solution Bot | When the user asks a causal/ambiguous question about why progress has stalled, the bot shall offer to route to a Solution bot. | Should Have |
| FR-GB-08 | Inherit Information Bot Capability | The bot shall retain the ability to answer general SME questions (what/why/who/when/how) related to its domain. | Must Have |

### 6.3 Solution Bot — Functional Requirements

| ID | Requirement | Description | Priority |
|---|---|---|---|
| FR-SB-01 | Ambiguous Query Interpretation | The bot shall interpret broad or ambiguous user goals (e.g., "What should I do to achieve X?") and decompose them into answerable sub-questions. | Must Have |
| FR-SB-02 | Data Identification | The bot shall identify which available data sources/metrics are relevant to answering the query. | Must Have |
| FR-SB-03 | Reasoning & Analysis | The bot shall analyze the identified data and apply a reasoning process to arrive at a conclusion or recommendation. | Must Have |
| FR-SB-04 | Actionable Recommendation | The bot shall produce a specific, actionable recommendation in response to the user's goal or problem statement (e.g., what to address to move a metric by X%). | Must Have |
| FR-SB-05 | Explainability | The bot shall present the reasoning/evidence behind its recommendation in a way the user can review and understand. | Must Have |
| FR-SB-06 | Confidence Indication | The bot shall indicate its confidence level or the limitations of its analysis when data is incomplete or uncertain. | Should Have |
| FR-SB-07 | Scenario/What-if Handling | The bot shall support what-if style questions (e.g., "If I want to move the needle by X%, what do I have to address?"). | Should Have |
| FR-SB-08 | Inherit Guidance & Information Capability | The bot shall retain the ability to perform state-vs-target comparisons and SME Q&A relevant to its domain. | Must Have |
| FR-SB-09 | Human Escalation | The bot shall escalate to a human expert when the query exceeds its reasoning confidence or requires an authorized decision. | Must Have |

### 6.4 Utility Bot — Functional Requirements

| ID | Requirement | Description | Priority |
|---|---|---|---|
| FR-UB-01 | Product/Content Text Generation | The bot shall generate draft product descriptions, titles, and marketing/campaign copy based on seller-provided inputs (e.g., product attributes, category, tone/style preference). | Must Have |
| FR-UB-02 | Editable Draft Output | The bot shall present generated text as an editable draft that the seller can accept, edit, or regenerate before publishing. | Must Have |
| FR-UB-03 | Multi-Language Text Generation | The bot shall support generating text in the platform's supported regional languages, consistent with Gimbll's multi-language rollout. | Should Have |
| FR-UB-04 | Automatic Image Enhancement | The bot shall automatically enhance uploaded product images (e.g., background cleanup, lighting/color correction, cropping/straightening) to a catalog-ready standard. | Must Have |
| FR-UB-05 | Image Generation by Dimension/Format | The bot shall generate product or campaign images in multiple dimensions/aspect ratios on request (e.g., square catalog thumbnail, portrait story format, landscape banner) from a source image or text prompt. | Must Have |
| FR-UB-06 | Before/After Preview | The bot shall let the seller preview enhanced or generated images against the original before replacing or publishing it. | Should Have |
| FR-UB-07 | Batch Processing | The bot shall support enhancing or generating images/text for multiple catalog items in a single batch request. | Could Have |
| FR-UB-08 | Brand & Compliance Consistency | Generated text and images shall respect seller-defined brand guidelines and avoid prohibited claims or content categories. | Should Have |
| FR-UB-09 | Reusable Across Bot Tiers | Other bot tiers (e.g., Guidance bots guiding store setup, Solution bots recommending catalog improvements) shall be able to invoke the Utility bot to produce the content/media needed to complete a recommended action. | Should Have |
