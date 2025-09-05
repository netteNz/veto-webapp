from django.contrib import admin
from django import forms
from dal import autocomplete
from import_export.admin import ImportExportModelAdmin
from .models import Map, GameMode, Series, Action, SeriesRound, SeriesBan


# Use django-autocomplete-light for Map.modes
class MapForm(forms.ModelForm):
    class Meta:
        from .models import Map  # local import to avoid circulars in tools
        model = Map
        fields = "__all__"
        widgets = {
            "modes": autocomplete.ModelSelect2Multiple(
                url="gamemode-autocomplete"
            )
        }

@admin.register(Map)
class MapAdmin(ImportExportModelAdmin):
    form = MapForm
    list_display = ("id", "name", "modes_count")
    search_fields = ("name",)
    # `filter_horizontal` replaced by DAL widget
    ordering = ("name",)
    list_per_page = 50

    @admin.display(description="Modes")
    def modes_count(self, obj):
        return obj.modes.count()

@admin.register(GameMode)
class GameModeAdmin(ImportExportModelAdmin):
    list_display = ("id", "name", "is_objective")
    list_filter = ("is_objective",)
    search_fields = ("name",)
    ordering = ("name",)
    list_per_page = 50

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
class SeriesAdmin(ImportExportModelAdmin):
    list_display = ("id", "team_a", "team_b", "state", "series_type", "round_index", "ban_index", "created_at")
    list_filter = ("state", "series_type")
    search_fields = ("team_a", "team_b")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 50
    inlines = [ActionInline, SeriesRoundInline, SeriesBanInline]
    readonly_fields = ("created_at",)  # avoid accidental edits in admin

@admin.register(SeriesRound)
class SeriesRoundAdmin(ImportExportModelAdmin):
    list_display = ("id", "series", "order", "slot_type", "mode", "pick_by", "pick_map", "locked")
    list_filter = ("slot_type", "locked", "mode")
    search_fields = ("series__team_a", "series__team_b", "pick_map__name", "mode__name")
    raw_id_fields = ("series", "mode", "pick_map")
    ordering = ("series", "order")
    list_per_page = 50

@admin.register(SeriesBan)
class SeriesBanAdmin(ImportExportModelAdmin):
    list_display = ("id", "series", "step_index", "by_team", "kind", "objective_mode", "map", "created_at")
    list_filter = ("kind", "by_team", "objective_mode", "map")
    search_fields = ("series__team_a", "series__team_b", "map__name", "objective_mode__name")
    raw_id_fields = ("series", "objective_mode", "map")
    ordering = ("series", "step_index")
    date_hierarchy = "created_at"
    list_per_page = 50

@admin.register(Action)
class ActionAdmin(ImportExportModelAdmin):
    list_display = ("id", "series", "step", "action_type", "team", "map", "mode", "created_at")
    list_filter = ("action_type", "team", "map", "mode")
    search_fields = ("series__team_a", "series__team_b", "map__name", "mode__name")
    raw_id_fields = ("series", "map", "mode")
    date_hierarchy = "created_at"
    list_per_page = 50