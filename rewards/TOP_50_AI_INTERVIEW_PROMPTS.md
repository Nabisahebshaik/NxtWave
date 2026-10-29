# 🏆 Top 50 AI Placement Interview Prompts & System Design Guide
**Exclusively Curated for NxtWave AI Workshop Students**  
*Unlock Milestone: 3 Successful Peer Referrals*

---

## 📌 Executive Summary
Recruiters hiring for GenAI, Data Science, and Machine Learning engineering roles in 2026 are looking for **applied system design**, **LLM orchestration**, and **prompt engineering resilience**. This guide provides 50 curated prompts, technical interview questions, and architectural solutions asked in top product firms.

---

## SECTION 1: LLM System Design & Architecture (Questions 1 - 15)

### Q1: Design a Low-Latency RAG (Retrieval-Augmented Generation) Pipeline for 100,000 Documents.
* **The Challenge:** How to maintain sub-500ms P99 latency while searching through dense technical documentation.
* **Architecture:**
  - Chunking strategy: Semantic chunking (300-500 tokens with 10% overlap).
  - Embedding: Fast vectorization (`text-embedding-3-small`).
  - Storage & Indexing: HNSW (Hierarchical Navigable Small World) index in Qdrant or Milvus.
  - Hybrid Search: Reciprocal Rank Fusion (RRF) combining BM25 keyword search + Vector cosine similarity.
  - Re-ranking: Cross-encoder re-ranking top-20 results down to top-5 before context injection.

### Q2: How do you prevent Prompt Injection and Jailbreaks in user-facing LLM agents?
* **Defense-in-depth Strategy:**
  1. Input sanitization: Strip delimiter tokens and format as JSON/Markdown strictly.
  2. Dual-LLM Guardrail: Lightweight classifier model (e.g. Llama-Guard) scans incoming input for adversarial prompts.
  3. Structured Output: Enforce schema validation (Pydantic / Function Calling) so raw text execution is prohibited.
  4. Token Canary Injection: Insert dynamic secret UUID tokens in system instructions to detect system prompt exfiltration.

### Q3: How do you handle LLM Hallucinations in high-stakes financial/medical queries?
* **Answer Blueprint:**
  - Implement RAG with strict ground truth citation requirements.
  - Use chain-of-thought verification (Self-Consistency sampling with temperature > 0.4, taking majority consensus).
  - Strict system prompt constraint: *"If the provided context does not contain the answer, reply strictly with 'Insufficient context' and do not extrapolate."*

*(Questions 4 - 15 covered in full cheat sheet)*

---

## SECTION 2: Advanced Prompt Engineering Patterns (Questions 16 - 35)

### Pattern 1: Chain-of-Density (CoD) Summarization
* **Prompt:**
  ```text
  You will generate increasingly concise, entity-dense summaries of the following article.
  Repeat the following 2 steps 5 times:
  Step 1: Identify 1-3 informative entities from the article missing in the previous summary.
  Step 2: Write a new, denser summary of identical length that covers every previous entity plus the newly identified missing entities.
  ```

### Pattern 2: Few-Shot In-Context Learning with Negative Constraints
* **Prompt Template:**
  ```text
  Task: Classify customer intent into: [BUG_REPORT, FEATURE_REQUEST, BILLING].
  Negative Constraint: NEVER guess. If message has ambiguity, output INTENT: UNKNOWN.
  Examples:
  Input: "The page stays white after I click pay." -> Output: BUG_REPORT
  Input: "Can you add dark mode?" -> Output: FEATURE_REQUEST
  Input: "What does your software do?" -> Output: UNKNOWN
  ```

*(Patterns 3 - 20 covered in full cheat sheet)*

---

## SECTION 3: Live Coding & Python AI Implementation (Questions 36 - 50)

### Code Challenge 1: Write an Async Rate-Limiter for OpenAI API in Python
```python
import asyncio
import time

class TokenBucketRateLimiter:
    def __init__(self, rate: int, per: float):
        self.rate = rate
        self.per = per
        self.allowance = rate
        self.last_check = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            current = time.monotonic()
            time_passed = current - self.last_check
            self.last_check = current
            self.allowance += time_passed * (self.rate / self.per)
            if self.allowance > self.rate:
                self.allowance = self.rate
            if self.allowance < 1.0:
                sleep_time = (1.0 - self.allowance) * (self.per / self.rate)
                await asyncio.sleep(sleep_time)
                self.allowance = 0.0
            else:
                self.allowance -= 1.0
```

---

## 🎯 Verification
*Document Hash:* `SHA256-NXT-REWARD-PROMPTS-V1`  
*Issued by:* NxtWave AI Workshop Growth & Curriculum Team
