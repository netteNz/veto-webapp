# server/veto/management/commands/seed_hcs.py
from django.core.management.base import BaseCommand
from django.db import transaction
from veto.models import Map, GameMode as Mode  # Mode has fields: name (unique), is_objective (bool)

OFFICIAL = {
    "Slayer": [
        "Aquarius", "Live Fire", "Origin", "Recharge", "Solitude", "Streets",
    ],
    "Capture the Flag": [
        "Aquarius", "Forbidden", "Fortress", "Origin",
    ],
    "King of the Hill": [
        "Live Fire", "Recharge", "Lattice",
    ],
    "Oddball": [
        "Live Fire", "Recharge", "Lattice",  # added
    ],
    "Strongholds": [
        "Live Fire", "Recharge", "Lattice",  # added
    ],
    "Neutral Bomb": [
        "Aquarius"
    ],
}

def is_objective_mode(mode_name: str) -> bool:
    return mode_name != "Slayer"

class Command(BaseCommand):
    help = "Seed ONLY the official HCS 2025 maps & modes (+ Lattice: KOTH, Oddball, Strongholds)."

    @transaction.atomic
    def handle(self, *args, **kwargs):
        # Create/ensure modes
        mode_objs = {}
        for mode_name in OFFICIAL.keys():
            obj, _ = Mode.objects.update_or_create(
                name=mode_name,
                defaults={"is_objective": is_objective_mode(mode_name)}
            )
            mode_objs[mode_name] = obj

        # Create/ensure maps & exact combos
        required_maps = set()
        for mode_name, maps in OFFICIAL.items():
            for map_name in maps:
                required_maps.add(map_name)

        # Create maps
        map_objs = {}
        for map_name in required_maps:
            m, _ = Map.objects.get_or_create(name=map_name)
            map_objs[map_name] = m

        # Assign EXACT modes to each map (clear any others)
        # Build reverse index Map -> [Modes]
        map_to_modes = {mn: [] for mn in required_maps}
        for mode_name, maps in OFFICIAL.items():
            for map_name in maps:
                map_to_modes[map_name].append(mode_objs[mode_name])

        # apply sets
        for map_name, modes in map_to_modes.items():
            m = map_objs[map_name]
            m.modes.set(modes)  # overwrites to be exact
            m.save()

        # Remove any maps and modes not in OFFICIAL
        Map.objects.exclude(name__in=required_maps).delete()
        Mode.objects.exclude(name__in=OFFICIAL.keys()).delete()

        self.stdout.write(self.style.SUCCESS("Seeded official HCS 2025 maps & modes (+ Lattice)."))
