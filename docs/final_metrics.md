# Final Metrics Summary

This document captures all metrics tracked in the OrchardVision experiment harness, their measured values from evaluation runs, and inferences for project utility.

---

## Identity & Tracking Metrics

| Metric | Metric Value | Inference |
|--------|-------------|-----------|
| **IDF1** (Identity F1) | Mock: 70.9% \| ByteTrack: 69.0% \| TAPNext: 0.88% | Primary identity consistency metric. Mock tracker (identity primitives) outperforms ByteTrack slightly; TAPNext fails without trained embedder. Use for tracker selection. |
| **HOTA** (Higher Order Tracking Accuracy) | Mock: 75.9% \| ByteTrack: 73.0% \| TAPNext: 0.89% | Balances detection, association, and localization. Mock leads; ByteTrack competitive. HOTA > IDF1 suggests detection quality is strong relative to association. |
| **ID Switches** (count) | Mock: 1.0 \| ByteTrack: 5.7 \| TAPNext: 3.2 | Lower is better. Mock maintains identities through occlusion best. ByteTrack switches ~6× more often; problematic for long-term fruit counting. |
| **Track Fragmentation** | Not directly reported in results; tracked in ExperimentMetrics | Inferred from ID switches and count error. High fragmentation on V2 (short tracks, fast camera motion). Correlates with camera motion ablation. |
| **Identity Recovery Rate** | Not directly reported; tracked in ExperimentMetrics | Re-ID stage recovers lost identities (e.g., track 11 in V4, similarity 0.934 > 0.6 threshold). Untrained embedder makes threshold un-tunable (similarities 0.90–0.96). Critical for occlusion handling. |

---

## Counting Accuracy Metrics

| Metric | Metric Value | Inference |
|--------|-------------|-----------|
| **Count MAE** (Mean Absolute Error) | V1: 1 \| V2: 11 \| V3: 3 (ByteTrack) | Absolute fruit count error. V2 is outlier (157% error) due to short clip (141 frames), fast camera motion (median shift 4.5px), and track fragmentation. |
| **Count MAPE** (Mean Absolute Percentage Error) | V1: 11.1% \| V2: 157.1% \| V3: 21.4% (ByteTrack) | Percentage error. V2 inflates mean. Median MAPE across videos ≈ 21%. Acceptable for V1/V3; V2 needs camera-motion handling. |
| **Predicted Track Count** | V1: 10 \| V2: 18 \| V3: 17 (ByteTrack, gt: 9, 7, 14) | ByteTrack overcounts on V2 (2.5× ground truth). Mock tracker would likely reduce overcount via identity primitives. |

---

## Camera Motion Metrics

| Metric | Metric Value | Inference |
|--------|-------------|-----------|
| **Camera Motion Compensation Effect on IDF1** | Off: 68.9% \| On: 69.2% | Negligible improvement (+0.3%). Compensation adds drift error (accumulated frame-shift estimation). Not recommended for handheld clips with few px/frame motion. |
| **Camera Motion Compensation Effect on HOTA** | Off: 73.0% \| On: 73.6% | Marginal gain (+0.6%). Same drift issue as IDF1. |
| **Camera Motion Compensation Effect on ID Switches** | Off: 5.7 \| On: 17.3 | **Worsens** identity switches 3×. Compensation destabilizes tracks by propagating estimation error. Disable for current hardware. |
| **Median Frame Shift (V1/V2/V3)** | V1: 0.3px \| V2: 4.5px (95th: 44.7px) \| V3: ~0.3px | V2 is the hard case: motion is an order of magnitude larger. Compensation only helps if motion estimation is accurate (not currently). |

---

## Re-Identification Metrics

| Metric | Metric Value | Inference |
|--------|-------------|-----------|
| **ReID Threshold Sensitivity (Identities Found)** | 0.90: 13.3 \| 0.93: 14.3 \| 0.95: 15.7 \| 0.97: 17.0 | Raising threshold increases identity count (fragments one fruit into many). Default 0.6 is far below operating range—untrained embedder produces similarities 0.90–0.96. |
| **ReID Threshold Sensitivity (Accepted Re-IDs)** | 0.90: 3.7 \| 0.93: 2.7 \| 0.95: 1.3 \| 0.97: 0.0 | Higher threshold rejects valid re-identifications. Trade-off: fewer merges but more fragments. Requires trained embedder for calibrated range. |
| **ReID Similarity Range (Untrained ResNet-18)** | 0.90 – 0.96 | Too narrow for threshold tuning. All candidates exceed default 0.6. Priority: train/fine-tune identity embedder. |

