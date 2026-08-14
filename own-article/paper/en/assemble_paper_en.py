# -*- coding: utf-8 -*-
"""Assemble own-article/paper/en/paper_en.tex from the five verified sections.
Bibliography is emitted in order of first citation in the assembled body."""
import re, os, io

D = 'C:/Users/zergu/repos/greenhouse-control/own-article/paper/en'
OUT = os.path.join(D, 'paper_en.tex')

SEC = ['01-introduction.tex', '02-methods.tex', '03-results.tex',
       '04-discussion.tex', '05-conclusions-abstract.tex']


def read(n):
    return open(os.path.join(D, n), encoding='utf-8').read()


def strip_comments(t):
    lines = []
    for ln in t.split('\n'):
        out, i = [], 0
        while i < len(ln):
            c = ln[i]
            if c == '\\':
                out.append(ln[i:i + 2]); i += 2; continue
            if c == '%':
                break
            out.append(c); i += 1
        lines.append(''.join(out))
    return '\n'.join(lines)


# ---------------------------------------------------------------- 05 split
t05 = read('05-conclusions-abstract.tex')
i_abs = t05.index('%% ===========================================================================\n\\section{Abstract and Keywords}')
concl = t05[:i_abs].rstrip() + '\n'
tail = t05[i_abs:]
abs_txt = tail[tail.index('\\subsection{Abstract}') + len('\\subsection{Abstract}'):
               tail.index('\\subsection{Keywords}')].strip()
kw_txt = tail[tail.index('\\subsection{Keywords}') + len('\\subsection{Keywords}'):]
kw_txt = kw_txt[:kw_txt.index('%% ==========')].strip()
tail_comments = tail[tail.index('%% ===========================================================================\n%% NEW REFERENCES NEEDED'):]

bodies = [read(SEC[0]), read(SEC[1]), read(SEC[2]), read(SEC[3]), concl]

