import importlib.util
from pathlib import Path
from types import SimpleNamespace as N
import unittest

spec=importlib.util.spec_from_file_location('smk_leds',Path(__file__).resolve().parents[1]/'SMK37_Custom/leds.py')
leds=importlib.util.module_from_spec(spec);spec.loader.exec_module(leds)

class LedTests(unittest.TestCase):
 def test_captured_packets(self):
  expected=[
   'f0 00 32 09 49 00 00 40 02 13 09 00 00 10 00 00 00 00 44 01 f7',
   'f0 00 32 09 49 00 00 40 02 14 09 00 00 10 00 00 00 2a 6e 00 f7',
   'f0 00 32 09 49 00 00 40 02 15 09 00 00 10 00 00 00 7f 43 01 f7']
  self.assertEqual([bytes(m).hex(' ') for m in leds.color_messages(12,(0,42,255))],expected)
 def test_all_rgb_packets_are_bounded_ram_field_writes(self):
  offsets=set()
  for pad in range(16):
   for component,message in enumerate(leds.color_messages(pad,(255,128,0))):
    self.assertEqual((message[0],message[-1]),(240,247))
    raw=[];acc=bits=0
    for byte in message[1:-1]:
     self.assertLess(byte,128)
     acc|=byte<<bits;bits+=7
     while bits>=8:
      raw.append(acc&255);acc>>=8;bits-=8
    self.assertEqual(raw[:7],[0,89,34,9,0,0,5])
    offset=int.from_bytes(bytes(raw[7:11]),'little')
    self.assertEqual(offset,283+74*pad+component)
    self.assertEqual(raw[11:14],[1,0,0])
    self.assertEqual(raw[-1],(~sum(raw[6:-1]))&255)
    self.assertGreater(offset,0);self.assertLessEqual(offset,1395)
    offsets.add(offset)
  self.assertEqual(len(offsets),48)
 def test_queue_coalesces_and_limits(self):
  lights=leds.PadLights();out=[]
  def send(m):out.append(m);return True
  lights.update({8:leds.GREEN,9:leds.PINK})
  lights.flush(send)
  self.assertEqual(len(out),1);self.assertEqual(len(lights.pending),5)
  self.assertEqual(lights.sent[(8,0)],0)
  lights.update({8:leds.CYAN,9:leds.PINK})
  for _ in range(8):lights.flush(send)
  self.assertEqual(lights.pending,{})
  self.assertEqual([lights.sent[(8,i)] for i in range(3)],list(leds.CYAN))
  out.clear();lights.update({8:leds.CYAN,9:leds.PINK});lights.flush(send)
  self.assertEqual(out,[])
  lights.update({8:leds.RED});lights.flush(lambda m:False)
  self.assertEqual(lights.sent[(8,0)],0);self.assertIn((8,0),lights.pending)
  lights.update({8:leds.CYAN});self.assertEqual(lights.pending,{})
 def test_transport_and_clip_states(self):
  clip=N(is_playing=False,is_recording=False)
  slot=N(is_triggered=False,has_clip=True,clip=clip)
  track=N(color=0x123456,can_be_armed=True,arm=False,clip_slots=[slot])
  scene=object()
  song=N(view=N(selected_track=track,selected_scene=scene),visible_tracks=[track],scenes=[scene],is_playing=False,record_mode=False,session_record=False,loop=False,metronome=False,can_undo=False)
  c=leds.colors_for_song(song,0,True)
  self.assertEqual(c[0],leds.dim((18,52,86),0.40));self.assertEqual(c[1],leds.BLACK)
  self.assertEqual(c[8],leds.dim(leds.GREEN));self.assertEqual(c[9],leds.LIGHT_YELLOW)
  clip.is_playing=True
  self.assertEqual(leds.colors_for_song(song,0,True)[0],(18,52,86))
  song.is_playing=True;song.record_mode=True;track.arm=True
  c=leds.colors_for_song(song,0,True)
  self.assertEqual(c[0],leds.dim(leds.RED));self.assertEqual(c[8],leds.GREEN)
  self.assertEqual(c[10],leds.RED);self.assertEqual(c[14],leds.PINK)
  clip.is_recording=True;self.assertEqual(leds.colors_for_song(song,0,True)[0],leds.RED)
  track.arm=False;clip.is_recording=False;slot.is_triggered=True;slot.will_record_on_start=True
  self.assertEqual(leds.colors_for_song(song,0,False)[0],leds.dim(leds.RED))

 def test_armed_focus_tracks_and_scenes(self):
  empty=lambda:N(has_clip=False,is_triggered=False)
  recording=N(has_clip=True,is_triggered=False,clip=N(is_recording=True,is_playing=True))
  first=N(color=0x336699,can_be_armed=True,arm=True,clip_slots=[empty(),recording])
  second=N(color=0x00ff00,can_be_armed=True,arm=True,clip_slots=[empty(),empty()])
  scenes=[object(),object()]
  song=N(view=N(selected_track=first,selected_scene=scenes[0]),visible_tracks=[first,second],scenes=scenes,is_playing=False,record_mode=False,session_record=False,loop=False,metronome=False,can_undo=False)
  self.assertEqual(leds.dim(leds.RED),(51,0,0))
  c=leds.colors_for_song(song,0,True)
  self.assertEqual(c[0],(51,0,0));self.assertEqual(c[1],(0,25,0))
  song.view.selected_scene=scenes[1]
  self.assertEqual(leds.colors_for_song(song,0,True)[0],leds.RED)
  song.view.selected_track=second
  c=leds.colors_for_song(song,0,True)
  self.assertEqual(c[1],(51,0,0));self.assertEqual(c[0],leds.RED)
  song.view.selected_scene=scenes[0]
  c=leds.colors_for_song(song,0,True)
  self.assertEqual(c[0],(5,10,15));self.assertEqual(c[1],(51,0,0))
  second.arm=False
  self.assertEqual(leds.colors_for_song(song,0,True)[1],(0,25,0))

 def test_delete_uses_focused_slot_once_per_press(self):
  import ast
  source=ast.parse((Path(__file__).resolve().parents[1]/'SMK37_Custom/__init__.py').read_text())
  method=next(n for c in source.body if isinstance(c,ast.ClassDef) for n in c.body if isinstance(n,ast.FunctionDef) and n.name=='_transport')
  ns={'focused_slot':leds.focused_slot}
  exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),'transport','exec'),ns)
  calls=[]
  def slot(label):
   result=N(has_clip=True)
   def delete():
    calls.append(label);result.has_clip=False
   result.delete_clip=delete
   return result
  scenes=[object(),object()]
  track=N(clip_slots=[slot('other scene'),slot('target')])
  song=N(view=N(selected_track=track,selected_scene=scenes[1]),scenes=scenes)
  controller=N(_pressed=set(),song=lambda:song,show_message=lambda m:None,log_message=lambda m:None)
  press=lambda value:ns['_transport'](controller,3,value)
  press(127);press(64)
  self.assertEqual(calls,['target']);self.assertTrue(track.clip_slots[0].has_clip)
  press(0);press(127)  # Empty selected slot is a no-op.
  self.assertEqual(calls,['target'])
  press(0);song.view.selected_track=N()  # Return/Main have no clip slots.
  press(127);self.assertEqual(calls,['target'])

if __name__=='__main__':unittest.main()
