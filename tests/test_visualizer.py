import unittest
from types import SimpleNamespace

from notch_music import Gst, Notch


@unittest.skipUnless(Gst.ElementFactory.find('spectrum'), 'Spectrum plugin unavailable')
class VisualizerTests(unittest.TestCase):
    def test_audio_messages_distinguish_tone_from_silence(self):
        for volume in (0, .8):
            with self.subTest(volume=volume):
                pipeline = Gst.parse_launch(
                    f'audiotestsrc num-buffers=16 volume={volume} ! '
                    'spectrum name=analyzer bands=32 threshold=-72 interval=40000000 ! fakesink')
                state = SimpleNamespace(spectrum=pipeline.get_by_name('analyzer'),
                                        visualizer_target=[0.0] * 32, visualizer_updated=0)
                try:
                    pipeline.set_state(Gst.State.PLAYING)
                    message = pipeline.get_bus().timed_pop_filtered(Gst.SECOND, Gst.MessageType.ELEMENT)
                    self.assertIsNotNone(message)
                    Notch.message(state, None, message)
                    self.assertGreater(state.visualizer_updated, 0)
                    self.assertEqual(len(state.visualizer_target), 32)
                    self.assertTrue(all(0 <= value <= 1 for value in state.visualizer_target))
                    if volume:
                        self.assertGreater(max(state.visualizer_target), .1)
                    else:
                        self.assertEqual(max(state.visualizer_target), 0)
                finally:
                    pipeline.set_state(Gst.State.NULL)