# ---------------------------------------------------------------- bibliography
ENTRIES = {
'katzin2020': r"""Katzin, D.; van Mourik, S.; Kempkes, F.; van Henten, E.J. GreenLight---An open source
model for greenhouses with supplemental lighting: Evaluation of heat requirements under LED
and HPS lamps. \textit{Biosyst. Eng.} \textbf{2020}, \textit{194}, 61--81.
\url{https://doi.org/10.1016/j.biosystemseng.2020.03.010}""",
'katzin2021': r"""Katzin, D.; Marcelis, L.F.M.; van Mourik, S. Energy savings in greenhouses by transition
from high-pressure sodium to LED lighting. \textit{Appl. Energy} \textbf{2021},
\textit{281}, 116019. \url{https://doi.org/10.1016/j.apenergy.2020.116019}""",
'vanhenten1994': r"""van Henten, E.J. Greenhouse Climate Management: An Optimal Control Approach. Ph.D. Thesis,
Wageningen University, Wageningen, The Netherlands, 1994.
\url{https://doi.org/10.18174/205106}""",
'mayne2000': r"""Mayne, D.Q.; Rawlings, J.B.; Rao, C.V.; Scokaert, P.O.M. Constrained model predictive
control: Stability and optimality. \textit{Automatica} \textbf{2000}, \textit{36}, 789--814.
\url{https://doi.org/10.1016/S0005-1098(99)00214-9}""",
'rawlings2012': r"""Rawlings, J.B.; Angeli, D.; Bates, C.N. Fundamentals of economic model predictive control.
In Proceedings of the 51st IEEE Conference on Decision and Control (CDC), Maui, HI, USA,
10--13 December 2012; pp. 3851--3861. \url{https://doi.org/10.1109/CDC.2012.6425822}""",
'lin2021': r"""Lin, D.; Zhang, L.; Xia, X. Model predictive control of a Venlo-type greenhouse system
considering electrical energy, water and carbon dioxide consumption. \textit{Appl. Energy}
\textbf{2021}, \textit{298}, 117163. \url{https://doi.org/10.1016/j.apenergy.2021.117163}""",
'brunton2016': r"""Brunton, S.L.; Proctor, J.L.; Kutz, J.N. Discovering governing equations from data by sparse
identification of nonlinear dynamical systems. \textit{Proc. Natl. Acad. Sci. USA}
\textbf{2016}, \textit{113}, 3932--3937. \url{https://doi.org/10.1073/pnas.1517384113}""",
'brunton2016c': r"""Brunton, S.L.; Proctor, J.L.; Kutz, J.N. Sparse identification of nonlinear dynamics with
control (SINDYc). \textit{IFAC-PapersOnLine} \textbf{2016}, \textit{49}, 710--715.
\url{https://doi.org/10.1016/j.ifacol.2016.10.249}""",
'kaiser2018': r"""Kaiser, E.; Kutz, J.N.; Brunton, S.L. Sparse identification of nonlinear dynamics for model
predictive control in the low-data limit. \textit{Proc. R. Soc. A} \textbf{2018},
\textit{474}, 20180335. \url{https://doi.org/10.1098/rspa.2018.0335}""",
'fasel2022': r"""Fasel, U.; Kutz, J.N.; Brunton, B.W.; Brunton, S.L. Ensemble-SINDy: Robust sparse model
discovery in the low-data, high-noise limit, with active learning and control.
\textit{Proc. R. Soc. A} \textbf{2022}, \textit{478}, 20210904.
\url{https://doi.org/10.1098/rspa.2021.0904}""",
'morcego2023': r"""Morcego, B.; Yin, W.; Boersma, S.; van Henten, E.J.; Puig, V.; Sun, C. Reinforcement learning
versus model predictive control on greenhouse climate control. \textit{Comput. Electron.
Agric.} \textbf{2023}, \textit{215}, 108372.
\url{https://doi.org/10.1016/j.compag.2023.108372}""",
'mallick2025': r"""Mallick, S.; Airaldi, F.; Dabiri, A.; Sun, C.; De Schutter, B. Reinforcement learning-based
model predictive control for greenhouse climate control. \textit{Smart Agric. Technol.}
\textbf{2025}, \textit{10}, 100751. \url{https://doi.org/10.1016/j.atech.2024.100751}""",
'vanlaatum2025': r"""van Laatum, B.; van Henten, E.J.; Boersma, S. GreenLight-Gym: Reinforcement learning
benchmark environment for control of greenhouse production systems.
\textit{IFAC-PapersOnLine} \textbf{2025}, \textit{59}, 437--442.
\url{https://doi.org/10.1016/j.ifacol.2025.11.827}""",
'yonezawa2026': r"""Yonezawa, A.; Yonezawa, H.; Yahagi, S.; Kajiwara, I.; Kijimoto, S.; Taniuchi, H.;
Murakami, K. Sparse identification of nonlinear dynamics with library optimization mechanism:
Recursive long-term prediction perspective. \textit{IEEE Trans. Cybern.} \textbf{2026},
\textit{56}, 2475--2488. \url{https://doi.org/10.1109/TCYB.2026.3652850}""",
'ljung1999': r"""Ljung, L. \textit{System Identification: Theory for the User}, 2nd ed.; Prentice Hall:
Upper Saddle River, NJ, USA, 1999.""",
'gevers1993': r"""Gevers, M. Towards a joint design of identification and control? In \textit{Essays on
Control: Perspectives in the Theory and its Applications}; Birkh\"auser: Boston, MA, USA,
1993; pp. 111--151. \url{https://doi.org/10.1007/978-1-4612-0313-1_5}""",
'vandenhof1995': r"""Van den Hof, P.M.J.; Schrama, R.J.P. Identification and control---Closed-loop issues.
\textit{Automatica} \textbf{1995}, \textit{31}, 1751--1770.
\url{https://doi.org/10.1016/0005-1098(95)00094-X}""",
'hjalmarsson2005': r"""Hjalmarsson, H. From experiment design to closed-loop control. \textit{Automatica}
\textbf{2005}, \textit{41}, 393--438.
\url{https://doi.org/10.1016/j.automatica.2004.11.021}""",
'lambert2020': r"""Lambert, N.; Amos, B.; Yadan, O.; Calandra, R. Objective mismatch in model-based
reinforcement learning. \textit{Proc. Mach. Learn. Res. (L4DC)} \textbf{2020}, \textit{120},
761--770.""",
'jackson2022': r"""Jackson, B.E.; Lee, J.H.; Tracy, K.; Manchester, Z. Data-efficient model learning for
control with Jacobian-regularized dynamic-mode decomposition.
\textit{Proc. Mach. Learn. Res. (CoRL)} \textbf{2022}, \textit{205}, 2273--2283.""",
'farahmand2017': r"""Farahmand, A.-m.; Barreto, A.; Nikovski, D. Value-aware loss function for model-based
reinforcement learning. \textit{Proc. Mach. Learn. Res. (AISTATS)} \textbf{2017},
\textit{54}, 1486--1494.""",
'wei2024': r"""Wei, R.; Lambert, N.; McDonald, A.; Garcia, A.; Calandra, R. A unified view on solving
objective mismatch in model-based reinforcement learning. \textit{Trans. Mach. Learn. Res.}
\textbf{2024}.""",
'controlorientedsurvey2025': r"""Sivaranjani, S.; Shi, Y.; Atanasov, N.; Duong, T.; Feng, J.; Martin, T.; Xu, Y.; Gupta, V.;
Allg\"ower, F. Control-oriented system identification: Classical, learning, and
physics-informed approaches. \textit{arXiv} \textbf{2025}, arXiv:2512.06315; accepted for
publication in \textit{Annu. Rev. Control}""",
'raissi2019': r"""Raissi, M.; Perdikaris, P.; Karniadakis, G.E. Physics-informed neural networks: A deep
learning framework for solving forward and inverse problems involving nonlinear partial
differential equations. \textit{J. Comput. Phys.} \textbf{2019}, \textit{378}, 686--707.
\url{https://doi.org/10.1016/j.jcp.2018.10.045}""",
'karniadakis2021': r"""Karniadakis, G.E.; Kevrekidis, I.G.; Lu, L.; Perdikaris, P.; Wang, S.; Yang, L.
Physics-informed machine learning. \textit{Nat. Rev. Phys.} \textbf{2021}, \textit{3},
422--440. \url{https://doi.org/10.1038/s42254-021-00314-5}""",
'cortiella2021': r"""Cortiella, A.; Park, K.-C.; Doostan, A. Sparse identification of nonlinear dynamical systems
via reweighted $\ell_1$-regularized least squares. \textit{Comput. Methods Appl. Mech. Eng.}
\textbf{2021}, \textit{376}, 113620. \url{https://doi.org/10.1016/j.cma.2020.113620}""",
'balanceguided2026': r"""Dang, Z.; Zhang, L.; Wang, L.; He, G. Balance-guided sparse identification of multiscale
nonlinear PDEs with small-coefficient terms. \textit{arXiv} \textbf{2026}, arXiv:2604.18414.""",
'belsley1980': r"""Belsley, D.A.; Kuh, E.; Welsch, R.E. \textit{Regression Diagnostics: Identifying Influential
Data and Sources of Collinearity}; Wiley: New York, NY, USA, 1980.
\url{https://doi.org/10.1002/0471725153}""",
'schulman2017': r"""Schulman, J.; Wolski, F.; Dhariwal, P.; Radford, A.; Klimov, O. Proximal policy optimization
algorithms. \textit{arXiv} \textbf{2017}, arXiv:1707.06347.""",
'haarnoja2018': r"""Haarnoja, T.; Zhou, A.; Abbeel, P.; Levine, S. Soft actor-critic: Off-policy maximum entropy
deep reinforcement learning with a stochastic actor. \textit{Proc. Mach. Learn. Res. (ICML)}
\textbf{2018}, \textit{80}, 1861--1870.""",
'raffin2021': r"""Raffin, A.; Hill, A.; Gleave, A.; Kanervisto, A.; Ernestus, M.; Dormann, N.
Stable-Baselines3: Reliable reinforcement learning implementations. \textit{J. Mach. Learn.
Res.} \textbf{2021}, \textit{22}, 1--8, article 268.""",
'henderson2018': r"""Henderson, P.; Islam, R.; Bachman, P.; Pineau, J.; Precup, D.; Meger, D. Deep reinforcement
learning that matters. In Proceedings of the 32nd AAAI Conference on Artificial Intelligence
(AAAI-18), New Orleans, LA, USA, 2--7 February 2018; pp. 3207--3214.
\url{https://doi.org/10.1609/aaai.v32i1.11694}""",
'ross2011': r"""Ross, S.; Gordon, G.J.; Bagnell, J.A. A reduction of imitation learning and structured
prediction to no-regret online learning. \textit{Proc. Mach. Learn. Res. (AISTATS)}
\textbf{2011}, \textit{15}, 627--635.""",
'wilcoxon1945': r"""Wilcoxon, F. Individual comparisons by ranking methods. \textit{Biom. Bull.} \textbf{1945},
\textit{1}, 80--83. \url{https://doi.org/10.2307/3001968}""",
'holm1979': r"""Holm, S. A simple sequentially rejective multiple test procedure. \textit{Scand. J. Stat.}
\textbf{1979}, \textit{6}, 65--70.""",
'demsar2006': r"""Dem\v{s}ar, J. Statistical comparisons of classifiers over multiple data sets.
\textit{J. Mach. Learn. Res.} \textbf{2006}, \textit{7}, 1--30.""",
'efron1994': r"""Efron, B.; Tibshirani, R.J. \textit{An Introduction to the Bootstrap}; Chapman \& Hall/CRC:
New York, NY, USA, 1994. \url{https://doi.org/10.1201/9780429246593}""",
'mahalanobis1936': r"""Mahalanobis, P.C. On the generalised distance in statistics. \textit{Proc. Natl. Inst. Sci.
India} \textbf{1936}, \textit{2}, 49--55.""",
'lee2018': r"""Lee, K.; Lee, K.; Lee, H.; Shin, J. A simple unified framework for detecting
out-of-distribution samples and adversarial attacks. In Proceedings of the 32nd International
Conference on Neural Information Processing Systems (NeurIPS), Montr\'eal, QC, Canada,
3--8 December 2018; pp. 7167--7177.""",
'lakshminarayanan2017': r"""Lakshminarayanan, B.; Pritzel, A.; Blundell, C. Simple and scalable predictive uncertainty
estimation using deep ensembles. In Proceedings of the 31st International Conference on
Neural Information Processing Systems (NIPS), Long Beach, CA, USA, 4--9 December 2017;
pp. 6402--6413.""",
'hersbach2020': r"""Hersbach, H.; Bell, B.; Berrisford, P.; Hirahara, S.; Hor\'anyi, A.; Mu\~noz-Sabater, J.;
Nicolas, J.; Peubey, C.; Radu, R.; Schepers, D.; et al. The ERA5 global reanalysis.
\textit{Q. J. R. Meteorol. Soc.} \textbf{2020}, \textit{146}, 1999--2049.
\url{https://doi.org/10.1002/qj.3803}""",
'openmeteo2023': r"""Zippenfenig, P. Open-Meteo.com Weather API, 2023; Zenodo.
\url{https://doi.org/10.5281/zenodo.7970649}. Historical archive endpoint available online:
\url{https://archive-api.open-meteo.com/v1/archive} (accessed on 11 August 2026).""",
'wachter2006': r"""W\"achter, A.; Biegler, L.T. On the implementation of an interior-point filter line-search
algorithm for large-scale nonlinear programming. \textit{Math. Program.} \textbf{2006},
\textit{106}, 25--57. \url{https://doi.org/10.1007/s10107-004-0559-y}""",
'fiedler2023': r"""Fiedler, F.; Karg, B.; L\"uken, L.; Brandner, D.; Heinlein, M.; Brabender, F.; Lucia, S.
do-mpc: Towards FAIR nonlinear and robust model predictive control. \textit{Control Eng.
Pract.} \textbf{2023}, \textit{140}, 105676.
\url{https://doi.org/10.1016/j.conengprac.2023.105676}""",
}

