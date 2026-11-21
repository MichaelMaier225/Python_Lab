# LinearSVC v5 feedback experiment

## From feedback to a feature

The Supabase export contained 133 votes on 125 distinct pairs. It included
a false match between AppleCare+ plans for 13-inch and 15-inch MacBook Pros.
V5 added one input to LinearSVC that flags an explicit coverage size conflict
when both listings name the same MacBook family.

## What the audit found

| Dataset | Pairs or votes flagged |
| --- | ---: |
| WDC training | 0 / 201,457 |
| WDC validation | 0 / 66,769 |
| Supabase feedback | 1 / 133 |

The rule flagged the AppleCare+ pair. It was always zero during fitting and
received zero weight in the resulting model.

## What stayed live

| Metric on the same 4,376 deduplicated WDC gold pairs | V4 | V5 |
| --- | ---: | ---: |
| True matches found | 951 | 968 |
| False matches | 79 | 88 |
| Precision | 92.33% | 91.67% |
| Recall | 79.38% | 80.80% |
| F0.5 | 0.8941 | 0.8927 |

V5 used a lower match threshold and found more true matches, with more false
matches. The added feature contributed zero to its scores. V4 remained deployed
because the experiment's goal was to reduce false matches. The Supabase votes
served as examples for feature design.

See [training commands](../../training.md) to repeat the audit or benchmark.
