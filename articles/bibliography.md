# Bibliography — master index

Master reference list for the paper (supersedes `method_core_sources.md`, which is
kept as historical notes). BibTeX: [`references.bib`](references.bib) — **79 entries**
(~70 target, with margin to trim during writing). `[PDF]` = full text in `articles/`.
`⚠` = a field flagged `VERIFY` in the .bib (confirm before submission).

## Map: paper section → key references

| Paper section | Primary citations |
|---|---|
| §1 Intro — honest-benchmark gap | vanlaatum2025greenlightgym, morcego2023rlvsmpc, henderson2018matters |
| §1.5 Novelty (objective mismatch, I4C) | lambert2020objective, gevers1993, vandenhof1995closedloop, jacobiandmd2022 |
| §2 SINDy family | brunton2016sindy, brunton2016sindyc, kaiser2018sindympc, fasel2022ensemble, champion2020sr3, kaptanoglu2022pysindy |
| §2 STLSQ / threshold sensitivity (mechanism neighbours) | cortiella2021sparse, balanceguided2026, mangan2017modelselection |
| §3.1 EPI / economic MPC | ellis2014economic, katzin2020greenlight |
| §3.2 Simulator / crop | katzin2020greenlight, vanthoor2011tomato, vanthoor2011climate, vanhenten1994thesis |
| §3.3 Controllers (baselines) | schulman2017ppo, haarnoja2018sac, raffin2021sb3, ross2011dagger |
| §3.4 Pre-registration | pineau2021repro, henderson2018matters |
| §3.6 Statistics | wilcoxon1945, holm1979, efron1994bootstrap, demsar2006 |
| §4.3 Mechanism (open-loop ≠ closed-loop) | lambert2020objective, jacobiandmd2022, farahmand2017value, controlorientedsurvey2025 |
| §4.4 Oracle / horizon | mayne2000constrained, ellis2014economic, korda2018koopman |
| §4.6 Adaptation (E4) | rosafalco2024ekf, stevenshaas2024kalman, ross2011dagger, abdullah2023adaptive |
| §4.7 OOD guard / safety (E5, E7) | mahalanobis1936, lee2018mahalanobis, lakshminarayanan2017ensembles, hewing2020learning |

## Groups (key — role — status)

**A. SINDy method core** — brunton2016sindy[PDF], brunton2016sindyc[PDF],
desilva2020pysindy, kaptanoglu2022pysindy[PDF], champion2020sr3[PDF],
kaheman2020sindypi[PDF], messenger2021weak[PDF], messenger2021weakpde[PDF],
fasel2022ensemble[PDF], rudy2017pde, mangan2017modelselection,
loiseau2018constrained[PDF], loiseau2018sparsereduced[PDF], kaptanoglu2021trapping[PDF],
chen2021physicsinformed[PDF], cortiella2021sparse, yonezawa2025sindylom[PDF]⚠,
fukami2021sparse[PDF], balanceguided2026[PDF]⚠, datadenoise2025[PDF]⚠, brunton2019book

**B. Online / Kalman SINDy** — stevenshaas2024kalman[PDF]⚠, rosafalco2024ekf[PDF],
rosafalco2024online[PDF]⚠, onlinesparse2025kalman[PDF]⚠, abdullah2023adaptive

**C. MPC & learning-based MPC** — kaiser2018sindympc[PDF], mayne2000constrained,
rawlings2017mpc, hewing2020learning, rosolia2018learning[PDF], koller2018learningmpc[PDF],
ellis2014economic, tagliabue2021guided[PDF]

**D. Koopman / DMD control** — proctor2016dmdc, williams2015edmd, korda2018koopman,
koopmanmpc2026multistep[PDF]⚠, jacobiandmd2022[PDF]⚠, controlorientedsurvey2025[PDF]⚠

**E. Identification-for-control & objective mismatch** — gevers1993,
hjalmarsson1994closing, vandenhof1995closedloop, hjalmarsson2005experiment,
lambert2020objective[PDF], wei2023unified[PDF]⚠, farahmand2017value

