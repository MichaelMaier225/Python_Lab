# Earlier SVM size runs

The five saved fits are under [trained_models/svm](../../../trained_models/svm/).
Gold scores were reproduced using the dataset hash in [results.json](results.json).
Training was not rerun. The supplied split audit and results are saved here.

Combined led on validation F1 in this run and used a threshold of +0.25.
The original Small V3 used -0.25. The current website uses Combined **v4**.

[Known false matches](known_false_matches.json) has two accessory examples
these models missed. The gold dataset had zero titles containing both
`iPhone` and `case`, so it gives little evidence about iPhone case matching.
