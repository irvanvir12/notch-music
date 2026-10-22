import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from notch_music import Notch


def player(index=1):
    state = SimpleNamespace(queue=['a', 'b', 'c'], index=index, playing=True,
                            shuffle_remaining=[0, 2], history=[0, 1, 2],
                            drawer_mode=None, update_status=Mock(), reset_player=Mock(),
                            load=Mock(), player=Mock(), sync_play_icons=Mock())
    return state


class QueueTests(unittest.TestCase):
    def test_remove_before_current_remaps_indices_without_restart(self):
        state = player()
        Notch.remove_track(state, 0)
        self.assertEqual(state.queue, ['b', 'c'])
        self.assertEqual(state.index, 0)
        self.assertEqual(state.shuffle_remaining, [1])
        self.assertEqual(state.history, [0, 1])
        state.load.assert_not_called()

    def test_remove_current_advances_to_successor(self):
        state = player()
        Notch.remove_track(state, 1)
        self.assertEqual(state.queue, ['a', 'c'])
        state.load.assert_called_once_with(1)

    def test_clear_stops_and_empties_queue(self):
        state = player()
        Notch.clear_queue(state)
        self.assertEqual(state.queue, [])
        self.assertEqual(state.history, [])
        self.assertEqual(state.shuffle_remaining, [])
        state.reset_player.assert_called_once()

    def test_repeat_modes_at_end(self):
        for repeat, expected in [(0, 'stop'), (1, 'same'), (2, 'next')]:
            state = SimpleNamespace(queue=['a', 'b'], index=1, repeat_mode=repeat,
                                    shuffle=False, load=Mock(), step=Mock(), stop_at_end=Mock())
            Notch.end_of_track(state)
            if expected == 'stop':
                state.stop_at_end.assert_called_once()
            elif expected == 'same':
                state.load.assert_called_once_with(1)
            else:
                state.step.assert_called_once_with(1)

    def test_shuffle_without_repeat_stops_after_cycle(self):
        state = SimpleNamespace(queue=['a', 'b'], index=0, repeat_mode=0,
                                shuffle=True, shuffle_remaining=[], stop_at_end=Mock(), step=Mock())
        Notch.end_of_track(state)
        state.stop_at_end.assert_called_once()
        state.step.assert_not_called()


if __name__ == '__main__':
    unittest.main()
