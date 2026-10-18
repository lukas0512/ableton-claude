from ableton_claude import mixing
import pytest


def test_moves_group_into_broad_regions_and_are_capped():
    moves = [{"hz": 25, "move_db": -2.0}, {"hz": 31.5, "move_db": -3.0},
             {"hz": 40, "move_db": -5.0},                      # sub: average -3.3 -> cap -3
             {"hz": 250, "move_db": 0.5},                      # too small: ignored
             {"hz": 8000, "move_db": 2.0}, {"hz": 10000, "move_db": 2.4},
             {"hz": 12500, "move_db": 2.2}]
    plan = mixing.eq_plan(moves)
    by = {b["region"]: b for b in plan}
    assert set(by) == {"sub", "air"}
    assert by["sub"]["type"] == "Low Shelf" and by["sub"]["gain_db"] == -3.0
    assert 45 < by["sub"]["hz"] < 60                 # shelf corner just above the bands
    assert by["air"]["type"] == "High Shelf" and 2.0 <= by["air"]["gain_db"] <= 2.4
    assert 6000 < by["air"]["hz"] < 8000


def test_loudness_move_respects_the_crest_floor():
    prof = {"loudness": {"integrated_lufs": {"median": -9.3},
                         "crest_db": {"p25": 10.0}}}
    assert mixing.loudness_move(-11.9, 12.0, prof) == 2.0     # crest allows only 2 dB
    assert mixing.loudness_move(-11.9, 16.0, prof) == 2.6     # the full way to the median
    assert mixing.loudness_move(-7.0, 9.0, prof) == -2.3      # too loud: back off


def test_eq_commands_use_bands_two_to_seven_and_switch_off_the_rest():
    plan = mixing.eq_plan([{"hz": 40, "move_db": -2.0}, {"hz": 10000, "move_db": 2.0}])
    cmds = mixing.eq_eight_commands("master", "EQ Eight", plan)
    params = [c["args"]["param"] for c in cmds]
    assert "2 Filter Type A" in params and "3 Filter Type A" in params
    offs = [c for c in cmds if c["args"]["param"].endswith("Filter On A") and c["args"].get("value") == 0]
    assert [c["args"]["param"] for c in offs] == ["1 Filter On A"] + ["%d Filter On A" % n
                                                                        for n in range(4, 9)]


def test_opposite_moves_in_a_region_do_not_average_into_one_bell():
    moves = [{"hz": 400, "move_db": -1.6}, {"hz": 800, "move_db": 2.8},
             {"hz": 1000, "move_db": 3.0}, {"hz": 1250, "move_db": 3.7},
             {"hz": 1600, "move_db": 5.6}]
    (bell,) = mixing.eq_plan(moves)
    assert bell["bands"] == [800, 1000, 1250, 1600] and bell["gain_db"] == 3.0
    assert 1000 < bell["hz"] < 1300


def test_incoherent_region_is_left_alone():
    # hats: peaks and dips alternating up top - a signature, not a tilt
    moves = [{"hz": 4000, "move_db": 1.8}, {"hz": 5000, "move_db": -1.3},
             {"hz": 6300, "move_db": -2.6}, {"hz": 8000, "move_db": 3.7},
             {"hz": 12500, "move_db": -2.8}, {"hz": 16000, "move_db": -4.3}]
    assert mixing.eq_plan(moves) == []


@pytest.mark.parametrize('gain,ceiling', [('Input Gain', 'Ceiling'), ('Gain', 'Ceiling'), ('Gain', 'Output Level')])
def test_limiter_controls_are_discovered_from_actual_parameters(gain, ceiling):
    assert mixing.limiter_controls([{'name': gain, 'display': '+2,5 dB'}, {'name': ceiling}]) == (gain, ceiling, 2.5)
    with pytest.raises(ValueError, match='unambiguous'):
        mixing.limiter_controls([{'name': gain, 'display': '0.5'}, {'name': ceiling}])


def test_master_preflight_fails_before_any_edit_without_supported_final_limiter(monkeypatch):
    from ableton_claude import knowledge, references
    prof = {'loudness': {'integrated_lufs': {'median': -9}, 'crest_db': {'p25': 10}}}
    monkeypatch.setattr(knowledge, 'load_profile', lambda genre: prof)
    monkeypatch.setattr(references, 'compare_to_profile', lambda path, profile: {
        'eq_moves': [], 'notes': [], 'loudness': {'integrated_lufs': -11, 'crest_db': 12}})
    calls = []
    def call(cmd, args):
        calls.append(cmd)
        assert cmd == 'get_track'
        return {'devices': [{'name': 'Utility'}]}
    with pytest.raises(ValueError, match='final device'):
        mixing.toward_profile('mix.wav', 'tech house', apply=True, call=call)
    assert calls == ['get_track']


def test_stock_limiter_master_keeps_limiter_last_and_reports_eq_failure(monkeypatch):
    from ableton_claude import knowledge, references
    prof = {'loudness': {'integrated_lufs': {'median': -9}, 'crest_db': {'p25': 10}}}
    monkeypatch.setattr(knowledge, 'load_profile', lambda genre: prof)
    monkeypatch.setattr(references, 'compare_to_profile', lambda path, profile: {
        'eq_moves': [], 'notes': [], 'loudness': {'integrated_lufs': -11, 'crest_db': 12}})
    for eq_ok in (True, False):
        chain, edits = ['Limiter'], []
        def call(cmd, args):
            if cmd == 'get_track':
                return {'devices': [{'name': n} for n in chain]}
            if cmd == 'get_device':
                return {'params': [{'name': 'Gain', 'display': '0 dB'}, {'name': 'Ceiling'}]}
            edits.append((cmd, args))
            if cmd == 'load_device':
                chain.append('EQ Eight')
            if cmd == 'move_device':
                chain.insert(args['position'], chain.pop(args['device']))
            if cmd == 'batch':
                return [{'ok': eq_ok}]
        result = mixing.toward_profile('mix.wav', 'tech house', apply=True, call=call)
        assert chain == ['EQ Eight', 'Limiter']
        assert result['applied'] is eq_ok
        assert bool([cmd for cmd, _ in edits if cmd == 'set_param']) is eq_ok
