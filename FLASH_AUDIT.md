# SMK-37 Pro v15: static RGB / persistence investigation

## Result and scope

The current script’s command `0x22`, selector `5`, one-byte writes to first-bank RGB offsets take a RAM-copy path. That path does not call the separately identified preset commit routine. This provides code-level support for the observed loss of LED changes after power-off. It is not an exhaustive proof of zero flash writes anywhere in the firmware.

No keyboard connection, MIDI send, firmware installation, or hardware readout was used during this investigation. No change to the working Ableton script was required.

## Image and tools

Source: [community archive, stock Pro v15](https://github.com/jonathaslacerda/smk-37-pro-docs/blob/main/firmware/smk37pro/SMK-37_Pro_015.fwsc).

Package SHA-256: `f7f1831cd7c9ad8b4831b6e71ea0bdbcdff9ae4c4077276b3c965511bf4d4fff`.
Extracted app SHA-256: `36fe8299667d06d4e2c195ea0b125b8e3400a4dc010b45d6989354dd4e172055`.
App length: 617012 bytes; execution base: `0x02000120`.

Unpacked using [jl-misctools](https://github.com/kagaimiq/jl-misctools). Decoded using the pure-Python [pi32v2-isa](https://github.com/jvitkauskas/pi32v2-isa) decoder. Linear disassembly includes data; conclusions below use function bodies, the command jump table, callback registration, and the callback table in the image. Parallel instructions marked `#` must be interpreted as a pair, not sequential overwrites.

## Traced path

1. `0x02008564`: USB MIDI SysEx parser; decodes packed bytes and checks header `00 59`.
2. Completed packet posts task message 144; handler at `0x0202D36A` passes the decoded buffer and length to `0x0202C358`.
3. `0x0202C358`: validates length and complemented body checksum. Commands `0x21..0x24` dispatch through a halfword jump table. The `0x22` case starts at `0x0202C4F2`.
4. The case fetches selector callback table `[global +1892 + selector*4]`, takes callback at table offset `+8`, and passes `(payload, offset_le32, count_le24)`.
5. Initialization at `0x0200677A..0x02006796` assigns selector 5 the ROM table `0x02057B80`. Its four words are `(0, 0x0202B976, 0x0202B988, 0)`; thus write callback is `0x0202B988`.
6. For an ordinary RGB write, `0x0202B988` reaches `0x0202BA22`, adds the offset to RAM base `0x01C0DE20`, and calls `0x02048DEE` with destination RAM, source payload, length 1. Inspection of `0x02048DEE` shows byte/word copy loops, including backward copying for overlap; no calls or flash programming operations.
7. The command handler then sends the normal response. No extra save is scheduled on this RGB branch.

## Separate persistence and deferred branches

The same selector-5 callback handles special requests. When both offset and count are zero, its early branch (`0x0202B996`) may call `0x02024F22` for one or two preset banks. This function performs five 4 KiB erase-style operations through `0x02004B74`, then writes 18915 bytes through `0x02004C22`. The latter wraps a page writer with calls to ROM `0x01C00820`. This is a separate preset commit path, inferred from those erase/program patterns; names were not present as symbols. The script never generates zero-offset, zero-length packets.

There is also a conditional countdown setter at `0x0202BA1C` (`global +54 = 50`). In its guarded mode it requires offset greater than `(bank+1)*2689` and less than `(bank+1)*18915`. Our RGB offsets are all at most 1395, so they cannot satisfy it for any nonnegative bank. Its expiry at `0x0202881E` calls `0x02024FAC`, whose inspected body rebuilds derived preset data in RAM; do not label this countdown itself a flash-save timer.

## Comparison with our sender

`SMK37_Custom/leds.py:color_messages` constructs only selector 5, command `0x22`, count 1 packets. For pads 0..15, component addresses are `0x11B + 74*pad + component`, component 0..2: 48 addresses between 283 and 1395. These are field offsets, not CPU addresses. They do not match the commit request or countdown guard. The script sends no Save/update command.

## Limits

The downloaded image was not compared byte-for-byte with a dump of this physical keyboard. An independent decoder was used, not the vendor toolchain. ROM function names are inferred. No exhaustive proof against every unrelated background writer, all indirect calls, or future firmware revisions is claimed. The strongest supported statement is: **the traced RGB update path in this stock Pro v15 image writes RAM and does not invoke the identified preset commit path**.

For publication, avoid “guaranteed zero flash wear.” A suitable statement is: “Static analysis of stock Pro v15 traces our RGB updates to RAM copies; preset persistence uses a separate request that the script does not send. Power-cycle tests also reverted the colors.”