---

## Detection Metrics

| Metric | Metric Value | Inference |
|--------|-------------|-----------|
| **Detector mAP<sub>50-95</sub> (YOLOv8n)** | 0.827 (best epoch 49) | Best of 4 runs. Highest mAP, fastest (33.6 ms), smallest weights (6.2 MB). Default for deployment. |
| **Detector mAP<sub>50-95</sub> (YOLOv8m)** | 0.808 (ep 10), 0.789 (ep 73) | Larger model, slower (83.5 ms), larger weights (52 MB). No accuracy gain over YOLOv8n. |
| **Detector mAP<sub>50-95</sub> (YOLOv8x)** | 0.788 (ep 40) | Slowest (173 ms), largest (546 MB). Lowest mAP. Not viable for real-time. |
| **Detection Confidence Threshold Sweep** | 0.25–0.75: identity metrics stable; track count collapses | Threshold trades recall for continuity. Identity metrics (IDF1, HOTA) insensitive in this range because tracker discards low-confidence detections internally. |

---

## Runtime Performance Metrics

| Metric | Metric Value | Inference |
|--------|-------------|-----------|
| **Mean Processing Time (ms/frame)** | Mock: 25.8 \| ByteTrack: 25.3 \| TAPNext: 600.0 | Mock/ByteTrack meet real-time (>30 FPS). TAPNext is 24× slower (1.67 FPS)—only viable with optimized checkpoint. |
| **95th Percentile (ms/frame)** | Mock: 28.8 \| ByteTrack: 28.6 \| TAPNext: 700.0 | Consistent latency for mock/ByteTrack. TAPNext has high variance. |
| **Throughput (FPS)** | Mock: 39.0 \| ByteTrack: 39.5 \| TAPNext: 1.67 | Both mock and ByteTrack exceed video FPS (24–30). Headroom for higher-res input or heavier detector. |

---

## Ground Truth Quality Metrics

| Metric | Metric Value | Inference |
|--------|-------------|-----------|
| **Raw IDs (Full-rate Association)** | V1: 61 \| V2: 44 \| V3: 43 | Overcounts due to occlusion/false positives creating short tracks. |
| **Retained IDs (Min 50 frames)** | V1: 9 \| V2: 7 \| V3: 14 | Matches expected max concurrency (9–12). Minimum-length rule filters transient tracks effectively. |
| **Dropped IDs** | V1: 52 \| V2: 37 \| V3: 29 | High drop rate confirms occlusion/fragmentation challenge. |
| **Max Concurrent Fruit** | V1: 10 \| V2: 10 \| V3: 12 | Upper bound for counting accuracy. |

---

## Experiment Harness Metrics

| Metric | Metric Value | Inference |
|--------|-------------|-----------|
| **Experiment Status** | running / completed / failed | Tracked per experiment. Enables async execution and result retrieval. |
| **Tracker Type** | mock / bytetrack | Mock = identity primitives (upper bound); ByteTrack = production baseline. |
| **Scenario** | orchard video (V1/V2/V3) | Fixed scenarios for reproducibility. |
| **Frame Count** | Configurable (default 310) | Trade-off: more frames = better statistics, longer runtime. |

---

## Summary: Actionable Metrics for Project Decisions

| Decision | Metric to Watch | Target |
|----------|----------------|--------|
| **Tracker selection** | IDF1, ID Switches | Mock > ByteTrack for identity continuity; ByteTrack for speed parity |
| **Camera motion handling** | ID Switches (compensation on/off) | Disable compensation (switches 5.7 → 17.3) |
| **Re-ID embedder training** | ReID similarity spread | Target: 0.2–0.8 calibrated range (currently 0.90–0.96) |
| **Detector choice** | mAP<sub>50-95</sub>, latency | YOLOv8n (0.827, 33.6 ms) |
| **Counting reliability** | Count MAPE (per video) | <25% on typical clips; investigate V2-style motion |
| **Real-time viability** | Mean frame time, 95th %ile | <33 ms (30 FPS) for mock/ByteTrack ✓ |

---

*Generated from: `packages/types/src/evaluation.ts`, `docs/report/ch8_results.tex`, and experiment harness code.*