# Entries that were absent from paper/statya_ru.tex and had to be written from the notes
# in the section files.  ALL of them -- and the other 33 as well -- were checked against
# Crossref, arXiv, PMLR, dblp or the publisher's own record on 2026-08-14; the marker below
# now records that check rather than requesting one.
NEW_KEYS = {'vanhenten1994', 'rawlings2012', 'raissi2019', 'karniadakis2021', 'belsley1980',
            'hjalmarsson2005', 'hersbach2020', 'openmeteo2023', 'wachter2006', 'fiedler2023',
            'ross2011'}

# first-citation order over the assembled body (abstract first, then sections)
order, seen = [], set()
scan_stream = strip_comments(abs_txt) + '\n' + '\n'.join(strip_comments(b) for b in bodies)
for m in re.finditer(r'\\cite\{([^}]*)\}', scan_stream):
    for k in m.group(1).split(','):
        k = k.strip()
        if k and k not in seen:
            seen.add(k); order.append(k)

missing = [k for k in order if k not in ENTRIES]
assert not missing, 'no bibitem text for: %s' % missing
unused = [k for k in ENTRIES if k not in seen]

bib = ['\\begin{thebibliography}{99}', '\\small', '']
for k in order:
    if k in NEW_KEYS:
        bib.append('%% NEW ENTRY (absent from statya_ru.tex) -- verified against the '
                   'publisher record 2026-08-14')
    bib.append('\\bibitem{%s}' % k)
    bib.append(ENTRIES[k])
    bib.append('')
