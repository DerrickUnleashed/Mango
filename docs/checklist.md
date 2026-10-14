# Submission Checklist — What's Still Missing

Scan of every `.tex` file in `docs/` for placeholders, empty tables and image frames.
`\pp{...}` prints as `<<...>>`, `\figph{...}` prints a framed `[IMAGE PLACEHOLDER]` box, and
every table row marked `\hr` is an empty shell.

Legend: `[ ]` todo · file refs are `docs/<file>`. Completed items are removed as they land;
the record of what was already fixed lives in `doc.md` and the git history.

Current state: 6 `\pp{...}` values left in Ch8, all inside three tables, and 3 figures
left; every one of them is gated on the identity memory running inside the evaluated loop.
72 pages.

---

## 1. Ground-truth sign-off (not blocking)

The retained identities were reviewed with `scripts/review_ground_truth.py`, which renders one row
per identity across its lifespan. All 30 identities across the three videos hold one fruit
throughout; the five size-variation flags and three look-alike identities in V3 were checked and
are genuine. Written up in `docs/GT-REVIEW.md`.

- [ ] A person still confirms the labels before submission. The construction is sound and the
      numbers reproducible; this is a sign-off, not a fix

## 2. Harness gaps (need the identity memory in the evaluated loop)

The offline harness scores detection and tracking only. The ReID threshold and the
camera-motion compensation both act inside the identity memory, which the API pipeline runs
but the harness does not, so three tables and two figures cannot honestly be filled yet.

- [ ] `tab:cam` — camera-motion compensation on/off: IDF1, HOTA, ID switches
- [ ] `tab:thr` — ReID threshold sweep at 0.5 / 0.6 / 0.7 / 0.8
- [ ] `fig:proj` — two-dimensional projection of identity prototypes
- [ ] `fig:reid` — filmstrip of a fruit lost and re-identified after an occlusion

## 3. Other open items

- [ ] TAPNext row in `tab:trackers` and `tab:timing` — the checkpoint is not on this machine
- [ ] Page count and formatting match department norms (72 pages currently)

---

## Fastest path to a submittable draft

1. Sign off the ground-truth labels (section 1). The numbers are already computed and written up.
2. Extend the harness to run the identity memory, then fill `tab:cam`, `tab:thr`, `fig:proj`
   and `fig:reid` (section 2). This is the only route to the last four gaps.
3. Get the TAPNext checkpoint onto this machine and add its row.
4. Confirm the page count against the guide's format spec.