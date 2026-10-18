# Wyniki: basal-omni-1.0-mini na Quick, Draw!

- rysunków testowych: **1020** (255 haseł × 4), każdy oceniany spośród **255 haseł naraz**
- trafność top-1: **28,0%** (95% CI 25,4%–30,9%); losowe zgadywanie: 0,4%
- hasło w top-5: **45,3%**
- błąd kalibracji ECE: **0,059**; średnia deklarowana pewność 25,4%
- wygenerowane tokeny: **0**; mediana wejścia 1872 tokeny, mediana czasu 8,0 s (fp16, PLE na CPU, Apple M1 Pro)

| pewność modelu | odsetek rysunków | trafność w tej grupie |
|---|---|---|
| ≥ 50% | 19,0% (194) | 66,5% |
| ≥ 80% | 7,2% (73) | 75,3% |
| ≥ 90% | 3,6% (37) | 75,7% |

| przedział pewności | rysunków | śr. pewność | trafność |
|---|---|---|---|
| 0%–10% | 465 | 4,5% | 7,1% |
| 10%–20% | 130 | 14,8% | 26,9% |
| 20%–30% | 103 | 24,8% | 35,0% |
| 30%–40% | 69 | 34,3% | 36,2% |
| 40%–50% | 59 | 44,7% | 47,5% |
| 50%–60% | 40 | 54,9% | 50,0% |
| 60%–70% | 47 | 65,5% | 70,2% |
| 70%–80% | 34 | 74,9% | 61,8% |
| 80%–90% | 36 | 84,9% | 75,0% |
| 90%–100% | 37 | 93,4% | 75,7% |

Najczęstsze pomyłki (prawda → odpowiedź modelu): stodoła → dom (4), ocean → linia (4), panda → mysz (4), skorpion → mysz (4), rekin → ryba (4), łyżka → mysz (4), znak stop → wiolonczela (4), telewizor → lodówka turystyczna (4), namiot → dom (4), lotniskowiec → samolot (3)
