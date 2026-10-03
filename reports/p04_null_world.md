# P04 matched null-world control

- Run ID: `p04-null-world-20261002T162128Z`
- Worlds: `100`
- Candidates per world: `1,000`
- Selected per world: `50`
- Total selected: `5,000`
- Seed: `20261002`
- Positive selected fraction: `1.0`

The control feeds zero-mean random scores through the same bounded GA and
selection interfaces. A 100% positive-selected fraction is the expected
winner's-curse signal under this deliberately permissive null and demonstrates
why Monte Carlo on selected trades cannot establish predictive validity.
