# /veto/machine_tsd.py
from django.db import transaction
from django.utils import timezone
from transitions import Machine
from .models import (
    Series, SeriesState, SeriesRound, SeriesBan,
    SlotType, BanKind, GameMode, Map
)

# 7-step ban schedule (A×3 Objective-combo, B×2 Objective-combo, B×1 Slayer, A×1 Slayer)
BAN_SCHEDULE = [
    ("A", BanKind.OBJECTIVE_COMBO),
    ("B", BanKind.OBJECTIVE_COMBO),
    ("A", BanKind.OBJECTIVE_COMBO),
    ("B", BanKind.OBJECTIVE_COMBO),
    ("A", BanKind.OBJECTIVE_COMBO),
    ("B", BanKind.SLAYER_MAP),
    ("A", BanKind.SLAYER_MAP),
]

ROUND_SLOTS = {
    "Bo3": [SlotType.OBJECTIVE, SlotType.SLAYER, SlotType.OBJECTIVE],
    "Bo5": [SlotType.OBJECTIVE, SlotType.SLAYER, SlotType.OBJECTIVE, SlotType.OBJECTIVE, SlotType.SLAYER],
    "Bo7": [SlotType.OBJECTIVE, SlotType.SLAYER, SlotType.OBJECTIVE, SlotType.OBJECTIVE, SlotType.SLAYER, SlotType.OBJECTIVE, SlotType.SLAYER],
}

def picking_team_for_game(game_number: int) -> str:
    # Odd games -> Team B picks; Even -> Team A picks
    return "B" if game_number % 2 == 1 else "A"

class TSDMachineError(Exception): ...
class GuardError(TSDMachineError): ...
class TurnError(TSDMachineError): ...

