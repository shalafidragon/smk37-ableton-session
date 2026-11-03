# Stock SMK-37 Pro v15 RGB protocol observations

Captured from Midi Suite 1.15.0 on macOS and independently replayed to one SMK-37 Pro. The general framing and bit packing are described in [genkigenki's porting documentation](https://github.com/genkigenki/fm1-to-smk37/blob/main/docs/02-update-and-recovery.md). The RGB field offsets and pacing behavior below were checked in this project.

## Frame and write body

```text
F0 pack7(00 59 22 09 00 00 BODY CHECKSUM) F7
BODY = 05 ADDRESS_LE32 01 00 00 VALUE
CHECKSUM = (~sum(BODY)) & FF
```

All numbers in this section are hexadecimal unless stated otherwise. The unpacked header length is nine body bytes. VALUE is an 8-bit RGB component (00–FF). `01 00 00` is the one-byte write count. `05` is the observed selector for the preset data region; static analysis of Pro v15 maps its ordinary write callback to a RAM preset buffer, with separate special requests for persistence (see the audit).

`pack7` serializes the whole raw payload as a continuous least-significant-bit-first stream of 7-bit groups. It is NOT the common scheme of a prefix byte holding the high bits of seven following bytes. This is why an 8-bit RGB value can be carried inside valid 7-bit SysEx data.

Only edit the exact RGB fields below. The addresses are offsets in the observed selected-preset data region, not CPU or flash addresses. No assumption is made about other firmware layouts or the role of nearby fields such as the editor's separate LED setting.

## First-bank physical pad addresses

Zero-based pad index `p`: `R = 0x11B + 74*p` (74 decimal), `G = R+1`, `B = R+2`.

| Physical position | Editor pad | R | G | B |
| --- | --- | --- | --- | --- |
| Top, 1 from left | 1 | 0x11B | 0x11C | 0x11D |
| Top, 2 from left | 2 | 0x165 | 0x166 | 0x167 |
| Top, 3 from left | 3 | 0x1AF | 0x1B0 | 0x1B1 |
| Top, 4 from left | 4 | 0x1F9 | 0x1FA | 0x1FB |
| Top, 5 from left | 5 | 0x243 | 0x244 | 0x245 |
| Top, 6 from left | 6 | 0x28D | 0x28E | 0x28F |
| Top, 7 from left | 7 | 0x2D7 | 0x2D8 | 0x2D9 |
| Top, 8 from left | 8 | 0x321 | 0x322 | 0x323 |
| Bottom, 1 from left | 9 | 0x36B | 0x36C | 0x36D |
| Bottom, 2 from left | 10 | 0x3B5 | 0x3B6 | 0x3B7 |
| Bottom, 3 from left | 11 | 0x3FF | 0x400 | 0x401 |
| Bottom, 4 from left | 12 | 0x449 | 0x44A | 0x44B |
| Bottom, 5 from left | 13 | 0x493 | 0x494 | 0x495 |
| Bottom, 6 from left | 14 | 0x4DD | 0x4DE | 0x4DF |
| Bottom, 7 from left | 15 | 0x527 | 0x528 | 0x529 |
| Bottom, 8 from left | 16 | 0x571 | 0x572 | 0x573 |

All 16 offsets were checked against their note/channel records in an exported preset. Physical pad 13 (bottom row, fifth from left) was used for the initial replay confirmation.

## Captured example: pad 13, RGB 00 2A FF

These are three complete on-wire MIDI messages, in R/G/B order:

```text
F0 00 32 09 49 00 00 40 02 13 09 00 00 10 00 00 00 00 44 01 F7
F0 00 32 09 49 00 00 40 02 14 09 00 00 10 00 00 00 2A 6E 00 F7
F0 00 32 09 49 00 00 40 02 15 09 00 00 10 00 00 00 7F 43 01 F7
```

Decoded raw messages:

```text
00 59 22 09 00 00 05 93 04 00 00 01 00 00 00 62
00 59 22 09 00 00 05 94 04 00 00 01 00 00 2A 37
00 59 22 09 00 00 05 95 04 00 00 01 00 00 FF 61
```

The included `leds.py` contains the tested encoder in `pack7` and `color_messages`. Example for a zero-based pad index: `color_messages(12, (0, 42, 255))`. Space each resulting message by approximately 100 ms; do not send the tuple of three messages in one burst.

## Why pacing matters

An independent readback experiment on physical pad 1 produced these results:

| Send pattern | Requested RGB | Readback |
| --- | --- | --- |
| Three component writes with 100 ms gaps | 01 02 03 | 01 02 03 |
| Three component writes sent back-to-back | 04 05 06 | 01 02 03 (unchanged) |

The paced writes also produced three acknowledgements. This establishes a working pacing choice for the tested unit; it does not establish the minimum possible interval or diagnose the firmware's internal cause.

Live was then tested independently: Play RGB read back as 00FF14 while playing, Stop as 1E000C in that historical test. Current released colors/brightness differ; the important result was that the device actually accepted Live's updates.

## Persistence and scope

The script sends no Save command. Static analysis of the archived stock Pro v15 firmware traces these RGB writes to RAM copies. Preset persistence uses a separate request that the script does not send. Full power-cycle tests also reverted the colors. This is evidence for the traced v15 RGB path, not an exhaustive guarantee of zero flash writes throughout the firmware or across other versions. See [FLASH_AUDIT.md](FLASH_AUDIT.md) for the traced callback chain and separate commit branch.

Ordinary Note On/Off tests on note 36, channels 1–16, velocities 5/20/60/127, on both physical USB ports caused no visible LED change. This is a negative result for those tested combinations, not proof that no other feedback mode exists.

`F0 7E 7F 06 02 ... F7` is the Universal Identity Reply form; it was not the RGB format captured from Midi Suite.

No modified Midi Suite binary, proprietary firmware image, personal preset dump or debugger is included. You only need the two Remote Script Python files for normal use.
