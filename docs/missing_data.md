# Missing-data decisions

These counts are from the generated CSVs in `data/clean/` for the 2021–2025
extracts. Blank CSV cells are treated as missing values. Percentages use the
number of rows in that table as the denominator.

| Table | Column | Missing rows | % Missing | Decision | Why |
| --- | --- | ---: | ---: | --- | --- |
| `dim_circuit` | `locality` | 28/28 | 100% | Leave as NULL until a verified circuit lookup is available. | The raw race and weather extracts do not provide locality. Guessing it from the circuit name could assign the wrong city. |
| `dim_circuit` | `country` | 28/28 | 100% | Leave as NULL until a verified circuit lookup is available. | Country is not present in the current raw extracts and should not be inferred from a circuit name. |
| `dim_driver` | `date_of_birth` | 35/35 | 100% | Leave as NULL until a verified driver lookup is available. | No raw source supplies birth dates; a made-up or inferred date would be misleading. Not needed for ML table. |
| `dim_driver` | `nationality` | 35/35 | 100% | Leave as NULL until a verified driver lookup is available. | No raw source supplies driver nationality, and it should not be inferred. Not needed for ML table. |
| `fact_driver_standing` | `team_id` | 1,784/1,784 | 100% | Do not guess. Keep NULL in any export; exclude this field from loading under the current schema. | The raw results have no constructor/team names, so stable team IDs cannot be assigned. The active `schema.sql` does not define `team_id` on this fact table. Not needed for ML table. |
| `fact_race_result` | `team_id` | 1,699/1,699 | 100% | Do not guess. Keep NULL in any export; exclude this field from loading under the current schema. | The raw results have no constructor/team names, so stable team IDs cannot be assigned. The active `schema.sql` does not define `team_id` on this fact table. Not needed for ML table. |
| `fact_race_result` | `fastest_lap_time` | 1,699/1,699 | 100% | Leave as NULL. | Fastest-lap time is not included in the current raw results extract. It is optional in the schema and should not be fabricated. Not needed for ML table. |

## Row handling

No rows are dropped because of these missing column values. The race-result
records remain useful for the prediction target and other available features;
dropping every row to avoid an unavailable optional field would discard the
entire dataset. When loading CSVs, interpret blank cells as SQL `NULL`, not as zero or the text
`"nan"`.
The active schema allows NULL in `dim_circuit.country`,
`dim_driver.date_of_birth`, and `dim_driver.nationality` to honor these decisions.
The loader skips the legacy `team_id` columns in the two fact CSVs because those
columns do not exist in the active fact-table schema; no team IDs are inferred.

Other columns in the current clean CSVs had no blank values at the time of this
check. The transform separately excludes 200 sprint-result rows because the
prediction unit is one driver in one main race, and excludes 2,088 hourly
weather observations that do not match a main-race season/round key; neither
count is a missing-value drop.