bib.append('\\end{thebibliography}')
bib = '\n'.join(bib)

PREAMBLE = r"""%% ============================================================================
%% paper_en.tex -- control-oriented model selection for economic greenhouse
%% climate MPC.  English manuscript for MDPI Agronomy.
%%
%% ASSEMBLED FILE.  Body text is the concatenation of the five verified sections
%% in own-article/paper/en/:
%%     01-introduction.tex  02-methods.tex  03-results.tex
%%     04-discussion.tex    05-conclusions-abstract.tex
%% The Abstract and Keywords of section 05 have been moved into the front matter
%% here; everything else is verbatim, including the provenance comments, which
%% are retained deliberately -- every number in this manuscript is traceable to a
%% CSV under own-article/regen/results/ and the comment beside it names the file.
%%
%% Regenerate with the assembly script rather than editing this file directly:
%% edits made here will be lost the next time the sections are re-assembled.
%%
%% TARGET JOURNAL NOTE: MDPI journals use their own class (mdpi.cls) in which
%% the abstract and keywords belong to the front matter and the bibliography is
%% produced from a .bib file.  This file uses the standard article class so that
%% it compiles anywhere; the front matter below maps one-to-one onto the MDPI
%% \begin{abstract} / \begin{keyword} blocks.
%% ============================================================================
\documentclass[11pt,a4paper]{article}

\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[english]{babel}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{array}
\usepackage{caption}
\usepackage{xcolor}
\usepackage[margin=2.5cm]{geometry}
\usepackage{url}
\usepackage[hidelinks]{hyperref}

\graphicspath{{figures/}{./}}
\setlength{\parskip}{0.2\baselineskip}
\captionsetup{font=small,labelfont=bf}

%% ===========================================================================
%% TITLE.  Reframed 2026-08-14.  Two earlier titles are RETRACTED and must not
%% come back:
%%   "Ill-Conditioning, Not Sparsity: ..."  (OUTLINE_v2.md) -- the conditioning
%%      mechanism it names is refuted; kappa 8.21/24.52/53.43 is monotone but
%%      closed-loop EPI +4.32/+0.28/+2.75 is not.
%%   "... one-step accuracy and multi-step stability disagree" -- true but it
%%      states only the screening result and none of the mechanism.
%% The title below carries the three things the evidence supports: the selection
%% rule (multi-step stability), the explanation (survival of the actuator term
%% through the sparsity threshold), and the shape of the physics effect
%% (non-monotone, not "more physics is worse").  Sources: phys_lib/,
%% priced_main/, ladder_rerun/, priced_mech/ under own-article/regen/results/.
%% ===========================================================================
\title{Multi-step stability selects, actuator-term survival explains:
physics-informed features have a non-monotone effect on sparse surrogate models
for economic greenhouse climate control}

%% ===========================================================================
%% AUTHOR BLOCK -- PLACEHOLDER.  NOTHING HERE IS A REAL NAME.
%%
%% This block is deliberately unfillable-looking.  No author name, initials,
%% affiliation, e-mail address or ORCID iD has been invented, guessed or
%% inferred anywhere in this manuscript or in its back matter, because a
%% fabricated authorship line on a real submission is misconduct, not a
%% formatting placeholder.  The manuscript will not compile into a submittable
%% PDF until a human supplies the following, and it is meant not to.
%%
%% MUST BE SUPPLIED BY THE AUTHORS BEFORE SUBMISSION
%%   1. Full name of every author, in the intended author order, spelled as it
%%      should appear in the citation (MDPI style: Given-name Family-name).
%%   2. An ORCID iD for every author who has one; MDPI displays them and
%%      requires one for the corresponding author.
%%   3. The full postal affiliation of every author: department, institution,
%%      street address, postcode, city, country.  One numbered affiliation per
%%      distinct institution; superscripts on the names must match.
%%   4. Which author is the corresponding author, and that author's
%%      institutional e-mail address.
%%   5. The e-mail address of every co-author (MDPI prints them in the
%%      affiliation footnotes).
%%   6. The CRediT contribution of each author, by initials, for the Author
%%      Contributions statement in the back matter below -- see the list of
%%      the fourteen CRediT roles there.
%%   7. A funding statement, including grant numbers, or the explicit
%%      declaration that there was no external funding.
%%   8. A conflict-of-interest declaration from every author.
%%
%% Items 6-8 are back-matter statements and are stubbed at the end of this
%% file, immediately before the bibliography.
%% ===========================================================================
\author{%
  \textbf{[[AUTHOR 1 -- FULL NAME REQUIRED]]}$^{1,}$%
  \thanks{Correspondence: \texttt{[[CORRESPONDING AUTHOR E-MAIL REQUIRED]]}}
  \ \textsuperscript{\textcolor{red}{[[ORCID REQUIRED]]}}
  \and \textbf{[[AUTHOR 2 -- FULL NAME REQUIRED]]}$^{2}$
  \ \textsuperscript{\textcolor{red}{[[ORCID REQUIRED]]}}
  \and \textbf{[[ADD OR DELETE AUTHORS AS REQUIRED]]} \\[4pt]
  \small $^{1}$[[AFFILIATION 1 REQUIRED: DEPARTMENT, INSTITUTION, STREET,
  POSTCODE, CITY, COUNTRY; E-MAIL]] \\
  \small $^{2}$[[AFFILIATION 2 REQUIRED, OR DELETE IF ALL AUTHORS SHARE
  AFFILIATION 1]]
}
\date{}

\begin{document}
\maketitle

%% ---------------------------------------------------------------------------
%% FRONT MATTER.  Moved here from 05-conclusions-abstract.tex, where it was
%% drafted and verified alongside the Conclusions.
\begin{abstract}
@@ABSTRACT@@
\end{abstract}

\noindent\textbf{Keywords:} @@KEYWORDS@@

\vspace{1\baselineskip}
"""

