# SMK37 Custom v1.7 — macOS test release

An unofficial Ableton Live Remote Script for the M-VAVE SMK-37 Pro, using its stock firmware. Session navigation, clip launch/record/delete, transport, selected-track faders and RGB pad feedback. Developed iteratively with Codex and tested on one physical keyboard.

**Demo video:** coming soon.

## Tested setup

- SMK-37 Pro, stock firmware shown as v15 in Midi Suite.
- USB connection; Ableton Live 12.4.7 on macOS.
- Midi Suite 1.15.0 was used to investigate RGB messages. It is not required to run this script.
- No custom keyboard firmware or companion background service is required.
- Windows, other Live versions, Elite models, other firmware revisions and Bluetooth have not been validated.
- This is a source-included test release, not an official M-VAVE or Ableton product.

## Installation

1. Close Live. Export your current keyboard preset in Midi Suite before changing any controller settings.
2. Find your actual Live User Library. At its default macOS location, create:
   `~/Music/Ableton/User Library/Remote Scripts/`
3. Copy the whole `SMK37_Custom` folder there. The resulting structure must be:

   ```text
   User Library/
     Remote Scripts/
       SMK37_Custom/
         __init__.py
         leds.py
   ```

4. Restart Live. In Settings → Tempo & MIDI, use a free Control Surface row:
   - Control Surface: `SMK37_Custom`
   - Input: `SMK-37 Pro-Private`
   - Output: `SMK-37 Pro-Private`
5. In the lower MIDI-port table, enable input Track for Private and disable input Track for Master. On the tested unit, both ports duplicated the same notes; enabling both can produce duplicate input.
6. The lower-table Remote switches are not a substitute for assigning the Control Surface Input/Output above. Enable input Remote on Private if you also want to make manual Cmd+M assignments, such as K8 → tempo. Sync is not required. Output Track/Sync/Remote are not required for this script's RGB feedback.
7. Close Midi Suite during normal use. Give the initial pad colors several seconds to settle.

If your User Library is elsewhere, use that location instead. See [Ableton's installation guide](https://help.ableton.com/hc/en-us/articles/209072009-Installing-third-party-remote-scripts).

## Controls

### Top row: eight tracks in the selected scene

Pads launch their corresponding Session clip slots. An empty slot on an armed track can begin recording under Live's normal recording and launch rules. Clip launch quantization and launch modes still apply. The Session highlight follows the selected track when it moves outside the eight-track window.

### Bottom row, left to right

| Pad | Action | Color |
| --- | --- | --- |
| 1 | Play | Green |
| 2 | Stop transport | Light yellow |
| 3 | Toggle Arrangement Record | Red |
| 4 | Delete clip at selected track × selected scene | Red; bright when a clip is available |
| 5 | Toggle Arrangement Loop | Orange |
| 6 | Toggle metronome | Purple |
| 7 | Arm / toggle Arm following focus | Pink |
| 8 | Undo | Turquoise |

Delete acts on the selected track/scene intersection, not an arbitrary clip open in Detail View. Empty slots and Return/Main tracks do nothing. It does not delete the track. Undo can restore the deletion. Session Record is no longer assigned to bottom pad 4.

### Knobs and faders

| Control | Action |
| --- | --- |
| K1 | Select visible track |
| K2 | Select scene |
| K3–K8 | Unassigned by the script |
| F1 | Selected track volume |
| F2 | Selected track Send A |
| F3 | Selected track Send B |
| F4 | Selected track Send C |

Missing sends are left unassigned. Faders use Live's native parameter mappings and respect its global Takeover Mode. K8 can be mapped to tempo using Cmd+M, including your preferred min/max range.

K1/K2 use absolute CC input: the first message establishes a reference, then four MIDI value units produce one selection step. At 0/127, turn the knob back before continuing. These are not unlimited relative encoders in the captured configuration.

The script does not claim musical key notes, pitch bend or modulation. Important mapping detail: F1 uses channel-1 CC64, which is also the standard sustain controller. A pedal transmitting the same channel/CC cannot be distinguished from F1 by this script. Pedal coexistence has not been validated.

## Arm behavior

The mode starts off. If the selected track is already armed, pressing bottom pad 7 disarms it. Otherwise that press enables Arm-follow-focus and arms the selected track. Moving focus with K1 or the mouse transfers the Arm enabled by the script. Tracks already armed manually are preserved during navigation. Pressing pad 7 while follow mode is on disables it and disarms the current track plus any Arm still owned by the script. Return/Main tracks cannot be armed; the mode can remain enabled while they are selected. Disconnecting the script releases its own Arm.

## Top-row colors

- No corresponding track: off.
- Existing track, empty slot: 10% of track RGB.
- Existing stopped clip: 40% of track RGB.
- Playing clip: 100% of track RGB.
- Selected track with Arm: selected-scene slot is red at 20%, even when empty or playing.
- Recording clip: 100% red, overriding the focus marker.
- A triggered slot outside the armed-focus override alternates bright/dim while awaiting launch.

These percentages scale RGB values; perceived LED brightness is not linear. Lower-row inactive colors use 20%, active colors use 100%. The Arrangement Record indicator is bright red only while record mode and playback are both active. Stop is bright when stopped and dim while playing. Undo is dim when unavailable.

## RGB behavior and limits

The script reproduces Midi Suite's stock preset-field SysEx writes. It only targets RGB bytes for the first 16-pad bank, sends changed values, and spaces writes one per Live display tick. Sending several writes back-to-back failed on our unit, while 100 ms gaps worked and were verified by readback. Full initial painting and large changes take several seconds; rapid blinking across multiple pads may lag or coalesce.

No Save or firmware-update command is sent. Static analysis of the archived stock Pro v15 firmware traces these RGB writes to RAM copies. Preset persistence uses a separate request that the script does not send. Full power-cycle tests also reverted the colors. This is evidence for the traced v15 RGB path, not an exhaustive guarantee of zero flash writes throughout the firmware or across other versions. See [the static audit](FLASH_AUDIT.md) for addresses, image hashes and limitations. This remains a reverse-engineered preset-field mechanism, not a documented dedicated LED API.

Stay on Pad Bank 1. The script does not manage bank switching, screen text, other presets, or firmware upgrades. After a keyboard power cycle, reinitialize the Control Surface (None → SMK37_Custom) if colors are stale. After installing new script files, fully restart Live.

## Troubleshooting / removal

- Nothing responds: check the Input in the Control Surface row; it must not be None or an old MiniLab port.
- Controls work but colors do not: check Output in that same row and allow several seconds. Confirm stock v15 and Bank 1. Do not run multiple RGB-writing apps at once.
- Mapping differs: compare MIDI_MAPPING.md with your preset; this package does not overwrite your full keyboard preset.
- Check Live's Log.txt for `SMK37_Custom v1.7` and `SMK37 RGB` errors.
- To stop using it, choose None for this Control Surface. To uninstall, close Live and remove only its `SMK37_Custom` folder from Remote Scripts. Other scripts are independent.

## Validation

RGB transport changes were verified both visually and by reading values back from the physical keyboard. Navigation, transport, faders and Arm-follow behavior were exercised during development. Codec packets are compared against actual Midi Suite captures; all 16 RGB offsets match the exported preset. Automated checks cover colors, queue pacing/coalescing, focus movement and deletion targeting/debounce. The final pad-4 Delete and pad-8 Undo actions were both confirmed working by the tester on the physical keyboard.

For reports, include your exact keyboard model, stock firmware, Live/macOS versions, MIDI preset/assignments, and which input/output ports are selected.
