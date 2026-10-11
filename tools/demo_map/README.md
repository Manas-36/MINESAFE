# Demo mine map

`demo_mine_plan.png` is a **made-up** underground plan for testing the Map tab (labelled "fictional plan for testing only"). `map.json` is the matching hub map setup: origin at the main shaft, 8 px per metre, the tunnels, two exits (main shaft, escape shaft) and REP-01 … REP-06 already placed.

Load it in one step (hub stopped):

```
copy tools\demo_map\map.json          hub\data\map.json
copy tools\demo_map\demo_mine_plan.png hub\data\map\demo_mine_plan.png
```

Then start the hub — the Map tab opens with the plan lined up. Or upload only the PNG on the Map tab and set the hub point / scale yourself.

Regenerate: `python make_demo_map.py` (needs matplotlib).
