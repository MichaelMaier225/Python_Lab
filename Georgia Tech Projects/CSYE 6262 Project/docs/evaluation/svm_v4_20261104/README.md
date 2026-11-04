# SVM V4 run supplied 2026-11-04

All five uploaded artifacts are preserved in trained_models/svm/v4/. Only Combined is exposed on the website as SVM, with the artifact's saved threshold. Previous artifacts remain intact.

Model metadata, settings, validation metrics and training metrics agree with the supplied report. All five feature-pipeline hashes match current code when encoded with Windows CRLF line endings. Gold metrics were independently reproduced on the recorded all_gs.json.gz SHA. Full training was performed on the user's computer, not rerun here.

Selection used validation F0.5, emphasizing precision. Gold-test pairs were quarantined from fitting; some individual products remain shared across splits. This is not a product-disjoint generalization experiment. Training/validation gaps and overlap counts are retained in results.json.

Both previously inspected iPhone accessory mistakes are rejected by Combined V4. These are previously seen diagnostic cases, not a representative or untouched website test set. Broader website precision is still unmeasured. No promise of zero errors or no overfitting is supported.
