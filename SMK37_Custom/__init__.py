"""SMK-37 Pro stock-firmware Session View controller for Live 12."""
from functools import partial

import Live
from _Framework.ControlSurface import ControlSurface
from _Framework.ButtonElement import ButtonElement
from _Framework.EncoderElement import EncoderElement
from _Framework.SliderElement import SliderElement
from _Framework.InputControlElement import MIDI_NOTE_TYPE, MIDI_CC_TYPE
from .leds import PadLights, colors_for_song, focused_slot

TOP = (40, 41, 42, 43, 48, 49, 50, 51)
BOTTOM = (36, 37, 38, 39, 44, 45, 46, 47)
NAVIGATION_DIVISOR = 4


def create_instance(c_instance):
    return SMK37Custom(c_instance)


class SMK37Custom(ControlSurface):
    def __init__(self, c_instance):
        self._led_ready = False
        super(SMK37Custom, self).__init__(c_instance)
        self._offset = 0
        self._last_knob = [None, None]
        self._knob_accumulator = [0, 0]
        self._held = {}
        self._pressed = set()
        self._bindings = []
        self._faders = []
        self._arm_follow = False
        self._arm_focus = None
        self._owned_arm = None
        self._lights = PadLights()
        self._led_tick = 0
        self._led_error = None
        self._led_messages = 0
        with self.component_guard():
            for index in range(4):
                fader = SliderElement(MIDI_CC_TYPE, 0, 64 + index)
                fader.set_needs_takeover(True)
                self._faders.append(fader)
            for column, note in enumerate(TOP):
                self._bind(ButtonElement(True, MIDI_NOTE_TYPE, 9, note),
                           partial(self._clip, column))
            for index, note in enumerate(BOTTOM):
                self._bind(ButtonElement(True, MIDI_NOTE_TYPE, 9, note),
                           partial(self._transport, index))
            for index in range(2):
                self._bind(EncoderElement(MIDI_CC_TYPE, 5, 48 + index,
                                          Live.MidiMap.MapMode.absolute),
                           partial(self._navigate, index))
        song = self.song()
        self._watched = [(song.view, 'selected_track'),
                         (song.view, 'selected_scene'),
                         (song, 'visible_tracks'), (song, 'scenes'),
                         (song, 'return_tracks')]
        for subject, event in self._watched:
            getattr(subject, 'add_' + event + '_listener')(self._update_ring)
        self._update_ring()
        self._led_ready = True
        self.log_message('SMK37_Custom v1.7 loaded: lower pad4 deletes focused Session clip')
        self.show_message('SMK-37: top=clips; bottom=transport; K1=track K2=scene')

    def _bind(self, control, callback):
        control.add_value_listener(callback)
        self._bindings.append((control, callback))

    def _send_midi(self, midi_event_bytes, optimized=None):
        # Controls have no generic MIDI feedback. RGB uses only our captured codec.
        return False

    def _send_pad_color(self, message):
        result = super(SMK37Custom, self)._send_midi(message, optimized=False)
        self._led_messages += 1
        if self._led_messages <= 3:
            self.log_message('RGB TX {} result={}: {}'.format(
                self._led_messages, result, ' '.join('{:02X}'.format(b) for b in message)))
        return result

    def update_display(self):
        super(SMK37Custom, self).update_display()
        if not self._led_ready:
            return
        self._led_tick += 1
        try:
            colors = colors_for_song(self.song(), self._offset,
                                     (self._led_tick // 5) % 2 == 0)
            self._lights.update(colors)
            self._lights.flush(self._send_pad_color)
            if self._led_tick in (1, 20):
                self.log_message('RGB tick={} TX={} bytes={} pending={}'.format(
                    self._led_tick, self._led_messages, len(self._lights.sent),
                    len(self._lights.pending)))
            self._led_error = None
        except (RuntimeError, AttributeError, IndexError, ValueError) as error:
            message = str(error)
            if message != self._led_error:
                self.log_message('SMK37 RGB: ' + message)
                self._led_error = message

    def refresh_state(self):
        super(SMK37Custom, self).refresh_state()
        if self._led_ready:
            self._lights.sent.clear()

    def _update_ring(self):
        song = self.song()
        self._update_arm_focus()
        self._update_faders()
        tracks = tuple(song.visible_tracks)
        selected = song.view.selected_track
        if selected in tracks:
            index = tracks.index(selected)
            if index < self._offset:
                self._offset = index
            elif index >= self._offset + 8:
                self._offset = index - 7
        self._offset = max(0, min(self._offset, max(0, len(tracks) - 8)))
        scenes = tuple(song.scenes)
        scene = scenes.index(song.view.selected_scene) if scenes else 0
        self._set_session_highlight(self._offset, scene, 8, 1, False)

    def _release_owned_arm(self):
        track = self._owned_arm
        self._owned_arm = None
        if track is not None:
            try:
                if track.arm:
                    track.arm = False
            except RuntimeError:
                pass  # The previously selected track may have been deleted.

    def _update_arm_focus(self):
        if not self._arm_follow:
            return
        track = self.song().view.selected_track
        if track == self._arm_focus:
            return
        self._release_owned_arm()
        self._arm_focus = track
        # An already armed track belongs to the user's manual setup.
        if track.can_be_armed and not track.arm:
            track.arm = True
            self._owned_arm = track

    def _toggle_arm_follow(self):
        track = self.song().view.selected_track
        if not self._arm_follow and track.can_be_armed and track.arm:
            # An explicit press can disarm even a track armed before script load.
            track.arm = False
            self.show_message('SMK-37: {} Arm OFF'.format(track.name))
            return
        self._arm_follow = not self._arm_follow
        self._arm_focus = None
        if self._arm_follow:
            self._update_arm_focus()
        else:
            self._release_owned_arm()
            if track.can_be_armed and track.arm:
                track.arm = False
        self.show_message('SMK-37: Arm follows focus {}'.format(
            'ON' if self._arm_follow else 'OFF'))

    def _update_faders(self):
        mixer = self.song().view.selected_track.mixer_device
        sends = tuple(mixer.sends)
        parameters = [mixer.volume] + [
            sends[index] if index < len(sends) else None for index in range(3)]
        # connect_to only rebuilds the native MIDI mapping when its target changes.
        # Native mappings let Live apply the user's global takeover preference.
        for fader, parameter in zip(self._faders, parameters):
            fader.connect_to(parameter)

    def _navigate(self, axis, value):
        previous = self._last_knob[axis]
        self._last_knob[axis] = value
        if previous is None or value == previous:
            return
        delta = value - previous
        accumulated = self._knob_accumulator[axis]
        # A reversal starts a fresh movement instead of cancelling old residue.
        if accumulated * delta < 0:
            accumulated = 0
        accumulated += delta
        steps = int(accumulated / NAVIGATION_DIVISOR)
        self._knob_accumulator[axis] = accumulated - steps * NAVIGATION_DIVISOR
        if not steps:
            return
        song = self.song()
        items = tuple(song.visible_tracks if axis == 0 else song.scenes)
        if not items:
            return
        selected = song.view.selected_track if axis == 0 else song.view.selected_scene
        position = items.index(selected) if selected in items else 0
        position = max(0, min(len(items) - 1, position + steps))
        if axis == 0:
            song.view.selected_track = items[position]
        else:
            song.view.selected_scene = items[position]
        self._update_ring()
        self.show_message('SMK-37: {} | {}'.format(
            song.view.selected_track.name, song.view.selected_scene.name))

    def _clip(self, column, value):
        try:
            if not value:
                slot = self._held.pop(column, None)
                if slot is not None:
                    slot.set_fire_button_state(False)
                return
            if column in self._held:
                return
            song = self.song()
            tracks = tuple(song.visible_tracks)
            index = self._offset + column
            if index >= len(tracks):
                return
            scene = tuple(song.scenes).index(song.view.selected_scene)
            slot = tracks[index].clip_slots[scene]
            self._held[column] = slot
            slot.set_fire_button_state(True)
        except (RuntimeError, IndexError, ValueError) as error:
            self.log_message('SMK37 clip: {}'.format(error))

    def _transport(self, index, value):
        if not value:
            self._pressed.discard(index)
            return
        if index in self._pressed:
            return
        self._pressed.add(index)
        song = self.song()
        try:
            if index == 0:
                song.start_playing()
            elif index == 1:
                song.stop_playing()
            elif index == 2:
                song.record_mode = not song.record_mode
            elif index == 3:
                slot = focused_slot(song)
                if slot is not None and slot.has_clip:
                    slot.delete_clip()
                    self.show_message('SMK-37: focused clip deleted (Undo: pad 8)')
                else:
                    self.show_message('SMK-37: no clip in focused slot')
            elif index == 4:
                song.loop = not song.loop
            elif index == 5:
                song.metronome = not song.metronome
            elif index == 6:
                self._toggle_arm_follow()
            elif index == 7 and song.can_undo:
                song.undo()
        except RuntimeError as error:
            self.log_message('SMK37 transport: {}'.format(error))
            self.show_message('SMK-37: action unavailable')

    def disconnect(self):
        self._led_ready = False
        self._arm_follow = False
        self._release_owned_arm()
        for fader in self._faders:
            fader.release_parameter()
        for slot in self._held.values():
            try:
                slot.set_fire_button_state(False)
            except RuntimeError:
                pass
        for subject, event in self._watched:
            getattr(subject, 'remove_' + event + '_listener')(self._update_ring)
        for control, callback in self._bindings:
            control.remove_value_listener(callback)
        self._set_session_highlight(-1, -1, -1, -1, False)
        super(SMK37Custom, self).disconnect()
