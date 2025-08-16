from django.db import models

class GameMode(models.Model):
    """Optional: normalize game modes (Slayer, CTF, Strongholds, Oddball, KOTH, etc.)"""
    name = models.CharField(max_length=64, unique=True)
    is_objective = models.BooleanField(default=False)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class SeriesState(models.TextChoices):
    IDLE = "IDLE", "Idle"
    SERIES_SETUP = "SERIES_SETUP", "Series Setup"
    BAN_PHASE = "BAN_PHASE", "Ban Phase"
    PICK_WINDOW = "PICK_WINDOW", "Pick Window"
    SERIES_COMPLETE = "SERIES_COMPLETE", "Series Complete"
    ABORTED = "ABORTED", "Aborted"

class SlotType(models.TextChoices):
    OBJECTIVE = "OBJECTIVE", "Objective"
    SLAYER = "SLAYER", "Slayer"

class BanKind(models.TextChoices):
    OBJECTIVE_COMBO = "OBJECTIVE_COMBO", "Objective + Map"
    SLAYER_MAP = "SLAYER_MAP", "Slayer Map"


class Map(models.Model):
    name = models.CharField(max_length=128, unique=True)
    # Many-to-many: which modes are valid on this map
    modes = models.ManyToManyField(GameMode, related_name='maps', blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Series(models.Model):
    team_a = models.CharField(max_length=64)
    team_b = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    # --- State machine fields (TSD $8s ruleset) ---
    state = models.CharField(max_length=32, choices=SeriesState.choices, default=SeriesState.IDLE)
    ruleset = models.CharField(max_length=32, blank=True, default="")
    series_type = models.CharField(max_length=8, blank=True, default="")  # "Bo3" | "Bo5" | "Bo7"
    round_index = models.PositiveIntegerField(default=0)
    ban_index = models.PositiveIntegerField(default=0)
    turn = models.JSONField(default=dict, blank=True)  # {"team":"A|B","action":"BAN|PICK","kind":"OBJECTIVE_COMBO|SLAYER_MAP"}

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.team_a} vs {self.team_b} (#{self.id})"

# ---- SeriesRound and SeriesBan models ----
class SeriesRound(models.Model):
    """
    Per-round slot for the series. For OBJECTIVE slots, the concrete mode is chosen on pick time.
    For SLAYER slots, mode is set to the Slayer GameMode on pick.
    """
    series = models.ForeignKey('Series', on_delete=models.CASCADE, related_name='rounds')
    order = models.PositiveIntegerField()  # 0..N-1
    slot_type = models.CharField(max_length=16, choices=SlotType.choices)

    # Filled when a pick is made
    mode = models.ForeignKey('GameMode', null=True, blank=True, on_delete=models.PROTECT)
    pick_by = models.CharField(max_length=1, blank=True)  # "A" or "B"
    pick_map = models.ForeignKey('Map', null=True, blank=True, on_delete=models.PROTECT)
    locked = models.BooleanField(default=False)

    class Meta:
        unique_together = ('series', 'order')
        ordering = ['order']

    def __str__(self):
        base = f"Game {self.order + 1}: {self.slot_type}"
        if self.pick_map_id:
            return f"{base} • {self.mode.name if self.mode_id else '—'} on {self.pick_map.name} ({self.pick_by})"
        return f"{base} • (pending)"

class SeriesBan(models.Model):
    """
    Immutable bans captured during the 7-step ban phase.
    OBJECTIVE_COMBO bans require both objective_mode and map.
    SLAYER_MAP bans only require a map.
    """
    series = models.ForeignKey('Series', on_delete=models.CASCADE, related_name='bans')
    step_index = models.PositiveIntegerField()  # 0..6
    by_team = models.CharField(max_length=1)    # "A" | "B"
    kind = models.CharField(max_length=32, choices=BanKind.choices)

    # Slayer map bans use only `map`
    map = models.ForeignKey('Map', on_delete=models.PROTECT)

    # Objective+Map bans include the objective mode used in the ban
    objective_mode = models.ForeignKey('GameMode', null=True, blank=True, on_delete=models.PROTECT)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('series', 'step_index')
        ordering = ['step_index', 'id']

    def __str__(self):
        if self.kind == BanKind.SLAYER_MAP:
            return f"{self.by_team} banned Slayer on {self.map.name} (step {self.step_index})"
        return f"{self.by_team} banned {self.objective_mode.name if self.objective_mode_id else 'Objective'} on {self.map.name} (step {self.step_index})"

class Action(models.Model):
    BAN = 'ban'
    PICK = 'pick'
    ACTION_TYPES = [
        (BAN, 'Ban'),
        (PICK, 'Pick'),
    ]

    series = models.ForeignKey(Series, on_delete=models.CASCADE, related_name='actions')
    step = models.PositiveIntegerField()
    action_type = models.CharField(max_length=8, choices=ACTION_TYPES)
    team = models.CharField(max_length=1)  # 'A' or 'B'
    map = models.ForeignKey(Map, on_delete=models.PROTECT)
    mode = models.ForeignKey(GameMode, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            ('series', 'step'),
        )
        ordering = ['step', 'id']

    def __str__(self):
        return f"{self.get_action_type_display()} {self.map.name} {self.mode.name} (step {self.step})"
