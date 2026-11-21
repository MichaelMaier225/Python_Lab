# SVM v5

Supabase captured 133 votes on 125 pairs. One false match was AppleCare+ for
13-inch and 15-inch MacBook Pros. V5 added a check for conflicting sizes in
the same MacBook family.

The check fired on that vote and on zero of the 201,457 training pairs and
66,769 validation pairs. It got zero weight during training.

| Same 4,376 WDC gold pairs | V4 | V5 |
| --- | ---: | ---: |
| True matches | 951 | 968 |
| False matches | 79 | 88 |
| Precision | 92.33% | 91.67% |
| Recall | 79.38% | 80.80% |
| F0.5 | 0.8941 | 0.8927 |

V5 used a lower threshold. V4 stayed live because it made fewer false matches.
See the [training commands](../../training.md) to repeat the check.