BACKMATTER = r"""
%% ============================================================================
%% MDPI BACK MATTER
%%
%% MDPI requires these statements between the Conclusions and the References,
%% in this order.  Under mdpi.cls each is produced by a macro
%% (\authorcontributions{}, \funding{}, \dataavailability{},
%% \conflictsofinterest{}); under the standard article class used here they are
%% typeset as an unnumbered block.  MDPI_SUBMISSION.md records the exact
%% substitutions.
%%
%% THREE OF THE FIVE ARE PLACEHOLDERS AND MUST BE COMPLETED BY THE AUTHORS.
%% They are not filled in here because no author identity exists in this
%% repository and inventing one would be fabrication.  The Institutional Review
%% Board / Informed Consent statements and the Data Availability statement are
%% REAL: the first two because this is a simulation study with no human or
%% animal subjects, and the third because the replication tree exists and is
%% described exactly as it is.
%% ============================================================================
\vspace{1\baselineskip}
\noindent\rule{\textwidth}{0.4pt}
\small

\noindent\textbf{Author Contributions:}
\textcolor{red}{[[REQUIRED --- NOT SUPPLIED.]]} State each author's contribution
by initials using the CRediT taxonomy, e.g.\ ``Conceptualization, X.X. and Y.Y.;
methodology, X.X.; software, X.X.; validation, X.X., Y.Y. and Z.Z.; formal
analysis, X.X.; investigation, X.X.; resources, X.X.; data curation, X.X.;
writing---original draft preparation, X.X.; writing---review and editing, X.X.;
visualization, X.X.; supervision, X.X.; project administration, X.X.; funding
acquisition, Y.Y. All authors have read and agreed to the published version of
the manuscript.'' Initials must match the author block above, and every listed
author must appear in at least one role.

\noindent\textbf{Funding:}
\textcolor{red}{[[REQUIRED --- NOT SUPPLIED.]]} Either name every funder with the
grant number in MDPI's form (``This research was funded by NAME OF FUNDER, grant
number XXX'') or state exactly ``This research received no external funding''.
Do not leave this blank: MDPI will not send the manuscript out for review
without it.

\noindent\textbf{Institutional Review Board Statement:} Not applicable. This
study is a computational study of a greenhouse climate simulator and involves
neither humans nor animals.

\noindent\textbf{Informed Consent Statement:} Not applicable.

\noindent\textbf{Data Availability Statement:}
All quantities reported in this article are computed from the per-run result
tables of the study's regeneration tree (\texttt{own-article/regen/results/} in
the project repository), which contains one row per (controller, seed, test
season) together with the seasonal margin, constraint-violation counts, solver
diagnostics and the identified sparse coefficients. Every wave reported here was
produced under a single frozen configuration whose hash,
\texttt{637c6b535a9e}, is written into every result row and into the
\texttt{regen\_manifest.json} of each wave alongside the git commit of the code
that generated it; the manifest also records the seeds, test years, horizon,
solver-failure budget, season length and the four identification recipes, so a
wave can be identified without reference to this text. The experiments are
regenerated with the single driver in \texttt{own-article/regen/}: each of the
eight experiment blocks is run as \texttt{python run\_regen.py --experiment
<block> --seeds <list> --out <dir>}, after which \texttt{python run\_regen.py
--merge --out <dir>} and \texttt{python make\_tables.py --out <dir>} rebuild
every derived table together with \texttt{NUMBERS.md}, a claim-to-value-to-source
map that names the file and column behind each reported quantity. \texttt{python
verify\_regen.py} then applies the acceptance gates---mixed configuration hash,
an incomplete or duplicated run grid, truncated seasons, non-uniform horizon or
solver budget, a missing sparse coefficient column, an unresolved sparsity
region or an incomplete ablation block---and exits non-zero if any fails.
Determinism is checked separately by \texttt{python repro.py --selftest}, which
executes the pipeline twice under identical seeds and compares SHA-256 digests of
the training states and actions, the ensemble and STLSQ coefficient matrices, the
neural-network weights, and the closed-loop trajectory and margin; all seven
digests agree on the pinned stack, and all nine with the two reinforcement-learning
policies included. Reproduction additionally requires the GreenLight tomato
greenhouse model as packaged in \texttt{gl\_gym}~0.3.1 \cite{katzin2020,vanlaatum2025}
and the ERA5-derived weather described in Section~\ref{sec:sim}, retrieved
from the Open-Meteo historical archive API \cite{hersbach2020,openmeteo2023}. As
Section~\ref{sec:repro} states, bit-level reproduction is established within one
computing environment; the cross-environment case was not measured, and closed-loop
margins should not be expected to match to the last decimal on a different stack.
\textcolor{red}{[[REQUIRED BEFORE SUBMISSION: a public, citable location for this
tree --- a repository URL and an archived release with a DOI (Zenodo, figshare or
equivalent). MDPI requires a link or an explicit statement of restriction; a path
inside a private repository is not sufficient.]]}

\noindent\textbf{Conflicts of Interest:}
\textcolor{red}{[[REQUIRED --- NOT SUPPLIED.]]} Every author must declare. Use
``The authors declare no conflicts of interest.'' only if that is true of all of
them; otherwise describe the interest and state the funders' role, or lack of
role, in the design of the study, in the collection, analyses or interpretation
of data, in the writing of the manuscript, and in the decision to publish the
results.

\normalsize
\vspace{0.5\baselineskip}
"""

