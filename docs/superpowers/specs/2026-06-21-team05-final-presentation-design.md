# Team 05 Final Presentation Design

## Objective

Create an English PowerPoint deck for a 12-minute Chinese oral presentation of the research in `team05_final_paper.pdf`. The deck must communicate the research question, the three-stage AI-assisted parallelization workflow, the most important CPU results, the profiling insight, and the selective GPU extension.

## Audience and Delivery

- Audience: parallel-programming course presentation session.
- Slide language: English.
- Spoken language: Chinese.
- Main deck: 11 slides, paced for approximately 12 minutes.
- Backup: 2 appendix slides for detailed data and questions.
- Speaker notes: concise Chinese notes on every main slide.

## Story Structure

1. **Title** — project title and team.
2. **Why bzip2?** — block parallelism appears simple, but ordering, allocation, synchronization, I/O, and hardware limits complicate performance.
3. **Research Question** — test whether progressively richer AI guidance produces better parallel implementations.
4. **Three-Stage Workflow** — naive prompting, constraint-guided design, and profiling-guided optimization.
5. **What the AI Built** — compare the Stage 1 OpenMP fork/join loop, Stage 2 pthread reader/worker/writer pipeline, and Stage 3 OpenMP loop with thread-local arena allocation.
6. **Experimental Setup** — 1.08 GB Canterbury workload, 900 KB blocks, compression level 9, thread sweep from 1 to 32, three repeats, and dual-socket Xeon hardware.
7. **Correctness First** — all three AI-assisted versions and both references pass round-trip correctness at every tested thread count.
8. **Headline Result** — Stage 3 is the fastest AI-assisted implementation, reaching 3.03 seconds and about 359 MB/s at 32 threads, on par with or marginally faster than lbzip2 for this configuration.
9. **Scaling Story** — near-linear scaling through 16 threads and diminishing returns at 32 threads; Stage 2 weakens at the high end because its synchronization structure adds overhead.
10. **Bottlenecks Move** — CPU profiling motivates thread-local memory reuse; the GPU extension selectively accelerates block sort, BWT output, and Huffman table work to reach about 3.17x over the CPU fallback, while the MTF prototype demonstrates that not every phase maps well to GPU parallelism.
11. **Takeaways** — structural constraints do not guarantee speed, empirical profiling feedback is the most valuable guidance, and AI-assisted code can reach mature-tool performance on this workload.

Appendix slides contain the full CPU runtime table and the GPU phase/configuration breakdown.

## Visual Direction

Use the approved **Signal & Structure** direction:

- 16:9 bright canvas with generous margins.
- Dark charcoal text with purple, cyan, and orange accents.
- Purple identifies profiling-guided Stage 3, cyan identifies measurement/data, and orange highlights bottlenecks or cautionary findings.
- Large English headlines, minimal body copy, and high-contrast charts suitable for projection.
- Flat editorial compositions rather than dashboard-style card grids.
- Reuse the report's runtime, throughput, and speedup plots where they are legible; crop and annotate them for presentation use.
- Use one simplified native chart for the GPU extension so the 85.80 s to 27.04 s progression is immediately readable.

## Content Rules

- Prioritize claims directly supported by the final paper and repository figures.
- Present Stage 3 performance as workload-specific parity, not a universal claim that AI outperforms mature tools.
- Explain why Stage 2 underperforms without implying that explicit constraints are always harmful.
- Keep equations, detailed implementation listings, and the extended lbzip2 optimization study out of the main 12-minute narrative.
- Use the final paper as the primary source; no external web research is required.

## Verification

- Export a `.pptx` and render every slide to images.
- Inspect all slides for overlap, clipping, wrapping, contrast, and chart legibility.
- Confirm numerical claims against the final paper.
- Ensure slide titles are at least 35 pt, deck title at least 50 pt, body text at least 16 pt, and primary callouts at least 24 pt.
- Verify Chinese speaker notes are present for all 11 main slides.
