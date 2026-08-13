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
and HPS lamps. \textit{Biosyst. Eng.} \textbf{2020}, \textit{194}, 61--81.""",
'katzin2021': r"""Katzin, D.; Marcelis, L.F.M.; van Mourik, S. Energy savings in greenhouses by transition
from high-pressure sodium to LED lighting. \textit{Appl. Energy} \textbf{2021},
\textit{281}, 116019.""",
'vanhenten1994': r"""van Henten, E.J. Greenhouse Climate Management: An Optimal Control Approach. Ph.D. Thesis,
Wageningen University, Wageningen, The Netherlands, 1994.""",
'mayne2000': r"""Mayne, D.Q.; Rawlings, J.B.; Rao, C.V.; Scokaert, P.O.M. Constrained model predictive
control: Stability and optimality. \textit{Automatica} \textbf{2000}, \textit{36}, 789--814.""",
'rawlings2012': r"""Rawlings, J.B.; Angeli, D.; Bates, C.N. Fundamentals of economic model predictive control.
In Proceedings of the 51st IEEE Conference on Decision and Control (CDC), 2012;
pp. 3851--3861.""",
'lin2021': r"""Lin, D.; Zhang, L.; Xia, X. Model predictive control of a Venlo-type greenhouse system
considering electrical energy and water consumption. \textit{Appl. Energy} \textbf{2021},
\textit{298}, 117163.""",
'brunton2016': r"""Brunton, S.L.; Proctor, J.L.; Kutz, J.N. Discovering governing equations from data by sparse
identification of nonlinear dynamical systems. \textit{Proc. Natl. Acad. Sci. USA}
\textbf{2016}, \textit{113}, 3932--3937.""",
'brunton2016c': r"""Brunton, S.L.; Proctor, J.L.; Kutz, J.N. Sparse identification of nonlinear dynamics with
control (SINDYc). \textit{IFAC-PapersOnLine} \textbf{2016}, \textit{49}, 710--715.""",
'kaiser2018': r"""Kaiser, E.; Kutz, J.N.; Brunton, S.L. Sparse identification of nonlinear dynamics for model
predictive control in the low-data limit. \textit{Proc. R. Soc. A} \textbf{2018},
\textit{474}, 20180335.""",
'fasel2022': r"""Fasel, U.; Kutz, J.N.; Brunton, B.W.; Brunton, S.L. Ensemble-SINDy: Robust sparse model
discovery in the low-data, high-noise limit, with active learning and control.
\textit{Proc. R. Soc. A} \textbf{2022}, \textit{478}, 20210904.""",
'morcego2023': r"""Morcego, B.; Yin, W.; Boersma, S.; van Henten, E.; Puig, V.; Sun, C. Reinforcement learning
versus model predictive control on greenhouse climate control. \textit{Comput. Electron.
Agric.} \textbf{2023}, \textit{215}, 108372.""",
'mallick2024': r"""Mallick, S.; Airaldi, F.; Dabiri, A.; Sun, C.; De Schutter, B. Reinforcement learning-based
model predictive control for greenhouse climate control. \textit{arXiv} \textbf{2024},
arXiv:2409.12789.""",
'vanlaatum2025': r"""van Laatum, B.; van Henten, E.J.; Boersma, S. GreenLight-Gym: A reinforcement learning
benchmark environment for control of greenhouse production systems. \textit{arXiv}
\textbf{2025}, arXiv:2410.05336.""",
'yonezawa2025': r"""Yonezawa, A.; Yonezawa, H.; Yahagi, S.; Kajiwara, I.; Kijimoto, S.; Taniuchi, H.;
Murakami, K. Sparse identification of nonlinear dynamics with library optimization mechanism:
Recursive long-term prediction perspective. \textit{arXiv} \textbf{2025}, arXiv:2507.18220.""",
'ljung1991': r"""Ljung, L. \textit{System Identification: Theory for the User}, 2nd ed.; Prentice Hall:
Upper Saddle River, NJ, USA, 1999.""",
'gevers1993': r"""Gevers, M. Towards a joint design of identification and control? In \textit{Essays on
Control: Perspectives in the Theory and its Applications}; Birkh\"auser: Boston, MA, USA,
1993; pp. 111--151.""",
'vandenhof1995': r"""Van den Hof, P.M.J.; Schrama, R.J.P. Identification and control---Closed-loop issues.
\textit{Automatica} \textbf{1995}, \textit{31}, 1751--1770.""",
'hjalmarsson2005': r"""Hjalmarsson, H. From experiment design to closed-loop control. \textit{Automatica}
\textbf{2005}, \textit{41}, 393--438.""",
'lambert2020': r"""Lambert, N.; Amos, B.; Yadan, O.; Calandra, R. Objective mismatch in model-based
reinforcement learning. \textit{Proc. Mach. Learn. Res. (L4DC)} \textbf{2020}, \textit{120},
761--770.""",
'jackson2022': r"""Jackson, B.E.; Lee, J.H.; Tracy, K.; Manchester, Z. Data-efficient model learning for
control with Jacobian-regularized dynamic-mode decomposition. \textit{arXiv} \textbf{2022},
arXiv:2212.07885.""",
'farahmand2017': r"""Farahmand, A.-m.; Barreto, A.; Nikovski, D. Value-aware loss function for model-based
reinforcement learning. \textit{Proc. Mach. Learn. Res. (AISTATS)} \textbf{2017},
\textit{54}, 1486--1494.""",
'wei2023': r"""Wei, R.; Lambert, N.; McDonald, A.; Garcia, A.; Calandra, R. A unified view on solving
objective mismatch in model-based reinforcement learning. \textit{Trans. Mach. Learn. Res.}
\textbf{2023}.""",
'controlorientedsurvey2025': r"""Sivaranjani, S.; Shi, Y.; Atanasov, N.; Duong, T.; Feng, J.; Martin, T.; Xu, Y.; Gupta, V.;
Allg\"ower, F. Control-oriented system identification: Classical, learning, and
physics-informed approaches. \textit{arXiv} \textbf{2025}, arXiv:2512.06315.""",
'raissi2019': r"""Raissi, M.; Perdikaris, P.; Karniadakis, G.E. Physics-informed neural networks: A deep
learning framework for solving forward and inverse problems involving nonlinear partial
differential equations. \textit{J. Comput. Phys.} \textbf{2019}, \textit{378}, 686--707.""",
'karniadakis2021': r"""Karniadakis, G.E.; Kevrekidis, I.G.; Lu, L.; Perdikaris, P.; Wang, S.; Yang, L.
Physics-informed machine learning. \textit{Nat. Rev. Phys.} \textbf{2021}, \textit{3},
422--440.""",
'cortiella2021': r"""Cortiella, A.; Park, K.-C.; Doostan, A. Sparse identification of nonlinear dynamical systems
via reweighted $\ell_1$-regularized least squares. \textit{Comput. Methods Appl. Mech. Eng.}
\textbf{2021}, \textit{376}, 113620.""",
'balanceguided2026': r"""Dang, Z.; Zhang, L.; Wang, L.; He, G. Balance-guided sparse identification of multiscale
nonlinear PDEs with small-coefficient terms. \textit{arXiv} \textbf{2026}, arXiv:2604.18414.""",
'belsley1980': r"""Belsley, D.A.; Kuh, E.; Welsch, R.E. \textit{Regression Diagnostics: Identifying Influential
Data and Sources of Collinearity}; Wiley: New York, NY, USA, 1980.""",
'schulman2017': r"""Schulman, J.; Wolski, F.; Dhariwal, P.; Radford, A.; Klimov, O. Proximal policy optimization
algorithms. \textit{arXiv} \textbf{2017}, arXiv:1707.06347.""",
'haarnoja2018': r"""Haarnoja, T.; Zhou, A.; Abbeel, P.; Levine, S. Soft actor-critic: Off-policy maximum entropy
deep reinforcement learning with a stochastic actor. \textit{Proc. Mach. Learn. Res. (ICML)}
\textbf{2018}, \textit{80}, 1861--1870.""",
'raffin2021': r"""Raffin, A.; Hill, A.; Gleave, A.; Kanervisto, A.; Ernestus, M.; Dormann, N.
Stable-Baselines3: Reliable reinforcement learning implementations. \textit{J. Mach. Learn.
Res.} \textbf{2021}, \textit{22}, 1--8.""",
'henderson2018': r"""Henderson, P.; Islam, R.; Bachman, P.; Pineau, J.; Precup, D.; Meger, D. Deep reinforcement
learning that matters. In Proceedings of the 32nd AAAI Conference on Artificial Intelligence,
2018; pp. 3207--3214.""",
'ross2011': r"""Ross, S.; Gordon, G.J.; Bagnell, J.A. A reduction of imitation learning and structured
prediction to no-regret online learning. \textit{Proc. Mach. Learn. Res. (AISTATS)}
\textbf{2011}, \textit{15}, 627--635.""",
'wilcoxon1945': r"""Wilcoxon, F. Individual comparisons by ranking methods. \textit{Biom. Bull.} \textbf{1945},
\textit{1}, 80--83.""",
'holm1979': r"""Holm, S. A simple sequentially rejective multiple test procedure. \textit{Scand. J. Stat.}
\textbf{1979}, \textit{6}, 65--70.""",
'demsar2006': r"""Dem\v{s}ar, J. Statistical comparisons of classifiers over multiple data sets.
\textit{J. Mach. Learn. Res.} \textbf{2006}, \textit{7}, 1--30.""",
'efron1994': r"""Efron, B.; Tibshirani, R.J. \textit{An Introduction to the Bootstrap}; Chapman \& Hall/CRC:
New York, NY, USA, 1994.""",
'mahalanobis1936': r"""Mahalanobis, P.C. On the generalised distance in statistics. \textit{Proc. Natl. Inst. Sci.
India} \textbf{1936}, \textit{2}, 49--55.""",
'lee2018': r"""Lee, K.; Lee, K.; Lee, H.; Shin, J. A simple unified framework for detecting
out-of-distribution samples and adversarial attacks. In \textit{Advances in Neural
Information Processing Systems}; 2018; Volume 31, pp. 7167--7177.""",
'lakshminarayanan2017': r"""Lakshminarayanan, B.; Pritzel, A.; Blundell, C. Simple and scalable predictive uncertainty
estimation using deep ensembles. In \textit{Advances in Neural Information Processing
Systems}; 2017; Volume 30, pp. 6402--6413.""",
'hersbach2020': r"""Hersbach, H.; Bell, B.; Berrisford, P.; Hirahara, S.; Hor\'anyi, A.; Mu\~noz-Sabater, J.;
Nicolas, J.; Peubey, C.; Radu, R.; Schepers, D.; et al. The ERA5 global reanalysis.
\textit{Q. J. R. Meteorol. Soc.} \textbf{2020}, \textit{146}, 1999--2049.""",
'openmeteo2023': r"""Zippenfenig, P. Open-Meteo.com Weather API, 2023. Available online:
\url{https://open-meteo.com} (accessed on [ACCESS DATE NEEDED]).""",
'wachter2006': r"""W\"achter, A.; Biegler, L.T. On the implementation of an interior-point filter line-search
algorithm for large-scale nonlinear programming. \textit{Math. Program.} \textbf{2006},
\textit{106}, 25--57.""",
'fiedler2023': r"""Fiedler, F.; Karg, B.; L\"uken, L.; Brandner, D.; Heinlein, M.; Brabender, F.; Lucia, S.
do-mpc: Towards FAIR nonlinear and robust model predictive control. \textit{Control Eng.
Pract.} \textbf{2023}, \textit{140}, 105676.""",
}

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
        bib.append('%% NEW ENTRY (absent from statya_ru.tex) -- verify against the original')
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
\usepackage[margin=2.5cm]{geometry}
\usepackage{url}
\usepackage[hidelinks]{hyperref}

