# Method-Core Sources: SINDy, MPC, DAgger

Подборка дополнительных источников без OOD/LLM. Эти статьи полезны для
методической части будущей работы: physics-informed SINDy-признаки, sparse
model discovery, MPC и DAgger/dataset aggregation.

## Physics-informed / constrained SINDy

- `sindy_sr3_physics_informed_champion_2020_arxiv_1906.10612.pdf`
  - Champion et al., "A unified sparse optimization framework to learn
    parsimonious physics-informed models from data".
  - Полезно для обоснования physics-informed sparse regression, SR3 и
    включения ограничений/регуляризации в SINDy.

- `sindy_pi_kaheman_2020_arxiv_2002.03139.pdf`
  - Kaheman et al., "SINDy-PI: a robust algorithm for parallel implicit sparse
    identification of nonlinear dynamics".
  - Полезно для implicit/рациональных уравнений и случаев, когда динамика
    плохо выражается явной полиномиальной библиотекой.

- `trapping_sindy_kaptanoglu_2021_arxiv_2105.01843.pdf`
  - Kaptanoglu et al., "Promoting global stability in data-driven models of
    quadratic nonlinear dynamics".
  - Полезно для раздела о физически осмысленных ограничениях на найденную
    модель, особенно если захочется обсуждать bounded/stable learned dynamics.

- `weak_sindy_messenger_bortz_2020_arxiv_2005.04339.pdf`
  - Messenger and Bortz, "Weak SINDy: Galerkin-based data-driven model
    selection".
  - Полезно для устойчивой идентификации по шумным данным без прямого
    численного дифференцирования.

- `weak_sindy_pde_messenger_bortz_2020_arxiv_2007.02848.pdf`
  - Messenger and Bortz, "Weak SINDy for partial differential equations".
  - Полезно как источник по weak-form sparse discovery и библиотекам
    признаков для распределенных систем.

- `physics_informed_governing_equations_chen_2020_arxiv_2005.03448.pdf`
  - Chen et al., "Physics-informed learning of governing equations from scarce
    data".
  - Полезно для аргумента, что физические знания помогают при дефиците данных
    и улучшают обобщение найденных уравнений.

- `pysindy_kaptanoglu_2022_joss.pdf`
  - Kaptanoglu et al., "PySINDy: A comprehensive Python package for robust
    sparse system identification".
  - Полезно как implementation/reference paper для используемой библиотеки,
    custom feature libraries, optimizers and differentiation methods.

## MPC and learning-based MPC

- `sindy_mpc_kaiser_2018_arxiv_1711.05501.pdf`
  - Kaiser, Kutz and Brunton, "Sparse identification of nonlinear dynamics for
    model predictive control in the low-data limit".
  - Уже был добавлен ранее; это ключевой источник для связки SINDy + MPC.

- `learning_mpc_rosolia_borrelli_2016_arxiv_1609.01387.pdf`
  - Rosolia and Borrelli, "Learning Model Predictive Control for Iterative
    Tasks. A Data-Driven Control Framework".
  - Полезно для итеративного улучшения MPC по данным rollout'ов.

- `learning_based_mpc_safe_exploration_koller_2018_arxiv_1803.08287.pdf`
  - Koller et al., "Learning-based Model Predictive Control for Safe
    Exploration".
  - Полезно для формулировки learning-based MPC с constraints и обновляемой
    моделью.

- `guided_policy_search_tube_mpc_tagliabue_2021_arxiv_2109.09910.pdf`
  - Tagliabue et al., "Demonstration-Efficient Guided Policy Search via
    Imitation of Robust Tube MPC".
  - Полезно как мост между expensive MPC expert и policy learning через
    imitation.

## DAgger / dataset aggregation

- `dagger_ross_2011_pmlr.pdf`
  - Ross, Gordon and Bagnell, "A Reduction of Imitation Learning and Structured
    Prediction to No-Regret Online Learning".
  - Базовая статья DAgger: dataset aggregation для устранения distribution
    shift между expert demonstrations и learned policy rollouts.

- `aggrevate_ross_bagnell_2014_arxiv_1406.5979.pdf`
  - Ross and Bagnell, "Reinforcement and Imitation Learning via Interactive
    No-Regret Learning".
  - Полезно как развитие интерактивного imitation learning с cost-to-go.

- `deeply_aggrevated_sun_2017_pmlr.pdf`
  - Sun et al., "Deeply AggreVaTeD: Differentiable Imitation Learning for
    Sequential Prediction".
  - Полезно для modern/deep variant of AggreVaTe and DAgger-style training.

- `deep_mpc_dagger_espin_2024_arxiv_2406.15985.pdf`
  - Espin et al., "Deep-MPC: A DAGGER-Driven Imitation Learning Strategy for
    Optimal Constrained Battery Charging".
  - Полезно как свежий пример связки DAgger + constrained MPC expert, пусть и
    вне контекста теплиц.

## Как использовать в статье

- Для блока SINDy-признаков: связать свою библиотеку
  `[psat, vpd, S_eff, t_S_eff, h_uVent, dc_uVent, t_uBoil]` с идеей
  physics-informed candidate libraries из Champion et al., SINDy-PI и
  physics-informed scarce-data literature.
- Для блока MPC: Kaiser et al. как главный методологический аналог SINDy-MPC;
  Rosolia/Borrelli и Koller et al. как backing для learning-based/iterative MPC.
- Для блока DAgger: Ross et al. как базовая теория dataset aggregation; Deep-MPC
  и guided policy search with tube MPC как аргументы, что MPC может выступать
  expert/policy generator для итеративного сбора данных.
