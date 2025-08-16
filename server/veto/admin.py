from django.contrib import admin
from .models import Map, GameMode, Series, Action, SeriesRound, SeriesBan


@admin.register(Map)
class MapAdmin(admin.ModelAdmin):
    list_display = ('id','name')
    search_fields = ('name',)
    filter_horizontal = ('modes',)

@admin.register(GameMode)
class GameModeAdmin(admin.ModelAdmin):
    list_display = ('id','name')
    search_fields = ('name',)

class ActionInline(admin.TabularInline):
    model = Action
    extra = 0

class SeriesRoundInline(admin.TabularInline):
    model = SeriesRound
    extra = 0
    fields = ('order', 'slot_type', 'mode', 'pick_by', 'pick_map', 'locked')
    raw_id_fields = ('mode', 'pick_map')

class SeriesBanInline(admin.TabularInline):
    model = SeriesBan
    extra = 0
    fields = ('step_index', 'by_team', 'kind', 'objective_mode', 'map')
    raw_id_fields = ('objective_mode', 'map')

@admin.register(Series)
class SeriesAdmin(admin.ModelAdmin):
    list_display = ('id','team_a','team_b','state','series_type','round_index','ban_index','created_at')
    list_filter = ('state','series_type')
    search_fields = ('team_a','team_b')
    inlines = [ActionInline, SeriesRoundInline, SeriesBanInline]

@admin.register(SeriesRound)
class SeriesRoundAdmin(admin.ModelAdmin):
    list_display = ('id','series','order','slot_type','mode','pick_by','pick_map','locked')
    list_filter = ('slot_type','locked','mode')
    search_fields = ('series__team_a','series__team_b','pick_map__name','mode__name')
    raw_id_fields = ('series','mode','pick_map')

@admin.register(SeriesBan)
class SeriesBanAdmin(admin.ModelAdmin):
    list_display = ('id','series','step_index','by_team','kind','objective_mode','map','created_at')
    list_filter = ('kind','by_team','objective_mode','map')
    search_fields = ('series__team_a','series__team_b','map__name','objective_mode__name')
    raw_id_fields = ('series','objective_mode','map')

@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    list_display = ('id','series','step','action_type','team','map','mode','created_at')
    list_filter = ('action_type','team','map','mode')
    search_fields = ('series__team_a','series__team_b','map__name','mode__name')