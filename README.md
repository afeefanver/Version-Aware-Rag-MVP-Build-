# Version-Aware RAG: Project Roadmap

**Goal:** A RAG system where every chunk carries a document version and effective date, retrieval prefers the current version, answers state which version they're based on, and contradictions between versions are flagged.

**Resume line:** *Built a version-aware RAG system with temporal metadata filtering and conflict detection, ensuring answers come from the current version of each document.*

---

## 1. Time Estimate

| Scope | Part-time (2-3 hrs/day) | Full-time |
|---|---|---|
| **MVP** (ingest, version filter, versioned answers) | ~2 weeks | ~4-5 days |
| **Full project** (+ conflict detection, eval, UI, docs) | **3-4 weeks** | **~2 weeks** |

Total effort: roughly **60-80 hours**. The MVP is already resume-worthy, so ship it first and add conflict detection and evaluation on top.

---

## 2. Suggested Tech Stack

Pick something simple you can run locally.

- **Language:** Python 3.11+
- **Parsing:** `pypdf` / `python-docx` / `unstructured` (or plain Markdown/text to start)
- **Embeddings:** `bge-small-en-v1.5` or `all-MiniLM-L6-v2` (sentence-transformers, CPU-friendly)
- **Vector store:** Qdrant (best payload filtering) or Postgres + pgvector (simplest to also hold the version registry)
- **Keyword search (optional hybrid):** `rank_bm25`, or Postgres full-text
- **Reranker (optional):** `bge-reranker-base`
- **LLM:** Claude API, or Ollama (Llama / Qwen) for fully local
- **Conflict detection:** NLI cross-encoder (`cross-encoder/nli-deberta-v3-base`) + LLM judge
- **API/UI:** FastAPI + Streamlit
- **Eval:** pytest + a small custom harness (optionally RAGAS)

---

## 3. Core Data Model

Design this first, because everything depends on it.

**Document-level (version registry table)**

| Field | Example |
|---|---|
| `doc_id` | `leave-policy` (stable across versions) |
| `version` | `v3` or `3.0` |
| `effective_from` | `2026-04-01` |
| `effective_to` | `null` (open) or `2026-03-31` |
| `status` | `current` / `superseded` / `draft` |
| `supersedes` | `v2` |
| `source_path` | `policies/leave_v3.pdf` |

**Chunk-level payload (stored with each vector)**

`chunk_id, doc_id, version, effective_from, effective_to, is_current, section_title, page, text, content_hash`

Rule: `is_current` and `effective_to` are **derived** from the registry, not hand-set on chunks, so publishing a new version updates one place.

---

## 4. Phases

### Phase 0: Setup and scope (Day 1)
- [ ] Create repo, virtualenv, `pyproject.toml`, folder structure (`ingest/`, `retrieval/`, `generation/`, `conflicts/`, `eval/`, `app/`, `data/`)
- [ ] Decide domain for the demo corpus (HR policies, IT security policy, refund/terms policy, or product docs)
- [ ] Write a 1-page spec: what questions the system must answer, and what "wrong" looks like (quoting an old version)
- [ ] Pick stack from section 2 and stick to it

**Done when:** repo runs `hello world` and spec is written.

### Phase 1: Build the corpus (Days 2-4)
You need multi-version documents, and they're hard to find, so create them.
- [ ] Write 5-8 documents, each with 2-4 versions (e.g., leave policy v1/v2/v3, expense policy, data-retention policy)
- [ ] Plant realistic **changes** between versions: changed numbers (15 days to 20 days), removed clauses, new clauses, renamed terms
- [ ] Plant a few **intentional contradictions** (two versions both marked current, or a v2 clause that conflicts with a v3 clause)
- [ ] Add 2-3 real public examples (privacy policy archive versions, open-source docs at two release versions)
- [ ] Create `data/manifest.json` listing every file with its `doc_id`, `version`, `effective_from`

**Done when:** you have ~20-30 files plus a manifest, and you know the "true" change list for each doc pair (this becomes your eval ground truth).

### Phase 2: Ingestion pipeline (Days 4-7)
- [ ] Parsers for PDF/DOCX/MD into clean text with section headings preserved
- [ ] Chunking: heading-aware, ~300-500 tokens, small overlap; keep `section_title` on each chunk
- [ ] Version registry (SQLite or Postgres): load from the manifest
- [ ] Attach metadata to every chunk (section 3), embed, upsert into the vector store
- [ ] Compute `content_hash` per chunk so re-ingesting an unchanged doc is a no-op
- [ ] Function `publish_version(doc_id, version, effective_from)` that marks the older version `superseded` and sets its `effective_to`

**Done when:** ingesting the full corpus gives correct metadata on every chunk, and publishing a new version automatically flips the old one to superseded.

### Phase 3: Version-aware retrieval (Days 7-11)
- [ ] Baseline: plain similarity search with no filters (keep it to prove the problem in your eval)
- [ ] Default mode: filter `is_current = true`
- [ ] **As-of mode:** user supplies a date ("what was the policy on 2025-06-01?"), filter `effective_from <= date AND (effective_to IS NULL OR effective_to >= date)`
- [ ] **Explicit version mode:** "according to v2..."
- [ ] **Compare mode:** retrieve the matching chunks from two versions of the same doc
- [ ] Query parsing: detect dates/version mentions in the question (regex first, LLM later)
- [ ] Fallback: if the current version has no relevant chunk, search superseded versions and mark the result clearly as outdated
- [ ] Optional: hybrid (BM25 + dense) and reranking