**F. Imitation / DAgger** — ross2011dagger[PDF], ross2014aggrevate[PDF],
sun2017deeply[PDF], espin2024deepmpc[PDF]⚠

**G. RL algorithms** — schulman2017ppo, haarnoja2018sac, raffin2021sb3, sutton2018rl

**H. Greenhouse & crop** — vanhenten1994thesis, vanhenten2009timescale,
vanthoor2011tomato, vanthoor2011climate, katzin2020greenlight[PDF], katzin2021led,
vanlaatum2025greenlightgym[PDF]⚠, morcego2023rlvsmpc⚠, mallick2024rlmpc[PDF]⚠,
lin2021greenhousempc[PDF]⚠, chenyou2020ddrmpc[PDF]⚠, vanmourik2023stochastic[PDF]⚠,
adaptiverobust2025greenhouse⚠

**I. OOD / uncertainty** — mahalanobis1936, lee2018mahalanobis,
lakshminarayanan2017ensembles, gal2016dropout, hendrycks2017baseline

**J. Statistics / reproducibility** — wilcoxon1945, holm1979, efron1994bootstrap,
demsar2006, henderson2018matters, pineau2021repro

## ⚠ To verify before submission (metadata not fully confirmed)

**Authors CONFIRMED this pass (from arXiv abstracts):** yonezawa2025sindylom,
balanceguided2026 (Dang, Zhang, Wang, He), datadenoise2025 (Yao et al.),
rosafalco2024online (Rosafalco, Conti, Manzoni, Mariani, Frangi), onlinesparse2025kalman
(Pillonetto, Yazdani, Aravkin), wei2023unified (Wei, Lambert, McDonald, Garcia, Calandra),
koopmanmpc2026multistep (Wu, Tan, Zhou, Braatz, Drgoňa), jacobiandmd2022 (Jackson, Lee,
Tracy, Manchester), controlorientedsurvey2025 (Sivaranjani et al.), espin2024deepmpc
(Espin, Zhang, Toti, Pozzi), mallick2024rlmpc (Mallick, Airaldi, Dabiri, Sun, De Schutter),
vanmourik2023stochastic (van Mourik, van't Ooster, Vellekoop), morcego2023rlvsmpc
(Morcego, Yin, Boersma, van Henten, Puig, Sun — CEA 215:108372).

**Still to confirm (journal vol/pages/DOI — non-arXiv):** stevenshaas2024kalman (venue),
vanlaatum2025greenlightgym (IFAC vol/pages), lin2021greenhousempc (author/vol),
chenyou2020ddrmpc (venue/vol), adaptiverobust2025greenhouse (authors — Smart Agric. Tech.).
- Cross-check every arXiv eprint id against the actual PDF in `articles/`.

## Newly added this session (were used but not previously in repo)
lambert2020objective, wei2023unified, balanceguided2026, jacobiandmd2022,
controlorientedsurvey2025, koopmanmpc2026multistep, vanmourik2023stochastic,
mallick2024rlmpc (all downloaded to `articles/`); plus cite-only additions:
gevers1993, hjalmarsson1994closing, vandenhof1995closedloop, hjalmarsson2005experiment,
farahmand2017value, mayne2000constrained, rawlings2017mpc, hewing2020learning,
ellis2014economic, proctor2016dmdc, williams2015edmd, korda2018koopman,
schulman2017ppo, haarnoja2018sac, raffin2021sb3, sutton2018rl, vanhenten1994thesis,
vanhenten2009timescale, vanthoor2011tomato, vanthoor2011climate, katzin2021led,
morcego2023rlvsmpc, adaptiverobust2025greenhouse, mahalanobis1936, lee2018mahalanobis,
lakshminarayanan2017ensembles, gal2016dropout, hendrycks2017baseline, wilcoxon1945,
holm1979, efron1994bootstrap, demsar2006, henderson2018matters, pineau2021repro,
desilva2020pysindy, rudy2017pde, mangan2017modelselection, cortiella2021sparse,
abdullah2023adaptive, brunton2019book.
