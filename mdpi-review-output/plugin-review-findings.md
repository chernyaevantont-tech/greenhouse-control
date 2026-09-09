# Plugin review — findings, verdicts, and what was done

> ## Third pass: reconciled against the calculations themselves
>
> Four of the contradictions below were then settled **against the regeneration data and
> the experiment driver**, not against other parts of the manuscript. Two of them — C-3 and
> C-4 — were Critical and are now **fixed**. See "Corrections established from the data".
>
> The project's own gate now runs on the revised manuscript and passes:
>
> ```
> recomputed 758 table cells and 336 prose values against the tree
> walked 1977 printed numbers; 0 unclaimed
> every value agrees, and every printed number is accounted for.
> ```
>
> Reproduce with `python mdpi-review-output/verify-revised.py`.

Second review pass, run after the three plugins became loadable in-session.

**Sources:** `academic-prose` and `humanizer` skills (rules applied by hand), plus
`academic-writing-agents` specialist agents run over the revised manuscript.

**Every agent claim below was verified against the manuscript before acting.** Two were
wrong; they are recorded as rejected rather than quietly dropped. Nothing was applied on
an agent's say-so.

---

## Rejected — the agent was wrong

| Claim | Verdict |
|---|---|
| "Figure 1's caption describes a panel (**d**) the figure does not contain" | **False.** `figures/make_fig1.py` builds four subplots and the caption's panel (d) exists. What is true, and minor, is that the body text discusses only panels a–c. Recorded below as m-8. |
| "The bibliography has 44 entries" | **False.** 48. The agent's own spot-checks were sound, but the count was not. |

---

## CRITICAL — verified, and beyond what an editor may fix

These four are new, they are real, and each needs the authors. They are the reason this
manuscript is further from submission than the first pass concluded.

### C-3. The violation axis is defined as a quantity the reported numbers cannot be

