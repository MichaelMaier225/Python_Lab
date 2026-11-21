# SVM v4 results

The five saved models are under [trained_models/svm/v4](../../../trained_models/svm/v4/).
The website uses Combined and its saved threshold.

Gold scores were reproduced with the dataset hash in [results.json](results.json).
The models were trained on Windows. The recorded code hashes refer to that
training run and its CRLF line endings.

Validation selected settings by F0.5. Exact gold pairs were kept out of
training, though some product IDs still overlap. Combined correctly rejected
two known iPhone accessory false matches. Those cases give a spot check of
that issue. Overall website precision is still unmeasured.
