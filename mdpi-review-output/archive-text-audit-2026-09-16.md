# Аудит текста депозита `greenhouse-control-regen-data-v1.0.zip` — 2026-09-16

Проверялся архив с хэшем `86f5bed3…` (630 записей): 10 текстовых файлов (md/txt) целиком и
комментарии с докстрингами 24 скриптов (через `tokenize`, код не сканировался). Скрипт
сканирования — `scan_archive.py` в scratchpad сессии: три класса регексов (A — утечка
процесса/агента/приватного, B — регистр ИИ-моделей 2025–26, C — хронологические пометки),
затем ручное чтение заголовков файлов с наибольшим числом попаданий. Ничего в архиве не менялось.

---

## 0. Итог

| | Находка | Серьёзность |
|---|---|---|
| 1 | `regen/results/final/NUMBERS.md` — файл, который README.txt и Data Availability Statement называют «картой утверждений рукописи», содержит 14 строк канонического default-дерева и **противоречит рукописи** по четырём заголовочным пунктам | факт, чинить обязательно |
| 2 | `figures/SPEC.md` — внутренний редакторский документ: 15 ссылок на файлы, которых в архиве нет (`REVISION_LOG`, `REMAINING.md`, `0x-*.tex:строка`), «editorial recommendation», «review comment», «RETRACTION GUARD», даты правок | не для депозита |
| 3 | «pre-registered» / «registered prediction» — 11 мест в коде и SPEC.md; рукопись после C-2 говорит «pre-specified» | расхождение с рукописью по пункту, который рецензия уже поднимала |
| 4 | Докстринги кода написаны в регистре ИИ-ассистента: история дефектов и ревизий (D1–D5, «the 2026-07 state had four runners…», «the first regen got this wrong», `REVISION_LOG G-6`, «reviewer item #1/#6»), моральная лексика (honest ×7, which is the point ×5, genuinely ×2, worth recording/stating ×3), императивы редактору (Do not restore / reintroduce ×7), 52 датированные пометки | самый сильный ИИ-маркер во всём пакете подачи |
| 5 | Приватная инфраструктура: `../greenlight/sindylom/.venv`, `admin-01 Wi-Fi`, `.venv-regen/Scripts/python.exe` | косметика |
| 6 | Чисто: `README.txt`, `LICENSE.txt`, `regen/README.md`, `regen/INSTRUCTIONS.md`, `analysis_notuboil.md`, `requirements-cluster.txt` (кроме двух строк из п. 5) — написаны для депозита, регистр нейтральный | — |

Рукопись после прохода 14.09 чище архива: в ней регистр вычищен, в архиве — нет. Если
рецензент откроет депозит, именно комментарии кода скажут ему, чем писался пакет.

---

## 1. `regen/results/final/NUMBERS.md` противоречит рукописи

Файл генерирует `make_tables.py` из `results/final/` (канонические default-блоки, `git_sha
f8f1aef`). Его строки — не утверждения рукописи:

| Строка NUMBERS.md | Что говорит рукопись |
|---|---|
| Cross-season leader: **ppo +0.45** | лидер — `sindy_mpc_raw_ens` +4.32 (priced-пул) |
| Single-coefficient knock-in effect: **median +3.05**, p = 0.00032, 17/20 | +0.21 (priced); +3.05 — отозванная default-величина, допустимая только рядом с заменой |
| 72 evaluated, **30 pass; frozen recipe … is NOT among them** | 32 из 72 проходят, замороженный рецепт проходит (`ladder_rerun/`) |
| Boiler term survives, sindy_mpc_conf: **12 % of 200 fits** | 15 % (3 из 20 сидов, priced-пул) |
| Draw axis: STLSQ control spread: **nan** | — |

Дисклеймер «This is not the manuscript's claim table» стоит только на
`regen/results_pull/raw/NUMBERS.md`; на `final/NUMBERS.md` его нет, а `README.txt` (строка 11)
и DAS указывают именно на него. Варианты:

- (а) минимальный — добавить в `final/NUMBERS.md` такой же заголовок-дисклеймер и написать в
  README.txt/DAS, что карта утверждений рукописи — её Таблица 16 (headline quantities → файлы);
- (б) правильный — генерировать `final/NUMBERS.md` из проверок `verify_tables.py` /
  `verify_prose.py` (1210 сравнений «значение в рукописи ↔ файл дерева»), для чего
  положить в архив и сами верификаторы; тогда фраза DAS станет буквально верной.

## 2. `figures/SPEC.md` — внутренний документ

Ссылки на отсутствующие в архиве файлы: `REVISION_LOG` (×3), `REMAINING.md §5 item 9`,
`02-methods.tex:58–62`, `02-methods.tex:218`, `03-results.tex:136/167/38/185/425/671`,
`01-introduction.tex:160`, `04-discussion.tex:79/165`, `05-conclusions-abstract.tex:19`.
Плюс «Deviations from the editorial recommendation», «the single most likely … review
comment», «Updated 2026-08-14», «RETRACTION GUARD», «Verified against the tree on 2026-08-13».
Читателю депозита нужны только: номер рисунка → скрипт → исходные CSV и фильтр. Это
50 строк, а не 374. Рекомендация: убрать SPEC.md из `make_archive.FIGURE_FILES`, а нужную
таблицу «рисунок → источник» перенести в `README.txt` или в докстринги `make_figN.py`.

## 3. «pre-registered» в коде (11 мест)

`e3_dagger_compare.py:38`, `protocol_config.py:162`, `regen/regen_config.py:130,132`,
`regen/run_regen.py:147`, `regen/experiments_support.py:59`, `regen/analyze_notuboil.py:9,165,168`
(и порождённый им `analysis_notuboil.md:47` «Verdict against the registered prediction»),
`figures/SPEC.md:133`, `figures/_plotstyle.py:457`. Замена: «pre-specified» / «the
prediction stated in advance» — и перегенерировать `analysis_notuboil.md`.

## 4. Регистр и история процесса в комментариях кода

Что читается как рассказ ассистента о собственной работе (по файлам, строки архива):

| Файл | Где | Что |
|---|---|---|
| `regen/regen_config.py` | 1–30 | «Why this file exists» с реестром дефектов D1–D5 «the 2026-06/07 results were produced by several runners that disagreed…»; 141 `statya_ru.tex:336`; 171 «It is the first thing a reviewer asks about»; 215 «(same computation, honest name)»; 245–260 «The first regen got this wrong and it produced a false alarm worth recording»; 417 «which is the point of a regen»; 446 «Two honest options, both requiring a human decision» |
| `regen/run_regen.py` | 1–5 | «ONE driver produces EVERY number … The 2026-07 state had four runners writing four mutually inconsistent headline tables; this replaces that»; 51 «Coefficient surgery is NOT reimplemented here»; 411 «(reviewer item #6)»; 480 «is exactly what the lambda…» |
| `regen/experiments_support.py` | 51, 331, 555 | «that is the point», «The paper's honest finding here is», «comparison stays honest» |
| `regen/make_tables.py` | 9, 116, 146 | «Statistical choices worth stating, because the 2026-07 analysis got two of them wrong», «genuinely uninformative», «the honest interval» |
| `regen/exp_draws.py` | 1–20 | пересказ отозванной формулировки «+2.43, first in all four seasons» и «-0.12, fourth of ten» |
| `figures/_plotstyle.py` | 4, 120, 188, 398, 432–438, 457, 462, 796, 935, 958, 990 | «The point is that…», `REVISION_LOG G-6` ×3, «is wrong (REVISION_LOG 2026-08-13)», «reports honestly», «label it that way», «a tail, not a shift» |
| `figures/make_fig1…6.py` | заголовки | «RETRACTION GUARD», «SCOPE GUARD», «TWO LABELS THE CAPTION MUST CARRY», «TEST TYPE, which the caption must respect», «the name 04-discussion.tex cites», «genuinely > 4» |
| `run_knockout_ablation.py` | 1, 16 | «(reviewer item #1)», «the reviewer asked for» |
| `regen/analyze_notuboil.py` | 29, 43 | `.venv-regen/Scripts/python.exe own-article/regen/…`, `paper/en/figures` |
| `EXPERIMENT_PROTOCOL.md` | 29, 159 | «honest in silico economic benchmark», «In other words, the price of interpretability is small» — это перевод протокола с его статусными заметками; менять только если менять сам документ |

Счётчики по архиву: honest ×7, genuinely ×2, «the point» ×9, «worth …» ×8, датированные
пометки ×52 (SPEC.md 27, `_plotstyle.py` 10, `make_fig3.py` 7, `regen_config.py` 7,
`run_regen.py` 6), «Do not restore/reintroduce/widen/…» ×7, `REVISION_LOG` ×7,
«reviewer item» ×2, «pre-registered/registered prediction» ×11. «X, not Y» — 32 попадания,
но почти все технические («steps, not seasons») — не трогать.

## 5. Приватная инфраструктура

`requirements-cluster.txt:19` «Verified 2026-07-17 against ../greenlight/sindylom/.venv»,
`:38` «on a host with direct internet (admin-01 Wi-Fi)»; `regen/INSTRUCTIONS.md:28,32`,
`analyze_notuboil.py:29`, `kappa_notuboil.py:10`, `ladder_notuboil.py:11` — пути
`.venv-regen/Scripts/python.exe` (Windows). Безвредно, но выдаёт станцию и сеть.

## 6. Что можно сделать (порядок по важности)

1. NUMBERS.md — вариант (а) за пять минут, вариант (б) за час (верификаторы в архив,
   генератор карты из их результатов).
2. `pre-registered` → `pre-specified` в 11 местах, перегенерировать `analysis_notuboil.md`.
3. SPEC.md — исключить из архива, таблицу «рисунок → источник» перенести в README.txt.
4. Докстринги: убрать `REVISION_LOG`/`REMAINING`/`*.tex:N`/«reviewer item» и датированную
   хронологию из заголовков (D1–D5 → одна фраза «constants that earlier runners left implicit
   are explicit and hashed here»), снять honest/genuinely/the point/worth. Это только
   комментарии — ни один гейт рукописи их не читает, `make_fig*` self-check не зависит.
5. Две строки в `requirements-cluster.txt`, пути `.venv-regen` в трёх докстрингах.
6. Пересобрать архив, новый хэш в `ZENODO.md`.

Пункты 1–2 — до подачи. 3–5 — желательно до подачи, поскольку депозит публикуется вместе
с DOI и его текст читают раньше рукописи.

---

## 7. Применено (2026-09-16, вечер)

Все шесть пунктов §6. Рукопись, `paper_en_mdpi.docx` (`08509bdf…`) и PNG рисунков не
менялись; `config_hash` прежний (`637c6b535a9e`).

| § | Что сделано |
|---|---|
| 1 | `make_tables.py` больше не пишет NUMBERS.md — его 14-строчная сводка default-дерева теперь `tables/SUMMARY.md` (в `results_pull/raw/` файл переименован `git mv`, шапка переписана). `results/final/NUMBERS.md` генерирует новый `paper/en/make_numbers_md.py` из `verify_tables.CHECKS` + `verify_prose.CHECKS`: 800 ячеек таблиц и 410 величин текста, по каждой — пересчитанное значение и файлы-источники (из строк `\source` в tex и из вызовов загрузчиков в чекерах), «Mismatches at generation time: 0». Четыре противоречия §1 исчезли вместе со старым файлом. `README.txt`, `regen/README.md`, `INSTRUCTIONS.md`, `ZENODO.md` — формулировки про NUMBERS/SUMMARY согласованы. |
| 2 | `pre-registered`/`registered prediction` → `pre-specified` во всех 11 местах; `analysis_notuboil.md` перегенерирован. В архиве 0 вхождений. |
| 3 | `figures/SPEC.md` исключён (`FIGURE_FILES`), таблица «рисунок → источники» добавлена в `README.txt`. Дополнительно исключён `regen/CLUSTER_REGEN_PLAN.md` (`SKIP_NAMES` в `make_archive.py`): отложенный план со ссылками на `admin-01`, `192.168.…`, `localhost:5000` и `REMAINING.md` попадал в архив как любой `.md` под `regen/`. |
| 4 | Заголовки и комментарии `regen_config.py` (D1–D5 → одна фраза), `run_regen.py`, `experiments_support.py` (WARNING-блок → нейтральная запись «OBJECTIVE OF THE SUPPORTING BLOCKS»), `exp_draws.py`, `verify_regen.py`, `repro.py`, `analyze_notuboil.py`, `run_knockout_ablation.py`, `article_experiment_utils.py`, `e3_dagger_compare.py`, `_plotstyle.py`, `make_fig1…6.py`: убраны `REVISION_LOG`, `REMAINING.md`, `*.tex:N`, «reviewer item», «RETRACTION GUARD», датированная хронология, honest/genuinely/the point/worth/Do not restore. Все шесть `make_fig*.py` перезапущены — self-check проходит, PNG побайтно те же. |
| 5 | Две строки из `requirements-cluster.txt` удалены; пути `.venv-regen/Scripts/python.exe` в трёх докстрингах → `python …`. |
| 6 | Архив пересобран дважды — хэш одинаков: `89504527cae5c44851a897557b05b6821f1edfcd6ad187ad69dcb31ee6bd070c`, 630 записей, 5.99 MB; записан в `ZENODO.md` с пометкой о причине пересборки. |

Счётчики по итоговому архиву тем же сканером: honest ×1 (перевод протокола, оставлено),
genuinely ×0, «the point» ×2 (оба буквальные: «the point it marks», «past the point where»),
«worth …» ×0, датированные пометки ×3 (дата сценария `2010-02-28`, дата замера
детерминизма RL, фиксированная метка zip), «Do not …» ×1 (`_plotstyle.py`: «sign_pass … was
never evaluated. Do not encode it» — предостережение загрузчика, оставлено), `REVISION_LOG`
×0, `REMAINING.md` ×0, `SPEC.md` ×0, «reviewer item» ×0, `pre-registered` ×0, приватные
хосты/пути ×0. Оставшиеся попадания класса B/C — буквальные («superseded» о двух
замещённых деревьях, «shipped» о данных gl_gym, «steps, not seasons») и переведённый
протокол («honest in silico economic benchmark», «In other words» — «честный in-silico
экономический бенчмарк», «Иными словами» в русском оригинале).

Проверено после правок: `make_numbers_md.py` воспроизводит NUMBERS.md побайтно
(SHA `b7475d14…`), 24 `.py` в архиве парсятся, `README.txt` не упоминает SPEC.md и план.
