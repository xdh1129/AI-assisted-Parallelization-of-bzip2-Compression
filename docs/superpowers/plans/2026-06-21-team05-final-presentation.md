# Team 05 Final Presentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify a polished 13-slide English PowerPoint deck, with 11 Chinese-noted main slides and 2 backup slides, for a 12-minute presentation of `team05_final_paper.pdf`.

**Architecture:** Extract claims and figures from the final paper into a traceable source ledger, then generate an editable 16:9 deck with `@oai/artifact-tool` from one JavaScript ES module in an external scratch workspace. Export PPTX, PNG previews, layout JSON, and a montage; use rendered evidence and layout inspection to revise until every slide is legible and free of unintended overlap.

**Tech Stack:** Poppler (`pdftotext`, `pdftoppm`), Node.js ES modules, `@oai/artifact-tool`, PowerPoint `.pptx`, PNG/WebP rendering.

---

## File Map

- Read: `team05_final_paper.pdf` — primary research source.
- Read: `report/runtime_by_impl.png` — CPU runtime figure.
- Read: `report/throughput_by_impl.png` — CPU throughput figure.
- Read: `report/speedup_by_impl.png` — CPU speedup figure.
- Create: `/private/tmp/codex-presentations/manual-team05-20260621/team05-final-slides/tmp/source-notes.txt` — claim and asset provenance.
- Create: `/private/tmp/codex-presentations/manual-team05-20260621/team05-final-slides/tmp/slide-content.txt` — final on-slide copy and Chinese notes.
- Create: `/private/tmp/codex-presentations/manual-team05-20260621/team05-final-slides/tmp/build-deck.mjs` — deck generator.
- Create: `/private/tmp/codex-presentations/manual-team05-20260621/team05-final-slides/tmp/preview/` — slide PNGs and montage.
- Create: `/private/tmp/codex-presentations/manual-team05-20260621/team05-final-slides/tmp/layout/` — slide layout JSON.
- Create: `outputs/team05_final_presentation.pptx` — final deliverable.

### Task 1: Extract and verify the research claims

- [ ] **Step 1: Extract the final paper text and metadata**

Run:

```bash
mkdir -p /private/tmp/codex-presentations/manual-team05-20260621/team05-final-slides/tmp/{assets,preview,layout,qa}
pdfinfo team05_final_paper.pdf
pdftotext -layout team05_final_paper.pdf /private/tmp/codex-presentations/manual-team05-20260621/team05-final-slides/tmp/paper.txt
```

Expected: `pdfinfo` reports 9 pages and `paper.txt` contains Sections I–VII and the conclusion.

- [ ] **Step 2: Record the exact presentation claims**

Create `source-notes.txt` with these paper-backed facts:

```text
Primary source: team05_final_paper.pdf, 9 pages.
CPU workload: 1,082,774,528 bytes; 900 KB blocks; compression level 9; 3 repeats; threads 1,2,4,8,16,32.
Hardware: 2x Intel Xeon Platinum 8352V; 72 physical cores; 144 logical threads; 2 NUMA nodes.
Stage 1: OpenMP dynamic parallel-for, per-block allocation.
Stage 2: pthread reader/worker/writer pipeline with a shared bounded queue.
Stage 3: OpenMP fork/join plus a 16 MB thread-local bump arena.
Correctness: every tested configuration round-trips successfully.
32-thread runtime: Stage 1 3.06 s; Stage 2 3.49 s; Stage 3 3.03 s; lbzip2 3.14 s; pbzip2 3.79 s.
32-thread throughput: Stage 3 approximately 359 MB/s; pbzip2 approximately 286 MB/s.
Scaling: near-linear through 16 threads, with diminishing returns at 32 threads.
GPU extension: CPU fallback 85.80 s; CUDA blocksort 33.44 s; +BWT 29.95 s; +Huffman 27.04 s; final speedup approximately 3.17x.
Failed GPU MTF prototype: total 136.14 s; MTF phase 114.41 s.
Figures: report/runtime_by_impl.png, report/throughput_by_impl.png, report/speedup_by_impl.png.
```

- [ ] **Step 3: Cross-check numerical claims against the extracted paper**

Run:

```bash
rg -n "3\.03|3\.49|359|3\.17|85\.80|27\.04|136\.14|114\.41" /private/tmp/codex-presentations/manual-team05-20260621/team05-final-slides/tmp/paper.txt
```

Expected: every headline number appears in the extracted final paper.

### Task 2: Author slide copy and Chinese speaker notes

- [ ] **Step 1: Create the 13-slide content manifest**

Create `slide-content.txt` with this exact outline:

```text
01 Title — AI-Assisted Parallelization of bzip2 Compression
02 Why bzip2? — Independent blocks create parallel opportunity; ordered output, allocation, synchronization, and hardware limits create the real systems problem.
03 Research question — Does progressively richer AI guidance produce faster parallel code?
04 Three-stage workflow — Naive prompt; constraint-guided design; profiling-guided optimization.
05 What the AI built — Stage 1 OpenMP dynamic loop; Stage 2 pthread pipeline; Stage 3 OpenMP plus thread-local arena.
06 Experimental setup — 1.08 GB Canterbury; 900 KB blocks; level 9; 1–32 threads; 3 repeats; dual-socket Xeon.
07 Correctness first — All configurations round-trip successfully; parallelism does not alter correctness.
08 Headline result — Stage 3: 3.03 s and about 359 MB/s at 32 threads; workload-specific parity with lbzip2.
09 Scaling story — Near-linear to 16 threads; plateau at 32; Stage 2 loses ground at high concurrency.
10 Bottlenecks move — Profiling motivates arena allocation; selective CUDA reaches 3.17x; GPU MTF regresses.
11 Takeaways — Constraints do not guarantee speed; profiling is the highest-value feedback; AI can reach mature-tool performance on this workload.
12 Backup — Full CPU runtime table.
13 Backup — GPU configurations and bottleneck migration.
```

