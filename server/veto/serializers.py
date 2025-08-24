from rest_framework import serializers
from .models import Series, SeriesBan, SeriesRound, Map, GameMode, Action

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
            # Get data from the Action model (which has related_name='actions')
            actions = []
            for action in obj.actions.all():
                actions.append({
                    'id': action.id,
                    'action_type': action.action_type.upper(),
                    'team': action.team,
                    'map': action.map_id,
                    'mode': action.mode_id,
                    'step': action.step
                })
            
            # Also get data from SeriesBan model (which has related_name='bans')
            for ban in obj.bans.all():
                actions.append({
                    'id': f"ban_{ban.id}",
                    'action_type': 'BAN',
                    'team': ban.by_team,
                    'map': ban.map_id,
                    'mode': ban.objective_mode_id,
                    'step': ban.step_index
                })
            
            # Get data from SeriesRound model (which has related_name='rounds')
            for round_obj in obj.rounds.all():
                if round_obj.pick_map_id:  # Only include if actually picked
                    actions.append({
                        'id': f"round_{round_obj.id}",
                        'action_type': 'PICK',
                        'team': round_obj.pick_by,
                        'map': round_obj.pick_map_id,
                        'mode': round_obj.mode_id,
                        'step': round_obj.order
                    })
            
            # Sort by step
            return sorted(actions, key=lambda x: x.get('step', 0))
            
        except Exception as e:
            print(f"[DEBUG] Error getting actions: {e}")
            return []
