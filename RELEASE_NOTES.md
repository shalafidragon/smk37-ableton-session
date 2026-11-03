# v1.7 — SMK-37 Pro stock firmware Session View controller

**Demo video:** coming soon.

First public macOS test release. Tested on one SMK-37 Pro, stock v15 over USB, Ableton Live 12.4.7.

- Eight Session clip slots, track/scene navigation and Arm following focus.
- Play, Stop, Arrangement Record, Delete focused clip, Arrangement Loop, Metronome, Arm and Undo.
- Selected-track volume and Sends A/B/C; K8 free for manual mapping.
- RGB track colors with 10/40/100% empty/stopped/playing levels; red armed-focus and recording indicators.
- Stock SysEx RGB writes paced one component per display tick, with changed-value coalescing.

Delete and Undo are confirmed working on the physical keyboard. Static analysis of the archived v15 image traces our RGB update path to RAM; preset commit is separate. See FLASH_AUDIT.md for evidence and limits.

Download the attached SMK37_Custom-v1.7-macOS-test-release.zip, unzip it and follow README.md. Assign both Control Surface Input and Output to Private. Match MIDI_MAPPING.md and stay on Pad Bank 1. Windows, other firmware/models and Bluetooth remain untested.
