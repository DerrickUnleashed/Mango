# Ground-truth annotation pass

Fix the candidate identities in the three labelme files, then hand them back.

## Files

| File | Frames to fix | Candidate IDs |
|---|---|---|
| `data/gt/labelme/test.json` | 48 | 61 |
| `data/gt/labelme/test4.json` | 15 | 47 |
| `data/gt/labelme/Test3.json` | 34 | 44 |

Images sit next to each JSON in `data/gt/labelme/images/`, every 10th video frame.

## Open

```bash
labelme data/gt/labelme/test.json      # repeat for test4.json, Test3.json
```

`labelme` is installed (7.8.1). Save with `Ctrl+S`; keep the JSON format.

## What to fix

The candidate IDs come from plain greedy IoU association, so one physical fruit
often carries several IDs. The task is to give every physical fruit one number
across the whole video.

- Two boxes of the same fruit in different frames must end up with the same label.
- Rename a label by editing the box text in the label list, or by deleting the box
  and redrawing it with the correct label.
- Delete boxes on fruit that leave the frame or are occluded beyond recognition.
- Draw a box if a fruit has none.
- Label format stays `mango_<number>`, three digits, zero padded: `mango_007`.
- Renumbering is optional; what matters is that the mapping fruit to number is
  consistent, not which number you pick.

## Reference

`data/gt/preview/*.jpg` shows 8 sampled frames per video with the candidate IDs
drawn, which is enough to spot the obvious merges without opening labelme.

## Back

Save the three JSONs in place. The evaluation harness reads them directly, so no
further conversion is needed.
