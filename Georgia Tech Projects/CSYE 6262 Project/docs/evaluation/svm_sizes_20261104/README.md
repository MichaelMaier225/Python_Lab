# Supplied SVM size experiment (2026-11-04)

The uploaded results, comparison table, split audit, validation IDs, and quarantined pairs are retained here. All five uploaded model artifacts are in `trained_models/svm/`. Their gold-test metrics were independently reproduced using the exact all_gs.json.gz SHA recorded in results.json. Training itself was not rerun during integration. The full training archives were not supplied here; their hashes and reported quarantine audit are preserved, not independently reconstructed.

Combined is the registry default because it had the highest common validation F1. Its saved threshold is +0.25. The original Small V3 baseline remains available separately with -0.25. New Small is a different fit from original Small V3.

Known limitations: `known_false_matches.json` records two clearly different accessory pairs that both models still classify as matches. Improved aggregate precision does not establish reliable model/compatibility conflict handling. These examples were not used to tune the threshold. Correcting them requires a separately validated feature/training revision; no ad hoc postprocessing has been added to hide the classifier output.

The exact supplied gold test has zero titles containing both iPhone and case (case-insensitive), across both pair sides. Its dominant recorded categories are Computers_and_Accessories, Shoes, Camera_and_Photo, and Jewelry. This is evidence of limited test coverage, not proof that no training record concerns phones; the training archives were not inspected here. Benchmark accuracy must not be presented as verified iPhone-case accuracy.