FOOTER = r"""
%% ============================================================================
%% BIBLIOGRAPHY
%%
%% ALL 44 ENTRIES VERIFIED 2026-08-14 against Crossref, arXiv, PMLR, dblp or the
%% publisher's own landing page.  Entries carried over from paper/statya_ru.tex
%% were reformatted from the Russian (GOST-style) layout into MDPI
%% author-year-volume style; those marked "NEW ENTRY" were written for this
%% manuscript and have now been checked as well.
%%
%% RULE APPLIED TO DOIs: a DOI appears only where it was resolved successfully
%% against the registry.  Nothing was reconstructed by pattern.  Four entries
%% therefore carry NO DOI, deliberately:
%%   holm1979              -- Scand. J. Stat. 6, 65-70 has no registered DOI that
%%                            resolves (the JSTOR stable id is not one).
%%   mahalanobis1936       -- the 1936 original is not registered; only the 2018
%%                            Sankhya A reprint is, and that is a different item.
%%   lambert2020, jackson2022, farahmand2017, haarnoja2018, ross2011,
%%   demsar2006, raffin2021, lee2018, lakshminarayanan2017
%%                         -- PMLR, JMLR and the NeurIPS/NIPS proceedings do not
%%                            mint DOIs for these volumes.  Volume and page
%%                            numbers were verified against proceedings.mlr.press,
%%                            jmlr.org and dblp instead.
%%   schulman2017, balanceguided2026, controlorientedsurvey2025
%%                         -- cited as preprints; the arXiv identifier is the
%%                            locator and no journal version exists (or, for the
%%                            survey, none with a volume yet).
%%
%% FOUR KEYS WERE RENAMED so that each key's year matches the version of record
%% now cited (the old keys are dead; do not reintroduce them):
%%   ljung1991     -> ljung1999      2nd English edition, Prentice Hall 1999,
%%                                   not the Russian translation of 1991 that the
%%                                   superseded manuscript cited.
%%   mallick2024   -> mallick2025    the arXiv preprint appeared in Smart Agric.
%%                                   Technol. 2025, 10, 100751.
%%   wei2023       -> wei2024        published in Trans. Mach. Learn. Res. 2024.
%%   yonezawa2025  -> yonezawa2026   published in IEEE Trans. Cybern. 2026, 56,
%%                                   2475-2488.
%%
%% ONE CORRECTION OF SUBSTANCE: `lin2021' had the wrong title.  The paper is
%% "... considering electrical energy, WATER AND CARBON DIOXIDE consumption";
%% the draft dropped the carbon dioxide.
%%
%% `hersbach2020' has 43 authors.  The first ten followed by "et al." is the
%% form MDPI's reference guide prescribes for more than ten authors, so the
%% list is correct as written and must not be "completed".
%% `fiedler2023' carries its FULL seven-author list already; the ";et al." that
%% an earlier register reported for it is not present.
%%
%% `ross2011' exists in paper/build_ru/references.bib under the key
%% `ross2011dagger'; if the submission moves to BibTeX, re-key rather than adding
%% a duplicate.  It is cited here in exactly one place, in
%% Section~\ref{sec:res-safety}, SOLELY to disclaim the DAgger label for the
%% on-policy re-identification loop.  It is not an attribution.
%% ============================================================================
"""


def main():
    head = PREAMBLE.replace('@@ABSTRACT@@', abs_txt).replace('@@KEYWORDS@@', kw_txt)
    parts = [head]
    for b in bodies:
        parts.append('\n')
        parts.append(b.rstrip())
        parts.append('\n')
    parts.append('\n' + BACKMATTER)
    parts.append('\n' + tail_comments.rstrip() + '\n')
    parts.append(FOOTER)
    parts.append(bib)
    parts.append('\n\n\\end{document}\n')
    txt = ''.join(parts)
    with io.open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write(txt)
    print('wrote', OUT, len(txt), 'chars')
    print('bibitems:', len(order))
    print('unused entries defined but never cited:', unused)


main()
