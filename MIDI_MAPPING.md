# Expected MIDI assignments

MIDI channels below use human-readable numbering 1–16 (the Python API uses 0–15). These were captured on the tested unit's current preset; they are not a claim about every factory preset.

| Physical controls | Channel | Message / identifier |
| --- | --- | --- |
| Top pads, left to right | 10 | Note 40, 41, 42, 43, 48, 49, 50, 51 |
| Bottom pads, left to right | 10 | Note 36, 37, 38, 39, 44, 45, 46, 47 |
| K1 | 6 | CC48, absolute 0–127 |
| K2 | 6 | CC49, absolute 0–127 |
| F1–F4, left to right | 1 | CC64, CC65, CC66, CC67, absolute 0–127 |
| K8, optional manual mapping | 6 | CC55 in the captured configuration; not claimed by script |

Use Pad Bank 1 and the captured knob/fader banks. The pads must send Note messages with nonzero Note On values and a release (Note Off or Note On velocity 0). Channel pressure is not used for actions.

The script does not contain a full controller preset. Compare assignments before testing, especially if you have edited your keyboard's channels or pad notes. Changing note assignments alone does not change the physical RGB address map below.
