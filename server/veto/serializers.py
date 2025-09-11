from rest_framework import serializers
from .models import Series, SeriesBan, SeriesRound, Map, GameMode, Action, BanKind, SlotType

class GameModeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameMode
        fields = ['id', 'name', 'is_objective']

class MapSerializer(serializers.ModelSerializer):
    modes = GameModeSerializer(many=True, read_only=True)
    
    class Meta:
        model = Map
        fields = ['id', 'name', 'modes']

class MapWriteSerializer(serializers.ModelSerializer):
    mode_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Map
        fields = ['id', 'name', 'mode_ids']
    
    def create(self, validated_data):
        mode_ids = validated_data.pop('mode_ids', [])
        map_obj = Map.objects.create(**validated_data)
        if mode_ids:
            map_obj.modes.set(mode_ids)
        return map_obj
    
    def update(self, instance, validated_data):
        mode_ids = validated_data.pop('mode_ids', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if mode_ids is not None:
            instance.modes.set(mode_ids)
        return instance

class ActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Action
        fields = ['id', 'series', 'step', 'action_type', 'team', 'map', 'mode', 'created_at']

class SeriesSerializer(serializers.ModelSerializer):
    actions = serializers.SerializerMethodField()
    
    class Meta:
        model = Series
        fields = ['id', 'team_a', 'team_b', 'created_at', 'state', 'turn', 'actions']
    
    def get_actions(self, obj):
        try:
            actions = []

            # 1) Ban actions from SeriesBan model
            for ban in obj.bans.all():
                # Determine mode_id for Slayer bans
                if ban.kind == BanKind.SLAYER_MAP:
                    slayer_mode = GameMode.objects.filter(name__iexact="Slayer").first()
                    mode_id = slayer_mode.id if slayer_mode else None
                    mode_name = slayer_mode.name if slayer_mode else "Slayer"
                else:
                    mode_id = ban.objective_mode_id
                    mode_name = ban.objective_mode.name if ban.objective_mode else None

                actions.append({
                    "id": f"ban_{ban.id}",
                    "action_type": "BAN",
                    "team": ban.by_team,
                    "map": ban.map_id,
                    "mode": mode_id,
                    "step": ban.step_index,
                    "kind": ban.kind,            # ← ensure this is set
                    "map_name": ban.map.name,    # optional debug
                    "mode_name": mode_name,      # optional debug
                })

            # 2) Pick actions from SeriesRound model
            for rnd in obj.rounds.all():
                if not rnd.pick_map_id:
                    continue

                kind = BanKind.SLAYER_MAP if rnd.slot_type == SlotType.SLAYER else BanKind.OBJECTIVE_COMBO
                actions.append({
                    "id": f"round_{rnd.id}",
                    "action_type": "PICK",
                    "team": rnd.pick_by,
                    "map": rnd.pick_map_id,
                    "mode": rnd.mode_id,
                    "step": rnd.order,
                    "kind": kind,             # ← ensure this is set
                    "slot_type": rnd.slot_type,    # optional debug
                    "map_name": rnd.pick_map.name,
                    "mode_name": rnd.mode.name if rnd.mode else None,
                })

            # 3) Actions from Action model (if any exist)
            for action in obj.actions.all():
                actions.append({
                    'id': action.id,
                    'action_type': action.action_type.upper(),
                    'team': action.team,
                    'map': action.map_id,
                    'mode': action.mode_id,
                    'step': action.step,
                    'kind': getattr(action, 'kind', None),  # Add kind if it exists
                })

            # Sort by step index and return
            return sorted(actions, key=lambda x: x.get("step", 0))
            
        except Exception as e:
            print(f"[DEBUG] Error getting actions: {e}")
            return []