\graphicspath{{figures/}{./}}
\setlength{\parskip}{0.2\baselineskip}
\captionsetup{font=small,labelfont=bf}

\title{Control-oriented model selection for economic model predictive control of
greenhouse climate: one-step accuracy and multi-step stability disagree}

%% ---------------------------------------------------------------------------
%% AUTHOR BLOCK -- PLACEHOLDER.  Replace before submission; MDPI requires
%% ORCID iDs, affiliation addresses, a corresponding-author e-mail and an
%% author-contributions statement.
\author{%
  [AUTHOR ONE]$^{1,}$\thanks{Correspondence: [CORRESPONDING AUTHOR E-MAIL]}
  \and [AUTHOR TWO]$^{1}$ \\[2pt]
  \small $^{1}$[AFFILIATION, DEPARTMENT, INSTITUTION, CITY, COUNTRY]
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

FOOTER = r"""
%% ============================================================================
%% BIBLIOGRAPHY
%% Entries marked "NEW ENTRY" are not present in paper/statya_ru.tex and were
%% written for this manuscript from the notes left in the section files; check
%% each against the original publication before submission.  Entries carried
%% over from statya_ru.tex have been reformatted from the Russian (GOST-style)
%% layout into MDPI author-date-volume style; the bibliographic content is
%% unchanged.  `ljung1991' deliberately keeps its key while pointing at the
%% ENGLISH 2nd edition (Prentice Hall, 1999) rather than the Russian
%% translation of 1991 that the superseded manuscript cited.
%% `ross2011' exists in paper/build_ru/references.bib under the key
%% `ross2011dagger'; it is cited here in exactly one place, in
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
