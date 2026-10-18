# Results: basal-omni-1.0-mini on Quick, Draw!

- test drawings: **1020** (255 words × 4), each judged against **all 255 words at once**
- top-1 accuracy: **28.0%** (95% CI 25.4%–30.9%); random guessing: 0.4%
- word in the top 5: **45.3%**
- calibration error (ECE): **0.059**; mean stated confidence 25.4%
- generated tokens: **0**; median input 1872 tokens, median time 8.0 s (fp16, PLE on CPU, Apple M1 Pro)

| model confidence | share of drawings | accuracy in this group |
|---|---|---|
| ≥ 50% | 19.0% (194) | 66.5% |
| ≥ 80% | 7.2% (73) | 75.3% |
| ≥ 90% | 3.6% (37) | 75.7% |

| confidence bin | drawings | mean confidence | accuracy |
|---|---|---|---|
| 0%–10% | 465 | 4.5% | 7.1% |
| 10%–20% | 130 | 14.8% | 26.9% |
| 20%–30% | 103 | 24.8% | 35.0% |
| 30%–40% | 69 | 34.3% | 36.2% |
| 40%–50% | 59 | 44.7% | 47.5% |
| 50%–60% | 40 | 54.9% | 50.0% |
| 60%–70% | 47 | 65.5% | 70.2% |
| 70%–80% | 34 | 74.9% | 61.8% |
| 80%–90% | 36 | 84.9% | 75.0% |
| 90%–100% | 37 | 93.4% | 75.7% |

Most common mistakes (truth → model's answer): barn → house (4), ocean → line (4), panda → mouse (4), scorpion → mouse (4), shark → fish (4), spoon → mouse (4), stop sign → cello (4), television → cooler (4), tent → house (4), aircraft carrier → airplane (3)