A season is **5760 control steps** ("60 days from 1 March at a 15-min control step
($T_s=900$ s), i.e. 5760 control steps"). The second Pareto axis is defined twice as a
count of steps: *"$J$ and the seasonal count of steps in violation"*, and *"constraint
pressure is the seasonal count of simulation steps outside the productive envelope"*.

But the manuscript reports violation figures of **9131, 9569, 6167 and about 9090** —
all larger than the number of steps in a season. A count of steps cannot exceed 5760.

The quantity is therefore almost certainly **variable-steps summed over the three corridor
variables** (ceiling 17,280), or accumulated excess. Either way the definition as printed
is wrong, and it is wrong in the two places a reviewer will look first.

**[AUTHOR CHECK: state the actual aggregation rule. If it is a sum over the three corridor
variables, the definition should read "the seasonal count of variable-steps in violation,
summed over the three corridor variables", and Figure 2's axis label needs the same
correction. If the quantity is accumulated excess rather than a count, the word "steps"
is wrong everywhere it appears.]** Not fixable here: only the authors know which.

### C-4. The Conclusions report a priced sensitivity the Results say was never measured

Conclusions: *"a $\pm15\,\%$ coefficient perturbation costs $7.97$ on the mean against
$3.35$ on the median ($p=4.3\times10^{-3}$)"*, and Table 9 carries a row labelled
"$\pm15\,\%$ coefficient perturbation, **priced**".

Results §3.8 states the opposite in plain words: *"The coefficient and threshold
sensitivities have consequently never been measured under the priced objective."* The
Discussion limitation agrees: *"The design and sensitivity blocks use the default
objective."*

Verified: the strings `7.97` and `design_priced_real` appear **4 times in the Conclusions
and zero times in the Results or Discussion**. The directory
`own-article/regen/results/design_priced_real/` **does exist** and contains
`design_designPriced.csv`, so the numbers are real data, not invention — and the numeric
gate traces them, which is why nothing failed.

So this is a narrative contradiction, not a fabrication: either a priced wave was run
later and §3.8 was never updated, or the Conclusions row is mislabelled. One further
signal: the provenance comment beside those values lists levels `0.02 / 0.05 / 0.10 /
0.15 / 0.20` and the contrast "0.15 against 0.02", which reads like a **sparsity-threshold
sweep**, not a ±15 % coefficient perturbation.

**[AUTHOR CHECK: resolve which. If the priced wave is real, report it in §3.8 and correct
the sentence that says it was never measured. If the Table 9 row is mislabelled, relabel
it. As it stands, a reviewer reading §3.8 and the Conclusions together sees a direct
contradiction about what was run.]**

### C-5. "The same shape under the other estimator" is not available under that estimator

Conclusions: the non-monotone series holds *"with the same shape under the other
estimator."*

Under STLSQ the intermediate library was never run: Table 6 prints
`p_nc  --  (not run)`, and the Methods say so explicitly — *"the STLSQ arm has only the two
endpoints… Any statement about how the library ordering behaves **between** the endpoints
therefore rests on the ensemble arm alone, and is scoped that way throughout."*

A "shape" is a three-point property. With two points there is no shape to reproduce. The
Conclusions contradicts the scoping the Methods promise to hold throughout, on the paper's
central non-monotonicity claim.

**[AUTHOR CHECK: suggested wording, which keeps everything that is supported —
"with the raw-over-physics direction reproducing under the other estimator, where the
intermediate library was not run". Not applied here: it changes the strength of a claim,
which this review does not do unilaterally.]**

### C-6. An entire experimental arm has no Methods

The 17-feature `physics_no_tuboil` library and its two controllers
(`sindy_mpc_notuboil`, `sindy_mpc_notuboil_ens`) carry the falsification of the retracted
detour reading — a headline contribution — but appear for the first time in the Results.
Methods §2.4 defines three libraries; Table 2 lists 15 controllers and excludes these two.
A reader meets a fourth library and two undefined controllers with no definition available.

**[AUTHOR CHECK: add `physics_no_tuboil` (17 features) to the §2.4 library list and its two
controllers to Table 2, marked as a term-deletion probe outside the 15-controller
comparison and outside the Holm family.]** Not applied: adding a row to a validated table
and a new Methods paragraph is authoring, not editing.

---

## MAJOR — verified, author decision

| # | Finding | Note |
|---|---|---|
| M-5 | **The headline significance test is never reported in the Results.** The Abstract, Introduction, Conclusions and Table 9 all rest on raw vs best physics-informed variant at $p_{\mathrm{Holm}}=7.7\times10^{-4}$; §3.3 reports only tests against the tuned heuristic, and the Discussion cross-references "the paired raw-versus-physics contrast of Section 3.3", which that section does not contain. |
| M-6 | **The same stratification is reported at two p-values on two different units**, $p=0.053$ (run-level, 12 vs 68) in the Conclusions and $p=0.18$ (replicate-level, 3 vs 17) in the Discussion — and the run-level one is the more favourable, straddling 0.05, computed on the unit the manuscript's own table footnote rejects. |
| M-7 | **Paired tests treat clustered observations as exchangeable.** $n=80$ pairs are (seed × season), but the four seasons of a seed share one identified surrogate. The manuscript applies the effective-$n$ argument to survival only. Reported levels are optimistic for every $n=80$ contrast. |
| M-8 | **"Bagged ensembling changed neither outcome … ($p=0.057$)"** reads a failure to reject as evidence of equivalence — a distinction the manuscript makes correctly elsewhere for the $p=0.60$ case. |
| M-9 | **"By a factor of 10" is a ratio of two noisy means** whose denominator is $+0.28$ with SD $4.11$. The paired difference $+2.47$ is already printed and is the quantity the test estimates. |
| M-10 | **Promised bootstrap confidence intervals never appear.** §2.8 promises "bootstrap confidence intervals" citing `efron1994, demsar2006`; no bootstrap CI appears anywhere. Separately `demsar2006` is about comparing classifiers across data sets, not bootstrap. |
| M-11 | **Limitations assert a hyperparameter search the Methods say never happened** ("the reinforcement learning agents and the heuristic received 16 trials each" vs "no hyper-parameter search artefact for either exists in the results tree"). |
| M-12 | **Symbol collision:** $c_k$ is variable cost in Equation (1) and $c$ is CO₂ concentration in Equation (2). |
| M-13 | **The central coefficient has four spellings** — $\xi_{u\mathrm{Boil}}$, $\xi_{u_{\mathrm{boil}}}$, $\xi_{u\text{Boil}}$, bare $\xi$ — and is never defined at first use; its only definition is a footnote to the final table, ~450 lines after first use. Controls likewise vary: $u_{\mathrm{boil}}$/$u_{\mathrm{Boil}}$, $u_{\mathrm{thscr}}$/$u_{\text{ThScr}}$. |
| M-14 | **Equation (3) omits terms the text says are active** — a move-suppression term and box constraints. A reader implementing the display solves a different problem. |
| M-15 | **`yonezawa2026` is cited on both sides.** The Introduction lists it as an example of selecting by one-step accuracy; the Discussion says it converges on the paper's own remedy; its title is "…Recursive long-term prediction perspective". The Introduction's use is a misattribution. |
| M-16 | **PINN references over-extended.** `raissi2019` and `karniadakis2021` are cited for the practice of adding physically motivated columns to a sparse-regression library; both concern embedding PDE residuals in neural training. |
| M-17 | **Named methods without citations:** SR3, the SINDy software implementation, the Magnus–Tetens coefficients, L-BFGS-B, cross-entropy planning and the extended Kalman filter are uncited while IPOPT, do-mpc, PPO, SAC and Stable-Baselines3 are cited. |
| M-18 | **Retracted-mechanism residue in Table 1**, which still lists candidates as *"scored by multi-step rollout stability and regression conditioning"* — the Discussion recommends the opposite ("The condition number belongs in the report as a diagnostic but not in the ranking"). |
| M-19 | **Methods reproducibility gaps:** greenhouse type, floor area, lamp/boiler/CO₂ capacities, the crop's initial state at 1 March, the size of the identification set, and the excitation specification (which channels, switching period, distribution) are not stated. MDPI *Agronomy* explicitly requires enough design detail to reproduce. |

---

## Applied — verified factual corrections and style normalisation

Six edits. None changes a measured value, a claim's strength, or an interpretation.

| # | Where | Was | Now | Why |
|---|---|---|---|---|
| A-7 | `02-methods.tex` | "**Four** of the SINDy-MPC labels form a deliberate one-factor design" | "**Five** of the SINDy-MPC labels…" | Counting error: the sentence then lists five (`raw_ens`, `conf`, `phys_ens` under the ensemble estimator; `raw`, `phys` under STLSQ). Verified by reading the list. |
| A-8 | `04-discussion.tex` | "**Two** things follow for practice" | "**Three** things follow for practice" | Broken enumeration: the passage continues "The second thing…" and "The third piece of guidance…". Verified at three line numbers. |
| A-9 | `03-results.tex` | "**pre-declared** family of 15 controllers" | "declared family of 15 controllers" | The manuscript states elsewhere that adding two controllers "enlarged the family from 13 to 15 and moved every corrected level". A family revised after the levels were computed is not pre-declared. One word deleted; the claim is now accurate. |
| A-10 | throughout | `EUR/m$^2$` ×6 | `EUR\,m$^{-2}$` | Unit consistency (MDPI §6.2): 6 occurrences against 92 of the negative-exponent form. |
| A-11 | throughout | `EUR~m$^{-2}$` ×7 | `EUR\,m$^{-2}$` | Same unit, inconsistent spacing command. |
| A-12 | throughout | `$^\circ$C` ×14 | `\textdegree C` | 14 against 16 of the dominant form. |

### Abbreviations MDPI requires to be defined (second agent, verified)

MDPI: an abbreviation is defined separately in **the abstract, the main text, and the
first figure/table caption** that uses it, "because they are often displayed in isolation".

| # | Abbreviation | State found | Applied |
|---|---|---|---|
| A-13 | **RMSE** | Used **31 times**; `root-mean-square`, `root mean squared` and `root` return **zero hits in the entire manuscript**. Never expanded anywhere, including the abstract. | Expanded at first use in the **abstract** and at first use in the **Results** running text. |
| A-14 | **PPO** | Used 9 times. Expanded only inside a bibliography title, which does not define it. First prose use is in the Introduction. | "proximal policy optimisation (PPO)" at first main-text use. |
| A-15 | **SAC** | Used 4 times, same situation. | "soft actor-critic (SAC)" in the first table that uses it, alongside PPO. |
| A-16 | **°C** | A fourth spelling, `\,^\circ$C`, survived the first sweep (13 sites). | Normalised to `\textdegree C`. Latitude and longitude degrees (`$47.24^{\circ}$~N`) are a different quantity and were correctly left alone. |

**Still outstanding, author's call:** MDPI also wants each of these defined in the first
**caption** that uses them, which A-13…A-15 do not yet satisfy in every case; and **SD**
(26 uses) is never bound to "standard deviation". **[AUTHOR CHECK]**

**Numeric effect of A-10:** rewriting `m$^2$` as `m$^{-2}$` turns six printed `2`s into six
`-2`s. That is the *only* numeric difference the integrity proof reports, and it is an
exponent in a unit, not a measured value. Every measured value is unchanged.

---

## Further verified findings from the consistency pass — author decisions

The second agent read the manuscript **and the rendered figures**. Its independent
confirmation of C-4, A-8 and A-9 is a useful cross-check. Its additional findings:

| # | Finding |
|---|---|
| M-20 | **Table numbering breaks MDPI's order-of-first-citation rule.** `tab:main` (Table 6) is first cited at line 1168; `tab:tune` (Table 5) not until line 1301. Verified. Every figure is in order; only this table pair inverts. |
| M-21 | **Arithmetic in prose does not match its own numbers.** "the median falls only from $+4.47$ to $-0.31$, a span of $5.72$" — but $4.47-(-0.31)=4.78$. The $5.72$ is a max−min span (the median peaks at $+5.40$). Each number is individually correct, which is why the numeric gate passes; the *relation asserted between them* is not. |
| M-22 | **Figure 2's caption and Table 6 round the same difference differently** (5 vs 6 violation steps; the unrounded value is 5.5). |
| M-23 | **Figure 3(b) plots `nn_mpc` survival at 0.00**, which Table 6's own note forbids: "`xi_uboil` is empty in all 40 of its rows, which must not be read as zero survival … it is excluded from every survival comparison". |
| M-24 | **Figure 1's text/caption mismatch**: the body attributes to panel (b) two encodings only panel (a) has, and says panel (c) holds the ensemble estimator fixed while the panel also plots the STLSQ arm. |
| M-25 | **Controller display names in figures are never mapped to the labels used in text and tables** — "frozen" is never connected to `sindy_mpc_conf` anywhere. |
| M-26 | **Terminology collisions**: the grid axis {STLSQ, SR3, constrained, ensemble} is called both "estimator" and "optimiser", sometimes in adjacent sentences; `oracle_mpc` has six names; `nn_mpc` has five; the non-priced arm is called both "original" and "default"; the constraint region has four names. |
| M-27 | **"Three pre-registered axes" against "the pre-registration declared two gates"** — and active-term count is nowhere declared as a gate. |
| M-28 | **"Family of 15" denotes two different families**, and in one the stock heuristic is counted twice. |
| M-29 | **Tables 3 and 5 present the same setpoint search with the same values**, with near-duplicated prose in §2.7 and §3.2. |

**Note on M-26 and the pass-1 spelling fix:** normalising `optimizer` → `optimiser` was a
spelling fix and remains correct. It does **not** resolve the deeper problem that the same
object is called an "estimator" in the Methods and an "optimiser" in the Results. That
needs one term chosen and applied, which touches ~30 sites including table headers and
figure labels. **[AUTHOR CHECK: "estimator" for the algorithm, "optimiser" for the NLP
solver, is the reviewer's suggestion and reads correctly against the Methods.]**

---

## Fourth agent (prose review) — applied

Seven further edits. It independently re-derived A-7 ("Four"→"Five"), A-8 ("Two things"→
"Three things") and C-4 (the priced-objective contradiction), which is useful corroboration.

| # | Where | Fix | Why |
|---|---|---|---|
| **A-17** | `04-discussion.tex` §4.1 | *"they entered in two groups of three and four, **no feature was added or removed alone**, and the one single-feature deletion that would matter most is **the untested experiment named above**"* → *"they entered in two groups of three and four, and the only single-feature deletion tested was that of the bilinear $T_{\text{in}}u_{\text{Boil}}$ term."* | **Stale text.** The manuscript reports a completed single-feature deletion wave (`physics_no_tuboil`, five mentions in the Results and five in the Discussion). Both clauses were false, and "named above" referred to nothing after the wave was written up. Verified before changing. |
| A-18 | `04-discussion.tex` Limitations | "a three-point library comparison, which is **few**" → "which is **a narrow base**" | Number disagreement, in a bolded limitation heading. |
| A-19 | `01-introduction.tex` | "a raw, physics-free library … attains the best four-season mean margin **of the 15 controllers**" → "**the controller built on** a raw, physics-free library …" | Category error: a library is not one of the fifteen controllers, so the comparison class did not contain its own subject. |
| A-20 | `02-methods.tex` §2.3 | "**Second,** the aggregation loop applied to two SINDy controllers…" → "The aggregation loop applied…" | Orphan ordinal: there is no "First". |
| A-21 | `02-methods.tex` §2.6 | "coefficient and threshold sensitivity **have not been** re-evaluated" → "**were not** re-evaluated" | MDPI Layout Style Guide §4.1.2: Methods take the simple past, and "The present perfect should be avoided". |
| A-22 | `05-conclusions-abstract.tex` **abstract** | "**Outcomes were simulated** seasonal margin and climate-corridor violations." → "**Outcome measures were** simulated seasonal margin…" | "Outcomes were simulated" parses as a passive verb, not a copula, in the most-read sentence block of the paper. |
| A-23 | `04-discussion.tex` §4.2 | "**Ours scored** 96 steps (24 h) against a 20-step (5 h) control horizon" → "**Our screen used** a 96-step (24 h) rollout against a 20-step (5 h) control horizon" | "Ours" had no antecedent, and a screen does not "score" steps. |

**Abstract length after A-22 and the RMSE expansion: 193 words** (was 190). MDPI Agronomy
allows about 200. Keywords remain 8 (limit 3–10).

**Four of its findings could not be located in the current text** — the agent quoted
strings that no longer exist after the earlier dash and spelling passes. They were **not**
applied: an edit whose target cannot be matched exactly is an edit that should not be made
blind. Worth a re-run against the current file if you want them.

### Its findings that were verified but NOT applied

| Finding | Why not |
|---|---|
| Contribution heading (i): *"the closed-loop ordering **follows** the multi-step one"* against §3.1's *"not that it ranks libraries"* and §4.2's *"neither open-loop criterion reproduces the full closed-loop ordering"* | A real contradiction, and the suggested fix ("the multi-step criterion selects the best library in closed loop") is good — but it changes the strength of a headline contribution claim. **[AUTHOR CHECK]** |
| Shift §3.1 and §3.5 from present to past tense (~7 sites) | MDPI §4.1.3 explicitly permits the present tense for results treated as established facts, and calls the past-tense form merely "the best option". A preference, not a rule, across many sites. |
| *"the learned controllers received 16 tuning trials"* against §2.3, which says the neural surrogate had no search | Same class as M-11; both should be settled together by the authors. |
| Reorder the values inside two parentheses so both read lose-then-keep | Correct in principle, but it repairs which number pairs with which label — too easy to introduce an error, and it is the authors' data. |
| Register: "does not pay", "works", "one bad basin", "the boiler term dying" | Below MDPI register, but each is a deliberate authorial choice, not an error. |
| Repeated frame *"The honest reading is / The supportable claim is / What is defensible is"* (5 occurrences) | A genuine repeated-frame tell, and "honest" does imply the alternatives are dishonest. Rewording five hedged epistemic frames touches how strongly five claims are stated. **[AUTHOR CHECK]** |

---

## Verified, and deliberately NOT applied

| Finding | Why not |
|---|---|
| Hedge the causal verbs: "What **determines** the closed-loop margin" → "tracks"; "Survival **gates** the outcome" → "appears to gate"; "which **implies**" → "suggests" (7 sites) | Real and well-argued — the library-level evidence is observational, and the manuscript says so itself. But the brief for this review is explicit: **preserve the confidence level of every statement**. Weakening seven claims is a scientific decision for the authors. **[AUTHOR CHECK: the reviewers make a good case; the two strongest statements in the paper are the two using causal verbs on observational evidence.]** |
| "pre-registered gates/axes" → "applied gates/axes" (3 sites) | Same class as C-2 from the first pass: the Methods say the pre-registration declared embeddability and a transparency check, specified stability only qualitatively, and never evaluated the transparency gate. Correcting this is right, but it interacts with the unresolved preregistration-link question and should be settled once, by the authors. |
| Replace "by a factor of 10" with "$+2.47$~EUR m$^{-2}$" (4 sites) | Statistically the better summary, but it substitutes one reported quantity for another. Author's call. |
| Conclusions: "the ordering of the margins" → "the grouping of the margins" | Correct — two libraries at 0.55 score $+4.32$ and $+2.75$, so survival groups but cannot order, exactly as the Introduction says. Still a claim-strength change. |
| Rename the cost symbol in Equation (1) to resolve the $c$ collision | Editing equations and propagating a symbol change through the manuscript is authoring, not copy-editing. |
| Normalise $\xi$ and control subscripts | Safe in principle, but these sit inside math mode across ~30 sites and interact with table headers and figure labels; worth doing in one careful pass with the figures regenerated. |
| Add a bridge sentence to §3.2; add the fault-supervisor block to the roadmap; retitle "Sparsity is exonerated" | Structural authoring. |

---

## The pre-registration question, settled

**What it is for.** A pre-registration is the difference between "we said in advance what
would count as success, then measured" and "we measured, then decided what counts as
success". It matters here more than in most papers, because the central claim *is* a
selection rule: that multi-step stability picks the right feature library. If the selection
axes had been chosen after the closed-loop economics were visible, that claim would be
circular. MDPI requires the link because a pre-registration claim is only checkable when a
reader can see the frozen plan and its timestamp.

**What this study actually has.** A real one, and it holds up:

| | |
|---|---|
| The plan | `own-article/EXPERIMENT_PROTOCOL.md`, whose §5 is "Шлюзы (gates) — формальные критерии допуска" |
| Frozen | first committed **2026-06-26**, last touched **2026-07-03** |
| Earliest reported result wave | records a commit dated **2026-08-09** |
| Margin | the plan predates every reported wave by about **five weeks** |

So the substance is there. What is missing is only that it sits in a git repository rather
than a public registry, which the Zenodo deposit fixes.

**The larger problem, which was not the missing link.** Methods §2.5 already states the
position, and states it well:

> "The pre-registration declared two gates, MPC-embeddability and a sign-and-dimension
> transparency check, and specified multi-step stability only qualitatively… **What was
> applied differs on both counts and is reported as applied**: the divergence criterion was
> operationalised as a fixed threshold of 0.05 in the table generator, and the transparency
> column is empty in all 1440 rows, so that gate was never evaluated and is not claimed here."

But four sites in the Results and Discussion then called the **applied** criteria
pre-registered — "pre-registered gates (embeddable and diverged fraction ≤ 0.05)" and
"all three pre-registered axes". By the manuscript's own account the 0.05 threshold was not
pre-registered, and the third axis (active-term count) appears as a gate **nowhere** in
`EXPERIMENT_PROTOCOL.md`. A reviewer who read Methods and then Results would have caught
the paper contradicting itself on its own methodological safeguard.

**Applied** — the four sites now say what Methods already says:

| Where | Was | Now |
|---|---|---|
| Results §3.1 | "32 pass both **pre-registered** gates" | "32 pass both **applied** gates" |
| Results §3.1 | "all three **pre-registered** axes" | "all three **applied open-loop** axes" |
| Results §3.1 | "still on the **pre-registered** axes" | "still on the **applied open-loop** axes" |
| Discussion §4.2 | "**pre-registered** axes at once" | "**applied open-loop** axes at once" |
| Methods §2.5 title | "and **pre-registered** open-loop criteria" | "and **pre-specified** open-loop criteria" |

The one honest mention in Methods — that a pre-registration existed and what it declared —
**stays**, because removing it would hide a real methodological strength. It now names the
artefact and carries a placeholder for its DOI, in the same red style the manuscript
already uses for the Data Availability blocker.

**Two things remain, and both are one action each:**

1. `EXPERIMENT_PROTOCOL.md` **is not in the archive.** `own-article/regen/make_archive.py`
   lists `PARENT_MODULES = ("article_experiment_utils.py", "protocol_config.py",
   "rostov_soil.py", "make_weather.py")`, and the built zip's top level confirms it: the
   plan is absent. Add it there and rebuild the archive, or the preregistration link will
   point at a package that does not contain the plan.
2. Once the deposit exists, `python mdpi-review-output/apply-zenodo-doi.py 10.5281/zenodo.XXXXXXX`
   fills **both** placeholders — the Data Availability Statement gets MDPI's recommended
   wording, and the Methods pointer gets the same DOI. Dry-run on a scratch copy leaves
   zero `[[` placeholders.

**A note on the checker.** Rewording "pre-registered axes" broke an anchor in
`verify_prose.py`, which matches that sentence literally, and six checks went dark. The
same trap as the degree-sign episode. Here the wording change is correct, so the checker
moved with it: `mdpi-review-output/manuscript-revised/verify_prose.py` carries the updated
anchor, and `verify-revised.py` prefers a patched checker over the original. **If you adopt
the revised sections, adopt that checker with them** — otherwise those six checks silently
stop verifying.

---

## Corrections established from the data

Each of these was decided by computing over `own-article/regen/results/` or by reading the
experiment driver, not by weighing one sentence against another.

### D-1. The violation axis was defined as a quantity it is not — **C-3, fixed**

**Evidence.** In `results/priced_main/*.csv` (545 rows) the column `violation_steps_total`
equals `t_in_violation_steps + co2_violation_steps + rh_violation_steps` in **100.0 % of
rows**, and exceeds the run's own step count in **30 rows**. A count of *time* steps cannot
exceed the season's 5760; a count of *variable*-steps over three corridor variables can
(ceiling 17,280, and the observed maximum is 9359).

**Applied**, at both definition sites:

- Methods: "the seasonal count of steps in violation" → "the seasonal count of
  **variable-steps** in violation, **summed over the three corridor variables**".
- Results: "the seasonal count of simulation steps outside the productive envelope" →
  "the seasonal count of **variable-steps** outside the productive envelope, **summed over
  inside-air temperature, CO₂ and relative humidity**".

**[AUTHOR CHECK: Figure 2's axis label carries the same wording and is baked into the
figure. It needs regenerating to match.]**

### D-2. The coefficient perturbation is not priced — **C-4, fixed**

Three independent lines of evidence, and they agree:

1. `design_priced_real/design_designPriced.csv` (280 rows) merges **280 of 280** rows with
   the deduplicated `priced_design` wave at **identical EPI**. They are the same runs.
2. `figures/_plotstyle.py`, `load_design()`: *"**MISLABELLED DIRECTORY.** Despite the name,
   these runs use the **ORIGINAL** objective … **Never caption them as priced.**"*
3. `regen/experiments_support.py`, lines 21–23, the author's own warning: *"The blocks below
   hard-coded `objective="full"` and therefore **SILENTLY ignored the driver's --objective
   flag**. The E-E wave, launched with `--objective priced`, was in fact scored on the
   hard-coded weights: confirmed."* `exp_design`, which produces `coef_perturb`, is one of
   those blocks.

That is also why the wave's `run.log` says "priced": the flag was passed and ignored.

**So the Results sentence was right all along** — "the coefficient and threshold
sensitivities have consequently never been measured under the priced objective" — and the
Conclusions' Table 16 row was mislabelled. **Applied:**

- Table 16 row: "±15 % coefficient perturbation, **priced**" → "±15 % coefficient
  perturbation, **default objective**".
- The provenance comment that asserted "NOW MEASURED UNDER THE PRICED OBJECTIVE" was
  corrected so it cannot mislead a copy-editor.

**No number changed.** 7.97 and 3.35 are correct; only the objective label was wrong.

### D-3. A span attributed to the wrong pair of numbers — **M-21, fixed**

Table 13's medians are +4.47, +4.35, **+5.40**, +1.12, −0.31 and its printed span is 5.72,
which is max − min = 5.40 − (−0.31). The prose said *"the median falls only from +4.47 to
−0.31, **a span of 5.72**"*, but those two endpoints differ by **4.78**. The checker
confirms the intent: `check_sens` computes the span row as `max(medians) − min(medians)`.

**Applied:** "while the median is non-monotone, peaking at $+5.40$ at the 10 % level before
falling to $-0.31$, a span of $5.72$". Every number is already in Table 13.

### D-4. Caption and table rounded the same difference differently — **M-22, fixed**

Over the deduplicated priced pool, `sindy_mpc_dense` averages **3686.30** violation steps
and `sindy_mpc_lowthr` **3691.61**. The difference is **5.3125**. The caption rounded the
difference (5); the table rounded each value and then differenced (6). Both are correct
roundings of the same quantity, which is why they disagreed.

**Applied:** the caption now quotes **5.3**, which no longer clashes with the table's 3692
and 3686. The ΔEPI of 0.0066 was verified as correct (0.006597).

---

## Blockers 3 and 4, closed

### C-5. "The same shape under the other estimator" — fixed

Under STLSQ the intermediate library is printed as **"(not run)"**, and the Methods scope
every between-endpoint statement to the ensemble arm: *"Any statement about how the library
ordering behaves between the endpoints therefore rests on the ensemble arm alone."*
A three-point shape cannot reproduce from two points; the direction can.

- **was:** "…the worst-conditioned library beating the intermediate one almost tenfold,
  **with the same shape under the other estimator**."
- **now:** "…the worst-conditioned library beating the intermediate one almost tenfold.
  **The raw-over-physics direction reproduces under the other estimator, for which the
  intermediate library was not run.**"

### C-6. The `physics_no_tuboil` arm now has Methods — fixed

Two additions, both in Section 2.4:

1. A paragraph after the three-library list: `physics_no_tuboil` is `physics` with the
   single bilinear term $T_{\mathrm{in}}u_{\mathrm{boil}}$ deleted, leaving 17 features;
   it exists to test the detour reading and is refit at both sparse estimators at the
   frozen threshold; its two controllers lie outside the one-factor series, outside the
   fifteen-controller comparison and outside the Holm family.
2. Table 2 gains the two controllers **below a rule**, under the heading *"Term-deletion
   probe, outside the fifteen-controller comparison and the Holm family"*, so every claim
   of "fifteen controllers" elsewhere stays true.

The gate stayed green through both: 1,980 printed numbers, 0 unclaimed, 0 mismatches.

---

## Figures: regenerated, corrected and inspected

All six were regenerated from the data (`make_fig1.py` … `make_fig6.py`, self-checks
48/48 and 61/61 passing). Originals under `own-article/paper/en/figures/` are untouched;
the new ones are in `mdpi-review-output/manuscript-revised/figures/`.

### Corrections of substance

| Figure | Was | Now |
|---|---|---|
| **2, x axis** | "Mean violation steps per season **(of 5760)**" — while plotting values up to 9359 | "Mean violation variable-steps per season (sum over T, CO₂, RH)". The parenthetical was the C-3 error rendered graphically: it told the reader the ceiling was 5760. |
| **3, panel (b)** | An **NN-MPC tick at survival 0.00** | Removed. Table 6's own note says `xi_uboil` "is empty in all 40 of its rows, **which must not be read as zero survival** … it is excluded from every survival comparison". The figure was asserting what the table forbids. The self-check that guards "every controller has a tick" was updated with the same reason. |
| **1, panel (d)** | x tick read "18 terms **+t_uBoil**" — the raw CSV column name, underscore and all, in a serif face | "18 terms + $T_{\mathrm{in}}u_{\mathrm{Boil}}$", the manuscript's own symbol |
| **2 and 6, y axis** | "economic performance **index**" | "**indicator**", which is what the manuscript defines EPI to be |
| `_plotstyle` | `physics $-$ $t\,u_{\mathrm{Boil}}$` — a third spelling of the coefficient | aligned to $T_{\mathrm{in}}u_{\mathrm{Boil}}$ |

### Overlaps found by inspecting the rendered PNGs, and fixed

Each was confirmed by cropping the 600 dpi output, not by reading the code.

| Figure | Overlap | Fix |
|---|---|---|
| **2** | The Pareto front, the error bars and the dotted reference line all **read through** the point labels: the halo behind them was only 72 % opaque. "frozen + re-ident." had the dotted line straight through it. | Halo raised to 92 % with a larger pad. Text already sat at zorder 7, so nothing moved. |
| **3** | The bold panel tag **"(b)" sat on top of** its own title, "boiler-term survival against the threshold" — the long centred title ran left past the axes. | Title shortened to "survival against the threshold". The y axis already says "boiler term kept", so nothing is lost. Also removes text. |
| **6 (a)** | The curved arrow ran **straight through** the two-line annotation "richer physics library: better one step, worse rollout". | Halo added. Then the halo revealed a second collision with the `raw` divergence label, so the annotation was raised and shifted left; both are now clear of each other and of the legend. |
| **6 (c)** | Controller labels crossed the non-dominated front line. | Halo added. |
| **4 (b)** | The black heuristic curve dipped through the **legend text**; the grid lines crossed the two-line footnote. | Legend given an opaque frame; footnote given a halo. |

### Checked and found sound

- **Font sizes** (from the shared rcParams): axis labels and panel titles 8 pt, tick labels
  7 pt, legends 7 pt, panel tags 9 pt bold, in-panel annotations 6.5 pt. At 600 dpi and
  the print widths below, all are legible; 6.5 pt is the floor and is used only for
  secondary annotations.
- **Print geometry**: figures 1–5 render 15.8–17.2 cm wide against a text width of about
  18.5 cm, so none is scaled down at layout — the point sizes above are the sizes on paper.
- **Graphical abstract**: 4434 × 1514 px, i.e. 18.8 × 6.4 cm, against MDPI's minimum of
  1100 × 560 px. PNG, no "Graphical Abstract" heading inside the image, as MDPI requires.
- **Figure 5** needed nothing: no overlaps, moderate text, clear legend.
- **Figure 1** panels (a)–(c) needed nothing.

### M-25 and M-26, closed

**M-25 — display names now map to the table labels.** Figure 2's caption gained a key:

> *Marker labels abbreviate the controller names of Table 2: **frozen** is
> `sindy_mpc_conf`, **dense** is `sindy_mpc_dense`, **dense, low thr.** is
> `sindy_mpc_lowthr`, **raw** and **raw (ens.)** are `sindy_mpc_raw` and
> `sindy_mpc_raw_ens`, **physics** and **physics (ens.)** are `sindy_mpc_phys` and
> `sindy_mpc_phys_ens`, and **+ re-ident.** marks the two on-policy re-identification
> variants.*

Figure 2 carries the densest set of these abbreviations and is where the reader meets
them; the self-evident ones (PPO, SAC, NN-MPC, oracle MPC, heuristic) are left alone
rather than padding the caption. Verified present in the built `.docx`.

**M-26 — one name for the non-priced objective.** It was called "original" 9 times and
"default" 17, sometimes for the same data, plus "original stage cost" against "default
stage cost". Normalised to **default**, which is the majority form and the one the Methods
use. Counts now: `default objective` 19, `default stage cost` 4, `original objective` 0 in
prose, 0 in the figure code. The three surviving instances are inside `%%` provenance
comments, which do not print.

The Figure 4(a) annotation was baked into the image and read "original objective (see
caption)"; the generator was corrected and the figure regenerated, so it now agrees with
the caption and the body text.

A third site of the C-3 violation wording turned up in the same caption while doing this —
"constraint-violation **steps**" — and was corrected to "variable-steps" alongside the two
found earlier.

### Still left for the author

| Item | Why not changed here |
|---|---|
| **Figure 2 label-to-marker ambiguity.** "raw" and "physics (ens.)" sit in a cluster where it is not obvious which label belongs to which marker; "physics" is nearer the grey square than its own point. | Not an overlap — a placement judgement in the densest region of the panel. Fixing it well means leader lines or pushing labels outward, either of which risks new collisions. The new caption key removes the *naming* ambiguity but not the geometric one. |
| `-- wins 6/9` in Figure 4's legend renders as two hyphens. | An en dash risks a missing glyph in the serif face; cosmetic. |
| **Figure 3's strip uses a different short-name set** ("raw, STLSQ", "frozen recipe") from Figure 2's. | Consistent within itself and adjacent to its own leader lines; unifying the two sets is a design decision. |

---

## A regression I introduced, and removed

Worth recording plainly. The unit-consistency pass (A-16) rewrote `\,^\circ` as
`\textdegree`. That is cosmetically better and **it silently broke five checks** in
`verify_prose.py`, which anchors on the literal `\,^\circ` form. Five values stopped being
verified — the exact "a checker that silently skips looks like one that passes" failure the
project's own documentation warns about.

The manuscript turned out to use **three** degree spellings, and the normalisation
collapsed them into one, so a naive revert could not tell them apart. All three were
restored site by site, keyed on the number beside each sign, and the gate then went green.
**The unit normalisation was abandoned**: MDPI's style guide says its own editors fix unit
formatting in production, so it was never worth losing verification coverage for.

---

## Minor

- **m-8.** Figure 1's body text discusses panels a–c; panel (d) exists but is never referenced in the text.
- **m-9.** `tab:ladder` bolds `2.022` (best one-step) and `30.84` (worst rollout) in the same row with no key in the caption.
- **m-10.** §2.7 reports outcomes ("Tuning is worth $+3.49$…", "Only 2 of the 16 draws beat…") that reappear almost verbatim in §3.2, and `tab:rbtune` duplicates four rows of `tab:tune`.
- **m-11.** Notation drift: $\lambda$ used from Table 2 onward and never defined; horizon written $N$ and $h$; $T_s$ defined once and never used; "$u=(1,1,1)$" reuses $u$, defined elsewhere as a six-vector; Equations (1) and (2) referenced by hard-coded number rather than `\eqref`.
- **m-12.** §4.3 is titled "Sparsity is exonerated" and opens by acquitting sparsity, but no section of the current manuscript accuses it — residue of the retracted "Ill-Conditioning, Not Sparsity" framing.
- **m-13.** The recommended screening gate would have rejected the library that finished **second** in closed loop ($0.0767 > 0.05$). §3.1 says so; the Discussion and Abstract recommend the gate without the caveat.

---

## Where both reviewers found the manuscript sound

Recorded because it is the larger part of the verdict:

- **The retraction is clean.** The withdrawn ill-conditioning mechanism is consistently
  retracted across all five files, $\kappa$ is confined to open-loop claims, and the figure
  captions carry explicit retraction guards. Only two residues were found (M-18 and a
  recurring "not a *sufficient* explanation" modifier), neither restating the causal chain.
- **Manipulated vs observed is handled better than most published work in the genre** —
  the manuscript repeatedly states that library-level survival is measured rather than
  assigned, and that the single-coefficient ablation is the only randomised contrast.
- **The narrative arc holds**: two questions posed, four contributions mapping onto four
  Results sections, and Conclusions returning to both questions in the same terms.
- **Scope-limiting language in the Abstract, Introduction and Conclusions is strong**; no
  sentence in those blocks reads as a field-performance claim.
- **Displayed equations are punctuated correctly throughout**, and the bibliography's
  venue/volume/page details matched on every spot-check.