class TSDMachine:
    def __init__(self, series_id: int):
        self.series_id = series_id

        states = ['IDLE', 'BANNING', 'PICKING', 'FINALIZED']

        transitions = [
            {'trigger': 'start_banning', 'source': 'IDLE', 'dest': 'BANNING'},
            {'trigger': 'start_picking', 'source': 'BANNING', 'dest': 'PICKING'},
            {'trigger': 'finalize', 'source': 'PICKING', 'dest': 'FINALIZED'},
            {'trigger': 'reset', 'source': '*', 'dest': 'IDLE'},
        ]

        # Initialize the state machine with the current state from the model
        super().__init__(model=self, states=states, transitions=transitions, initial=series.state)

        # Persist state back to the model on every transition
        self.on_transition += self._sync_state_to_model

    def _sync_state_to_model(self, event):
        self.series.state = self.state
        self.series.save()

    # ---- helpers ----
    def _expect_turn(self, s: Series, team: str, action: str, kind: str | None = None):
        t = s.turn or {}
        if t.get("team") != team or t.get("action") != action:
            raise TurnError("Not your turn")
        if kind and t.get("kind") != kind:
            raise TurnError(f"Wrong action kind (expected {kind})")

    def _start_ban_phase(self, s: Series):
        s.state = SeriesState.BAN_PHASE
        s.ban_index = 0
        team, kind = BAN_SCHEDULE[0]
        s.turn = {"team": team, "action": "BAN", "kind": kind}
        s.save(update_fields=["state","ban_index","turn"])

    def _advance_ban_turn(self, s: Series):
        idx = s.ban_index + 1
        if idx < len(BAN_SCHEDULE):
            team, kind = BAN_SCHEDULE[idx]
            s.ban_index = idx
            s.turn = {"team": team, "action": "BAN", "kind": kind}
            s.save(update_fields=["ban_index","turn"])
        else:
            # Move to Game 1 pick
            s.ban_index = idx
            s.state = SeriesState.PICK_WINDOW
            s.round_index = 0
            game_no = 1
            slot = s.rounds.get(order=0).slot_type
            kind = BanKind.OBJECTIVE_COMBO if slot == SlotType.OBJECTIVE else BanKind.SLAYER_MAP
            s.turn = {"team": picking_team_for_game(game_no), "action": "PICK", "kind": kind}
            s.save(update_fields=["ban_index","state","round_index","turn"])

    def _map_unused(self, s: Series, m: Map) -> bool:
        return not SeriesRound.objects.filter(series=s, pick_map=m).exists()

    # ---- API entrypoints (each atomic) ----

    @transaction.atomic
    def confirm_tsd(self, series_type: str, ruleset="TSD_8s_v2"):
        s = Series.objects.select_for_update().get(pk=self.series_id)
        if s.state not in [SeriesState.IDLE, SeriesState.SERIES_SETUP]:
            raise GuardError("Series already configured")
        if series_type not in ROUND_SLOTS:
            raise GuardError("Invalid series_type")
        s.ruleset = ruleset
        s.series_type = series_type
        s.rounds.all().delete()
        for i, slot in enumerate(ROUND_SLOTS[series_type]):
            SeriesRound.objects.create(series=s, order=i, slot_type=slot)
        self._start_ban_phase(s)
        return s

    @transaction.atomic
    def assign_roles(self, team_a: str, team_b: str):
        s = Series.objects.select_for_update().get(pk=self.series_id)
        if s.state != SeriesState.IDLE:
            raise GuardError("Roles can only be assigned in IDLE")
        s.team_a = team_a
        s.team_b = team_b
        s.state = SeriesState.SERIES_SETUP
        s.save(update_fields=["team_a","team_b","state"])
        return s

    @transaction.atomic
    def ban_objective_combo(self, team: str, objective_mode_id: int, map_id: int):
        s = Series.objects.select_for_update().get(pk=self.series_id)
        self._expect_turn(s, team, "BAN", BanKind.OBJECTIVE_COMBO)
        if s.state != SeriesState.BAN_PHASE:
            raise GuardError("Not in ban phase")

        mode = GameMode.objects.get(pk=objective_mode_id)
        if not mode.is_objective:
            raise GuardError("Mode must be objective")
        m = Map.objects.get(pk=map_id)
        if not m.modes.filter(pk=mode.pk).exists():
            raise GuardError("Map does not support this objective")
        if SeriesBan.objects.filter(series=s, kind=BanKind.OBJECTIVE_COMBO, objective_mode=mode, map=m).exists():
            raise GuardError("That combo is already banned")

        SeriesBan.objects.create(
            series=s, step_index=s.ban_index, by_team=team,
            kind=BanKind.OBJECTIVE_COMBO, map=m, objective_mode=mode
        )
        self._advance_ban_turn(s)
        return s

    @transaction.atomic
    def ban_slayer_map(self, team: str, map_id: int):
        s = Series.objects.select_for_update().get(pk=self.series_id)
        self._expect_turn(s, team, "BAN", BanKind.SLAYER_MAP)
        if s.state != SeriesState.BAN_PHASE:
            raise GuardError("Not in ban phase")

        m = Map.objects.get(pk=map_id)
        if not m.modes.filter(name="Slayer").exists():
            raise GuardError("Map is not valid for Slayer")
        if SeriesBan.objects.filter(series=s, kind=BanKind.SLAYER_MAP, map=m).exists():
            raise GuardError("That Slayer map is already banned")

        SeriesBan.objects.create(
            series=s, step_index=s.ban_index, by_team=team,
            kind=BanKind.SLAYER_MAP, map=m
        )
        self._advance_ban_turn(s)
        return s

    @transaction.atomic
    def pick_objective_combo(self, team: str, objective_mode_id: int, map_id: int):
        s = Series.objects.select_for_update().get(pk=self.series_id)
        self._expect_turn(s, team, "PICK", BanKind.OBJECTIVE_COMBO)
        if s.state != SeriesState.PICK_WINDOW:
            raise GuardError("Not in pick window")

        r = s.rounds.get(order=s.round_index)
        if r.slot_type != SlotType.OBJECTIVE:
            raise GuardError("This round is not Objective")

        mode = GameMode.objects.get(pk=objective_mode_id)
        m = Map.objects.get(pk=map_id)
        if not mode.is_objective or not m.modes.filter(pk=mode.pk).exists():
            raise GuardError("Invalid objective combo")
        if SeriesBan.objects.filter(series=s, kind=BanKind.OBJECTIVE_COMBO, objective_mode=mode, map=m).exists():
            raise GuardError("Combo is banned")
        if not self._map_unused(s, m):
            raise GuardError("Map already used in this series")

        r.mode = mode
        r.pick_by = team
        r.pick_map = m
        r.locked = True
        r.save(update_fields=["mode","pick_by","pick_map","locked"])
        self._advance_round_after_pick(s)
        return s

    @transaction.atomic
    def pick_slayer_map(self, team: str, map_id: int):
        s = Series.objects.select_for_update().get(pk=self.series_id)
        self._expect_turn(s, team, "PICK", BanKind.SLAYER_MAP)
        if s.state != SeriesState.PICK_WINDOW:
            raise GuardError("Not in pick window")

        r = s.rounds.get(order=s.round_index)
        if r.slot_type != SlotType.SLAYER:
            raise GuardError("This round is not Slayer")

        m = Map.objects.get(pk=map_id)
        if not m.modes.filter(name="Slayer").exists():
            raise GuardError("Map is not valid for Slayer")
        if SeriesBan.objects.filter(series=s, kind=BanKind.SLAYER_MAP, map=m).exists():
            raise GuardError("This Slayer map is banned")
        if not self._map_unused(s, m):
            raise GuardError("Map already used in this series")

        slayer = GameMode.objects.get(name="Slayer")
        r.mode = slayer
        r.pick_by = team
        r.pick_map = m
        r.locked = True
        r.save(update_fields=["mode","pick_by","pick_map","locked"])
        self._advance_round_after_pick(s)
        return s

    def _advance_round_after_pick(self, s: Series):
        last = s.rounds.count() - 1
        if s.round_index < last:
            s.round_index += 1
            next_game = s.round_index + 1
            slot = s.rounds.get(order=s.round_index).slot_type
            kind = BanKind.OBJECTIVE_COMBO if slot == SlotType.OBJECTIVE else BanKind.SLAYER_MAP
            s.state = SeriesState.PICK_WINDOW
            s.turn = {"team": picking_team_for_game(next_game), "action": "PICK", "kind": kind}
        else:
            s.state = SeriesState.SERIES_COMPLETE
            s.turn = {}
        s.save(update_fields=["round_index","state","turn"])

    @transaction.atomic
    def undo_last(self):
        # minimal, safe undo: delete last ban if in BAN_PHASE, else reopen last locked round in PICK_WINDOW
        s = Series.objects.select_for_update().get(pk=self.series_id)
        if s.state == SeriesState.BAN_PHASE:
            last_ban = s.bans.order_by('-step_index','-id').first()
            if not last_ban:
                raise GuardError("Nothing to undo")
            last_ban.delete()
            # reset turn to that step
            s.ban_index = last_ban.step_index
            team, kind = BAN_SCHEDULE[s.ban_index]
            s.turn = {"team": team, "action": "BAN", "kind": kind}
            s.save(update_fields=["ban_index","turn"])
            return s

        if s.state == SeriesState.PICK_WINDOW:
            # if current round has a pick_map, roll it back; else, go to previous round
            try:
                r = s.rounds.get(order=s.round_index)
            except SeriesRound.DoesNotExist:
                raise GuardError("Nothing to undo")
            if r.pick_map_id:
                r.mode = None
                r.pick_by = ""
                r.pick_map = None
                r.locked = False
                r.save(update_fields=["mode","pick_by","pick_map","locked"])
                # recompute turn for this round
                game_no = s.round_index + 1
                kind = BanKind.OBJECTIVE_COMBO if r.slot_type == SlotType.OBJECTIVE else BanKind.SLAYER_MAP
                s.turn = {"team": picking_team_for_game(game_no), "action":"PICK", "kind": kind}
                s.save(update_fields=["turn"])
                return s
            # move to previous round if exists
            if s.round_index == 0:
                raise GuardError("Nothing to undo")
            s.round_index -= 1
            r = s.rounds.get(order=s.round_index)
            r.mode = None
            r.pick_by = ""
            r.pick_map = None
            r.locked = False
            r.save(update_fields=["mode","pick_by","pick_map","locked"])
            game_no = s.round_index + 1
            kind = BanKind.OBJECTIVE_COMBO if r.slot_type == SlotType.OBJECTIVE else BanKind.SLAYER_MAP
            s.turn = {"team": picking_team_for_game(game_no), "action":"PICK", "kind": kind}
            s.save(update_fields=["round_index","turn"])
            return s

        raise GuardError("Undo not available in current state")

    @transaction.atomic
    def reset(self):
        s = Series.objects.select_for_update().get(pk=self.series_id)
        s.bans.all().delete()
        s.rounds.all().delete()
        s.ruleset = ""
        s.series_type = ""
        s.round_index = 0
        s.ban_index = 0
        s.turn = {}
        s.state = SeriesState.IDLE
        s.save(update_fields=["ruleset","series_type","round_index","ban_index","turn","state"])
        return s