**Done when:** the same question returns v3 chunks by default, v1 chunks when asked "as of 2024", and the baseline demonstrably returns mixed versions.

### Phase 4: Versioned answer generation (Days 11-14)
- [ ] Prompt template that receives chunks **with** their version and effective date in the context
- [ ] Structured output: `answer`, `based_on: [{doc_id, version, effective_from}]`, `citations`, `warnings`
- [ ] Force the answer to open with its basis, e.g. *"Based on Leave Policy v3 (effective 2026-04-01): ..."*
- [ ] If an answer used a superseded version, say so explicitly
- [ ] "I don't know" behavior when nothing relevant is retrieved

**Done when:** every answer names the version and date it relies on, and citations map to real chunks.

### Phase 5: Conflict detection (Days 14-20)
This is the most distinctive part of the project. Build it in layers.

1. **Pairing:** align chunks across versions of the same `doc_id` (same section title first, then embedding similarity above a threshold)
2. **Cheap screen:** flag pairs where text differs materially (hash + similarity below threshold)
3. **NLI check:** run a cross-encoder on (old, new); `contradiction` label means candidate conflict
4. **LLM judge:** for candidates, ask "Do these conflict on a factual or policy point? Return JSON: `conflict: bool, type, explanation, which_is_newer`"
5. **Conflict types** to classify: *value change* (15 to 20 days), *removed clause*, *added clause*, *scope change*
6. **Cross-document conflicts within the same effective period** (two current docs disagreeing)
7. **At query time:** if retrieved chunks include a flagged conflicting pair, attach a warning to the answer
8. **Offline job:** a `detect_conflicts` command that scans the whole corpus and writes a `conflicts.json` report

**Done when:** the planted contradictions from Phase 1 are caught, and the report lists each with an explanation.

### Phase 6: Evaluation (Days 20-24)
Numbers on your resume are far stronger than adjectives.
- [ ] Build a test set of ~50-100 questions: answer-in-current, answer-changed-between-versions, as-of-date questions, conflict-trigger questions
- [ ] Metrics:
  - **Current-version accuracy:** % of default queries answered from the current version
  - **Stale-answer rate:** baseline RAG vs. your system (the headline number)
  - **Version attribution accuracy:** answer names the correct version
  - **As-of-date accuracy**
  - **Conflict detection precision / recall / F1** against your planted ground truth
  - Latency per query
- [ ] Ablations: no filter vs. filter, with and without the NLI step
- [ ] Put results in a table in the README

**Done when:** you can state something like "stale answers dropped from X% to Y%, conflict detection F1 of Z."

### Phase 7: API and UI (Days 24-27)
- [ ] FastAPI endpoints: `POST /ingest`, `POST /query`, `GET /conflicts`, `GET /documents/{doc_id}/versions`
- [ ] Streamlit app: question box, optional "as-of date" picker, answer with a version badge, expandable sources, conflict warning banner
- [ ] A side-by-side "Baseline RAG vs. Version-aware RAG" toggle (great for demos)

### Phase 8: Polish and ship (Days 27-30)
- [ ] README: problem, architecture diagram, data model, how to run, eval results, limitations
- [ ] Docker Compose (app + vector DB)
- [ ] Unit tests for registry logic, date filtering, and conflict classification
- [ ] 2-3 minute demo video or GIF
- [ ] Push to GitHub, write a LinkedIn post, update the resume line with your real metrics

---

## 5. Suggested Repo Structure

```
version-aware-rag/
├── data/               # corpus + manifest.json
├── ingest/             # parsers, chunker, registry, publish_version
├── retrieval/          # filters, as-of logic, hybrid, rerank
├── generation/         # prompts, structured answer
├── conflicts/          # pairing, NLI, LLM judge, report
├── eval/               # test set, metrics, ablations
├── app/                # FastAPI + Streamlit
├── tests/
├── docker-compose.yml
└── README.md
```

---

## 6. Common Pitfalls

- **Skipping the baseline.** Without "plain RAG gets it wrong," your improvement has nothing to be measured against.
- **Setting `is_current` by hand on chunks.** Derive it from the registry.
- **Chunking that splits clauses.** Conflicts become undetectable if a rule is cut in half.
- **Relying only on the LLM for conflict detection.** Use pairing and NLI to narrow candidates first (cheaper and more explainable).
- **Using real company docs with no ground truth.** Synthetic docs with known changes let you measure precision and recall.
- **Treating "latest" as "effective."** A v4 with a future effective date is not current yet. Filter on dates, not just version numbers.

---

## 7. Stretch Goals (only after the core is done)

- Detect version/date automatically from document headers and filenames
- Change-summary feature: "What changed between v2 and v3?"
- Audit log of which version every answer used
- Per-user access filters combined with version filters
- Scheduled re-ingestion and expiry alerts for documents past their review date

---

## 8. Weekly Checkpoints

| Week | Target |
|---|---|
| 1 | Phases 0-2: corpus built, ingestion and registry working |
| 2 | Phases 3-4: **MVP**: version-filtered retrieval with versioned answers |
| 3 | Phase 5: conflict detection working on planted contradictions |
| 4 | Phases 6-8: evaluation, UI, README, demo |

Start with Phase 0 and Phase 1 this week. The corpus and ground-truth change list will make every later phase easier to test.
