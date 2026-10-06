# Frozen-result provenance

The supplied project archive contained only `case-000.json` through
`case-011.json` and contained none of `summary.json`, `outcomes.json`,
`mutations.json`, or `micro-exhaustive.json`. A search of the files supplied in
this conversation found no copy of the missing 84 certificates or the missing
old aggregate records. Those old files are therefore not claimed as recovered.

After repairing the serialization/type contract, the retained deterministic
96-case corpus was regenerated in an independent candidate directory. The
candidate run produced all 96 certificates, executed every applicable named
mutation without a tail limit, recomputed the bounded micro-exhaustive grid,
and replayed the complete result bundle. The 12 certificates that were present
in the supplied archive matched their newly generated counterparts exactly as
JSON values. The other 84 certificates and all aggregate result records are a
fresh deterministic regeneration from the retained corpus and source.

The following inherited measurements describe the earlier regeneration
recorded by the supplied package (the frozen summary identifies Python 3.13.5
on Linux). They are not measurements of subsequent checks on another host:

- producer/oracle/certificate/mutation campaign: 2.38 s user CPU, 2.03 s wall,
  97,452 KiB maximum resident set size;
- micro-exhaustive recomputation: 1.50 s user CPU, 1.24 s wall, 93,228 KiB;
- complete certificate and mutation replay: 2.22 s user CPU, 1.90 s wall,
  104,616 KiB.

These measurements describe this run only. The finite results test the encoded
model and implementation; they do not replace the mathematical proofs or show
upstream-system integration.
