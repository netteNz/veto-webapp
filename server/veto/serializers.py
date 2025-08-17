from rest_framework import serializers
from .models import Map, GameMode, Series, Action

class GameModeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameMode
        fields = ['id','name']

class MapSerializer(serializers.ModelSerializer):
    modes = GameModeSerializer(many=True, read_only=True)

    class Meta:
        model = Map
        fields = ['id','name','modes']

class MapWriteSerializer(serializers.ModelSerializer):
    mode_ids = serializers.PrimaryKeyRelatedField(many=True, write_only=True, queryset=GameMode.objects.all(), source='modes')

    class Meta:
        model = Map
        fields = ['id','name','mode_ids']

class ActionSerializer(serializers.ModelSerializer):
    map = serializers.PrimaryKeyRelatedField(queryset=Map.objects.all())
    mode = serializers.PrimaryKeyRelatedField(queryset=GameMode.objects.all())

    class Meta:
        model = Action
        fields = ['id','series','step','action_type','team','map','mode','created_at']
        read_only_fields = ['created_at']

class SeriesSerializer(serializers.ModelSerializer):
    actions = ActionSerializer(many=True, read_only=True)

    class Meta:
        model = Series
        fields = [
            'id',
            'team_a',
            'team_b',
            'created_at',
            'actions',
            'state',  # ✅ ADD THIS LINE
        ]
        read_only_fields = ['created_at']
