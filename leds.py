"""Stock Pro v15 RGB field writes captured from Midi Suite 1.15.0.

Only the first pad bank's RGB bytes are addressed. No Save/update commands.
Offsets verified against all 16 pad records in the exported preset.
"""
from collections import OrderedDict

RGB_BASE = 0x11B
PAD_STRIDE = 74
BLACK = (0, 0, 0)
GREEN = (0, 255, 20)
PINK = (255, 0, 100)
RED = (255, 0, 0)
ORANGE = (255, 110, 0)
PURPLE = (130, 0, 255)
CYAN = (0, 255, 190)
LIGHT_YELLOW = (255, 255, 120)


def pack7(data):
    accumulator = bits = 0
    result = []
    for byte in data:
        accumulator |= byte << bits
        bits += 8
        while bits >= 7:
            result.append(accumulator & 127)
            accumulator >>= 7
            bits -= 7
    if bits:
        result.append(accumulator & 127)
    return tuple(result)


def color_messages(pad, rgb):
    if not 0 <= pad < 16 or len(rgb) != 3:
        raise ValueError('Invalid pad or RGB')
    messages = []
    for channel, value in enumerate(rgb):
        if not isinstance(value, int) or not 0 <= value <= 255:
            raise ValueError('RGB byte out of range')
        address = RGB_BASE + pad * PAD_STRIDE + channel
        body = (5,) + tuple(address.to_bytes(4, 'little')) + (1, 0, 0, value)
        raw = (0, 0x59, 0x22, 9, 0, 0) + body + ((~sum(body)) & 255,)
        messages.append((0xF0,) + pack7(raw) + (0xF7,))
    return tuple(messages)


def dim(rgb, factor=0.20):
    return tuple(int(component * factor) for component in rgb)


def track_rgb(track):
    color = int(track.color)
    return ((color >> 16) & 255, (color >> 8) & 255, color & 255)


def focused_slot(song):
    """The same track/scene intersection used by navigation and the Arm marker."""
    scenes = tuple(song.scenes)
    selected_scene = song.view.selected_scene
    slots = tuple(getattr(song.view.selected_track, 'clip_slots', ()))
    if selected_scene not in scenes:
        return None
    index = scenes.index(selected_scene)
    return slots[index] if index < len(slots) else None


def colors_for_song(song, offset, blink):
    selected = song.view.selected_track
    armed = selected.can_be_armed and selected.arm
    playing = song.is_playing
    target = focused_slot(song)
    # Transport first, so its updates take priority over a whole new clip bank.
    colors = OrderedDict(enumerate((
        GREEN if playing else dim(GREEN),
        dim(LIGHT_YELLOW) if playing else LIGHT_YELLOW,
        RED if song.record_mode and playing else dim(RED),
        RED if target is not None and target.has_clip else dim(RED),
        ORANGE if song.loop else dim(ORANGE),
        PURPLE if song.metronome else dim(PURPLE),
        PINK if armed else dim(PINK),
        CYAN if song.can_undo else dim(CYAN),
    ), start=8))
    tracks = tuple(song.visible_tracks)
    scenes = tuple(song.scenes)
    scene = scenes.index(song.view.selected_scene) if scenes else None
    for column in range(8):
        rgb = BLACK
        index = offset + column
        if index < len(tracks) and scene is not None:
            track = tracks[index]
            slot = track.clip_slots[scene]
            color = track_rgb(track)
            if slot.has_clip and slot.clip.is_recording:
                rgb = RED
            elif track == selected and armed:
                # Focus marker includes empty slots in the selected scene.
                rgb = dim(RED)
            elif slot.is_triggered:
                color = RED if slot.will_record_on_start else color
                rgb = color if blink else dim(color)
            elif slot.has_clip:
                clip = slot.clip
                rgb = color if clip.is_playing else dim(color, 0.40)
            else:
                rgb = dim(color, 0.10)
        colors[column] = rgb
    return colors


class PadLights:
    def __init__(self):
        self.sent = {}
        self.pending = OrderedDict()

    def update(self, colors):
        for pad, rgb in colors.items():
            for channel, value in enumerate(rgb):
                key = (pad, channel)
                if self.sent.get(key) == value:
                    self.pending.pop(key, None)
                else:
                    self.pending[key] = value

    def flush(self, send, limit=1):
        # Pro v15 drops back-to-back configuration writes. One per display tick
        # (100 ms), matching the independently verified slow-send experiment.
        for _ in range(min(limit, len(self.pending))):
            key, value = next(iter(self.pending.items()))
            pad, channel = key
            rgb = tuple(value if index == channel else 0 for index in range(3))
            message = color_messages(pad, rgb)[channel]
            if not send(message):
                return
            self.sent[key] = value
            del self.pending[key]
