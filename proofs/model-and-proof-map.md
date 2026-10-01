# Model and proof map

This note is an index, not an additional proof claim. The authoritative editable proofs are `paper/main.tex` and `paper/supplement.tex`.

## Objects

- `n` input rows and `T` slots.
- A binary matrix `X in {0,1}^{n x T}`.
- Root column sums `h`.
- Exact totals for a selected row set.
- A finite family containing the root and directed strict balancing paths from the root to every member.

## Proof dependency order

1. **Unit transport:** a source column with strictly more ones than a destination column contains a row with pattern `(1,0)`; move that row's one.
2. **Path transport:** compose unit transport along each supplied path.
3. **Family reduction:** the root is a member, so root feasibility is necessary; path transport makes it sufficient for all descendants.
4. **Partial margins:** selected rows use between `max(0,h_t-(n-k))` and `min(h_t,k)` positions in every column; a lower-bound circulation and four cut classes prove sufficiency.
5. **Minimum core:** fixed-cardinality subset sums are extremized by sorted prefixes; the first failed prefix has globally minimum cardinality.
6. **Deletion witnesses:** removing any one member of the returned prefix has no smaller conflict and admits a constructive matrix.
7. **Termination:** the sum of squared column heights decreases by at least two per strict balancing step.
8. **Hardness boundary:** without complete-incidence symmetry and the root contract, distinct-label bounded paths encode Set Cover.

## Trusted boundary

The checker does not certify queue dynamics, service, buffer capacity, trace-family completeness, or physical counter correctness. It certifies only the typed case/certificate relation, binary margins, rooted paths, matrices, conflicts, and deletion witnesses.
