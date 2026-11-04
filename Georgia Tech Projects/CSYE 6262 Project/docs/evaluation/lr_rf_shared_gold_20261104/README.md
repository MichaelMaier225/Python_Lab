# Saved LR/RF evaluation, 2026-11-04

Original saved artifacts, vectorizers/features, and classifier decision rules were evaluated without training or threshold changes. The evaluator calls the same prediction adapters used by the website, in their isolated scikit-learn 1.9.1 runtime. Artifact checksums in each result identify the exact unchanged model.

Both use the same original all_gs.json.gz SHA as SVM. One positive exact/reversed pair also occurs in the supplied normalized Computers XL archive and was excluded, leaving 4,397 pairs (3,200 different; 1,197 match). The retained pair-ID digest matches between LR and RF. SVM's currently displayed results still use all 4,398 pairs; do not describe all three scores as an identical-test-set ranking.

The supplied archive is a reference for overlap exclusion, not proof of the original LR CSV conversion or complete training history. Shared individual product IDs and unknown original preparation remain limitations. LR and RF were trained on computers; this is a broader benchmark evaluation, not the original computer-only notebook experiment. Full benchmark fields are used, including available specifications; current catalog listings lack RF specification-table text. This is not measured website-retrieval precision.

The full predictions/errors CSVs are generated locally under reports/evaluation/<model-id>/ and remain ignored. Reproduce from the project folder:

    python -m scripts.evaluate_model --model logistic_regression_v1 --exclude-training data/computers_train.zip --output reports/evaluation/logistic_regression_v1
    python -m scripts.evaluate_model --model random_forest_v1 --exclude-training data/computers_train.zip --output reports/evaluation/random_forest_v1

No algorithm source, saved artifact, learned coefficients/trees, or threshold was modified.
