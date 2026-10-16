# Listing Search Service

A full-stack property search and ranking application built for the **Software Engineer Coding Assessment**. It ingests property listings from multiple MLS providers and exposes an interactive search experience with relevance scoring, deliberate error handling, cross-MLS deduplication, and pagination.

---

## 1. Quick Start

### 🌐 Live Interactive Demo
Try the deployed application directly in your browser:
**[https://behlv10.github.io/brilio_assessment/](https://behlv10.github.io/brilio_assessment/)**

---

### Option A: Run Both Services Locally with One Command
```bash
./run.sh
```
- **Backend API**: [http://127.0.0.1:8000](http://127.0.0.1:8000) (Interactive Swagger docs at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs))
- **Frontend UI**: [http://localhost:5173](http://localhost:5173)

---

### Option B: Run Services Manually

#### Backend (Python / FastAPI)
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### Frontend (React + TypeScript / Vite)
```bash
cd frontend
npm install
npm run dev
```

---

## 2. Running Tests

The test suite covers core business logic, scoring formulas, tie-breaking, deduplication, edge cases (no matches, tied scores, pagination boundaries), and deliberate error handling:

```bash
cd backend
./venv/bin/pytest -v
```
*(All 25 unit and API integration tests pass).*

---

## 3. Relevance Scoring Approach

The assessment requires ranking listings using `targetBudget` and `recency`:
> *"A targetBudget value, used along with recency to rank results by relevance — you design the scoring; we're more interested in whether your approach is sensible and clearly explained than in one 'correct' formula."*

### A. Budget Relevance Score ($S_{\text{budget}}$)
Home buyers typically consider listings within a narrow band around their target budget, with steep drops in relevance as listings diverge significantly:
- Let the relative budget deviation be $\Delta = \frac{|\text{price} - \text{targetBudget}|}{\text{targetBudget}}$.
- We model budget affinity using an **exponential decay function** (inspired by Elasticsearch numeric decay scoring):
  $$S_{\text{budget}} = \exp(-3.0 \cdot \Delta) \times 100$$
  - Exact match ($\Delta = 0$): $100.0$
  - $4.4\%$ off ($+\$20\text{k}$ on $\$450\text{k}$): $87.5$
  - $10\%$ deviation: $74.0$
  - $25\%$ deviation: $47.2$
- If `targetBudget` is omitted, budget scoring is bypassed.

### B. Recency Score ($S_{\text{recency}}$)
Fresher listings represent new market inventory:
- Let $\text{daysAgo} = \max(0, \text{refDate} - \text{listedDate})$.
- Uses a **30-day half-life decay function**:
  $$S_{\text{recency}} = \left(\frac{1}{1.0 + \frac{\text{daysAgo}}{30.0}}\right) \times 100$$
  - Listed today ($0$ days ago): $100.0$
  - Listed 6 days ago: $83.3$
  - Listed 30 days ago: $50.0$
  - Listed 60 days ago: $33.3$

### C. Status Penalty Multiplier ($M_{\text{status}}$)
Pending listings are already under contract and significantly less actionable for active homebuyers:
- $M_{\text{status}} = 1.0$ for `active`
- $M_{\text{status}} = 0.70$ for `pending` (30% relevance penalty)
- $M_{\text{status}} = 0.30$ for `sold` (70% relevance penalty)

### D. Composite Score & Deterministic Tie-Breaking
- **Base Score**:
  - With `targetBudget`: $S_{\text{base}} = 0.70 \times S_{\text{budget}} + 0.30 \times S_{\text{recency}}$
  - Without `targetBudget`: $S_{\text{base}} = S_{\text{recency}}$
- **Final Relevance Score**:
  $$\text{Relevance Score} = S_{\text{base}} \times M_{\text{status}}$$
- **Deterministic Tie-Breaking**:
  When scores match, listings are ordered deterministically by:
  1. `listedDate` descending (fresher first)
  2. `price` ascending (more affordable first)
  3. `id` ascending (lexicographical stability)

---

## 4. Status Filtering & Actionability

Users can filter by listing status:
- **All Statuses** (shows both active and pending listings, with pending listings receiving the 30% score penalty)
- **Active Only** (hides pending listings entirely)
- **Pending Only** (focuses exclusively on under-contract properties)

---

## 5. Cross-MLS Deduplication (Anticipated Interview Requirement)

### The Observation
MLS aggregators frequently receive overlapping listings for the identical physical property across different provider feeds. In the provided sample dataset:
- `A1` (MLS_A, `123 Main St, Apt 4B`) and `B7` (MLS_B, `123 Main Street, Unit 4B`)
- `A2` (MLS_A, `456 Oak Ave`) and `B8` (MLS_B, `456 Oak Avenue`)
- `A3` (MLS_A, `789 Pine Rd`) and `B9` (MLS_B, `789 Pine Rd`)
- `A5` (MLS_A, `55 Elm Ct`) and `B11` (MLS_B, `55 Elm Court`)

### The Implementation
1. **Entity Resolution Key**:
   - Normalized address: Standardizes street suffixes (`St` $\to$ `street`, `Ave` $\to$ `avenue`, `Ct` $\to$ `court`, `Apt` $\to$ `unit`) and removes punctuation.
   - Coordinate clustering: Groups coordinates rounded to 4 decimal places ($\approx 11\text{m}$ precision).
2. **Conflict Resolution**:
   - For clustered listings, the system prefers `active` status over `pending`/`sold`, followed by the highest relevance score / newest date.
   - Retained listing annotates `otherSources` (e.g. *"Also available on MLS_B"*).
3. **User Control**:
   - Included a toggle switch in the UI: **"Hide duplicates across MLS sources"** (`deduplicate=true|false`), allowing users (and the interviewer) to inspect both raw and deduplicated views.

---

## 6. Deliberate Input Validation & Error Handling

Rather than crashing or failing silently, the service validates search parameters and returns HTTP `400 Bad Request` with structured error messages:
- `minPrice > maxPrice`: e.g. `"minPrice ($600,000) cannot be greater than maxPrice ($400,000)"`
- `minPrice < 0` or `maxPrice < 0`: `"minPrice/maxPrice cannot be negative"`
- `minBedrooms < 0`: `"minBedrooms cannot be negative"`
- `targetBudget <= 0`: `"targetBudget must be greater than zero"`
- `pageSize <= 0` or `page < 1`: `"pageSize/page must be greater than or equal to 1"`
- In the React frontend, errors are caught and surfaced via a red alert banner with actionable feedback.

---

## 7. Architecture & Trade-offs

| Component | Choice | Trade-offs & Rationale |
| :--- | :--- | :--- |
| **Backend** | Python + FastAPI | Clean Pydantic schemas, built-in validation, async support, and interactive Swagger UI. Slower than Go for high throughput, but ideal for agile interview extensions and clean domain modeling. |
| **Storage** | In-Memory Model List | Optimal for sample datasets ($<10,000$ listings) and zero setup overhead. In production, this would be backed by PostgreSQL with PostGIS or Elasticsearch/OpenSearch. |
| **Frontend** | React + TypeScript (Vite) | Lightning-fast builds, strict type safety between backend schemas and UI, reactive state updates, and clean modular components. |
| **Keyword Search** | Substring Matching | Case-insensitive substring match against listing descriptions. Fast and zero-dependency; for millions of listings, inverted indices (BM25) would be preferred. |