- [ ] **Step 2: Add concise Chinese speaker notes for slides 1–11**

Each note must state the slide's one-sentence purpose, explain the visual, and end with the transition to the next slide. Target 45–75 seconds for slides 2–10, 20–30 seconds for slides 1 and 11, totaling approximately 11 minutes 30 seconds to leave buffer.

- [ ] **Step 3: Review copy density**

Run:

```bash
awk 'length($0) > 180 { print NR ":" length($0) ":" $0 }' /private/tmp/codex-presentations/manual-team05-20260621/team05-final-slides/tmp/slide-content.txt
```

Expected: no on-slide content line exceeds 180 characters.

### Task 3: Build the PowerPoint deck

- [ ] **Step 1: Initialize the artifact-tool workspace**

Run:

```bash
node /Users/xdh/.codex/plugins/cache/openai-primary-runtime/presentations/26.619.11828/skills/presentations/container_tools/setup_artifact_tool_workspace.mjs --workspace /private/tmp/codex-presentations/manual-team05-20260621/team05-final-slides/tmp
mkdir -p outputs
```

Expected: `@oai/artifact-tool` resolves from the scratch workspace.

- [ ] **Step 2: Implement `build-deck.mjs`**

The module must:

```javascript
import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const ROOT = "/Users/xdh/Documents/大三下/平行/final/Final_Project";
const TMP = "/private/tmp/codex-presentations/manual-team05-20260621/team05-final-slides/tmp";
const OUT = path.join(ROOT, "outputs/team05_final_presentation.pptx");
const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });

const COLORS = {
  ink: "#101828", muted: "#667085", canvas: "#F7F9FC",
  purple: "#7C3AED", cyan: "#19A7CE", orange: "#F59E0B",
  line: "#DCE3EC", white: "#FFFFFF"
};

// Add 13 slides in the approved order. Use 56–72 px outer margins,
// 50+ px title-slide type, 35+ px slide titles, 24+ px callouts,
// and 16+ px body type. Embed the three repository plots once each,
// create the GPU comparison as a native editable bar chart, and attach
// Chinese notes to slides 1–11.

for (const [index, slide] of deck.slides.items.entries()) {
  const stem = `slide-${String(index + 1).padStart(2, "0")}`;
  const png = await deck.export({ slide, format: "png", scale: 2 });
  await fs.writeFile(path.join(TMP, "preview", `${stem}.png`), new Uint8Array(await png.arrayBuffer()));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(TMP, "layout", `${stem}.json`), await layout.text());
}

const montage = await deck.export({ format: "webp", montage: true, scale: 1 });
await fs.writeFile(path.join(TMP, "preview", "deck-montage.webp"), new Uint8Array(await montage.arrayBuffer()));
const pptx = await PresentationFile.exportPptx(deck);
await pptx.save(OUT);
```

The implementation fills the indicated 13 slides with the approved content; it must not introduce unrelated claims or web-sourced assets.

- [ ] **Step 3: Run the generator**

Run:

```bash
cd /private/tmp/codex-presentations/manual-team05-20260621/team05-final-slides/tmp
node build-deck.mjs
```

Expected: 13 PNGs, 13 layout JSON files, one montage, and `outputs/team05_final_presentation.pptx`.

### Task 4: Render and inspect every slide

- [ ] **Step 1: Inspect the montage and full-size PNGs**

Check all 13 slides for title wrapping, low contrast, cramped labels, inconsistent margins, plot readability, and unintended UI-card styling. Inspect slides 5, 8, 9, and 10 at full resolution because they contain the densest technical visuals.

- [ ] **Step 2: Scan layout exports for out-of-bounds objects**

Run:

```bash
rg -n '"left":\s*-|"top":\s*-|"width":\s*0|"height":\s*0' /private/tmp/codex-presentations/manual-team05-20260621/team05-final-slides/tmp/layout
```

Expected: no negative coordinates and no zero-sized visible objects.

- [ ] **Step 3: Fix all visual defects and regenerate**

Edit `build-deck.mjs`, rerun `node build-deck.mjs`, and replace the prior previews and PPTX. Repeat until the latest montage and full-size slides show no overlap, clipping, unexpected wrapping, or unreadable plot labels.

### Task 5: Final verification and delivery

- [ ] **Step 1: Verify artifact existence and size**

Run:

```bash
test -s outputs/team05_final_presentation.pptx
find /private/tmp/codex-presentations/manual-team05-20260621/team05-final-slides/tmp/preview -name 'slide-*.png' | wc -l
find /private/tmp/codex-presentations/manual-team05-20260621/team05-final-slides/tmp/layout -name 'slide-*.json' | wc -l
```

Expected: the PPTX is non-empty and both counts equal 13.

- [ ] **Step 2: Confirm the final numerical claims**

Inspect the deck snapshot or layout text and verify that `3.03`, `359`, `3.17`, `85.80`, and `27.04` are present, while no unresolved placeholder text is present.

- [ ] **Step 3: Deliver only the final PPTX**

Return `outputs/team05_final_presentation.pptx` as the final artifact. Do not deliver scratch files, previews, layout JSON, or the generator unless requested.
