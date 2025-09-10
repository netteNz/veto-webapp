# server/veto/views.py
from django.utils import timezone
from .machine_tsd import TSDMachine, GuardError, TurnError
from django.utils.text import slugify
from rest_framework.decorators import action
from collections import defaultdict
from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from .models import Map, GameMode, Series, Action
from .serializers import (
    MapSerializer, MapWriteSerializer,
    GameModeSerializer, SeriesSerializer, ActionSerializer
)

class HealthView(APIView):
    def get(self, request):
        return Response({
            "status": "ok",
            "service": "veto-api",
            "timestamp": timezone.now().isoformat(),
            "maps": Map.objects.count(),
            "modes": GameMode.objects.count(),
            "series": Series.objects.count(),
            "actions": Action.objects.count(),
        }, status=status.HTTP_200_OK)


class MapViewSet(viewsets.ModelViewSet):
    """
    GET /api/maps/           -> list maps (with modes)
    POST /api/maps/          -> create (use mode_ids)
    PATCH/PUT /api/maps/:id  -> update (use mode_ids)
    """
    queryset = Map.objects.all().prefetch_related('modes')

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return MapWriteSerializer
        return MapSerializer


# Normalize team labels to "A"/"B"
def _as_team_code(series: Series, raw: str) -> str:
    v = (raw or "").strip()
    if v in ("A", "B"):
        return v
    if v == series.team_a:
        return "A"
    if v == series.team_b:
        return "B"
    raise GuardError("Invalid or unknown team")

# Change base class so get_serializer exists
class SeriesViewSet(viewsets.ModelViewSet):
    queryset = Series.objects.all()
    serializer_class = SeriesSerializer

    def create(self, request, *args, **kwargs):
        """Create a new series"""
        try:
            series = Series.objects.create(
                team_a=request.data.get("team_a", "Team A"),
                team_b=request.data.get("team_b", "Team B"),
            )
            serializer = self.get_serializer(series)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            print(f"[DEBUG] Series creation error: {e}")
            return Response(
                {"detail": f"Failed to create series: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    # --- New minimal actions ---

    @action(detail=True, methods=["get"], url_path="state", url_name="series-state")
    def state(self, request, pk=None):
        s = get_object_or_404(Series, pk=pk)
        return Response({"state": s.state}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="veto", url_name="series-veto")
    def veto(self, request, pk=None):
        """
        Minimal placeholder endpoint to record a veto/pick action for tests.
        Accepts: {"team": str, "map": int, "mode": int}
        Creates an Action and returns 201.
        """
        s = get_object_or_404(Series, pk=pk)
        team_label = (request.data.get("team") or "").strip()
        team_code = ""
        if team_label:
            if team_label == s.team_a:
                team_code = "A"
            elif team_label == s.team_b:
                team_code = "B"
        
        # Strict: no fallback to first letter, ensure team matches one of the series teams
        if not team_code:
            return Response(
                {"detail": "Invalid or missing team"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            map_obj = Map.objects.get(pk=request.data.get("map"))
            mode_obj = GameMode.objects.get(pk=request.data.get("mode"))
        except (Map.DoesNotExist, GameMode.DoesNotExist):
            return Response(
                {"detail": "Invalid map or mode"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        step = (s.actions.count() or 0) + 1

        act = Action.objects.create(
            series=s,
            step=step,
            action_type=Action.BAN,
            team=team_code,
            map=map_obj,
            mode=mode_obj,
        )
        return Response(ActionSerializer(act).data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=["post"], url_path="assign_roles", url_name="series-assign-roles")
    def assign_roles(self, request, pk=None):
        m = TSDMachine(pk)
        team_a = request.data.get("team_a", "").strip()
        team_b = request.data.get("team_b", "").strip()

        if not team_a or not team_b:
            return Response({"detail": "Both team_a and team_b are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            m.assign_roles(team_a=team_a, team_b=team_b)
            return Response({"detail": "Roles assigned"}, status=status.HTTP_200_OK)
        except GuardError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=True, methods=["post"], url_path="confirm_tsd", url_name="series-confirm-tsd")
    def confirm_tsd(self, request, pk=None):
        m = TSDMachine(pk)
        series_type = request.data.get("series_type", "").strip()

        if not series_type:
            return Response({"detail": "Missing series_type"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            m.confirm_tsd(series_type=series_type)
            return Response({"detail": "Series confirmed"}, status=status.HTTP_200_OK)
        except GuardError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


    @action(detail=True, methods=["post"], url_name="series-reset")
    def reset(self, request, pk=None):
        """Reset the series using TSD machine"""
        try:
            m = TSDMachine(pk)
            m.reset()  # ✅ This method exists in your TSD machine
            return Response({"detail": "Series reset successfully"}, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"[DEBUG] Reset error: {e}")
            return Response({"detail": f"Reset error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=["post"], url_name="series-undo")
    def undo(self, request, pk=None):
        """Undo the last action using TSD machine"""
        try:
            m = TSDMachine(pk)
            m.undo_last()  # ✅ Change from m.undo() to m.undo_last()
            return Response({"detail": "Last action undone successfully"}, status=status.HTTP_200_OK)
            
        except (GuardError, TurnError) as e:
            print(f"[DEBUG] Undo error: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"[DEBUG] Undo error: {e}")
            return Response({"detail": f"Undo error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=["post"], url_path="ban_objective_combo", url_name="series-ban-objective-combo")
    def ban_objective_combo(self, request, pk=None):
        """Ban an objective combo using TSD machine"""
        try:
            s = get_object_or_404(Series, pk=pk)
            team_raw = request.data.get("team")
            map_id = request.data.get("map_id") or request.data.get("map")
            mode_id = (request.data.get("objective_mode_id")
                       or request.data.get("mode_id")
                       or request.data.get("mode"))
            if not all([team_raw, map_id, mode_id]):
                return Response({"detail": "team, map/map_id, and mode/mode_id are required"},
                                status=status.HTTP_400_BAD_REQUEST)
            team = _as_team_code(s, team_raw)
            TSDMachine(pk).ban_objective_combo(team, int(mode_id), int(map_id))
            return Response({"detail": "Objective combo banned"}, status=status.HTTP_200_OK)
        except (GuardError, TurnError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="ban_slayer_map", url_name="series-ban-slayer-map")
    def ban_slayer_map(self, request, pk=None):
        """Ban a slayer map using TSD machine"""
        try:
            s = get_object_or_404(Series, pk=pk)
            team_raw = request.data.get("team")
            map_id = request.data.get("map_id") or request.data.get("map")
            if not all([team_raw, map_id]):
                return Response({"detail": "team and map/map_id are required"},
                                status=status.HTTP_400_BAD_REQUEST)
            team = _as_team_code(s, team_raw)
            TSDMachine(pk).ban_slayer_map(team, int(map_id))
            return Response({"detail": "Slayer map banned"}, status=status.HTTP_200_OK)
        except (GuardError, TurnError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


    @action(detail=True, methods=["post"], url_path="pick_objective_combo", url_name="series-pick-objective-combo")
    def pick_objective_combo(self, request, pk=None):
        """Pick an objective combo using TSD machine"""
        try:
            s = get_object_or_404(Series, pk=pk)
            team_raw = request.data.get("team")
            map_id = request.data.get("map") or request.data.get("map_id")
            mode_id = request.data.get("mode") or request.data.get("mode_id") or request.data.get("objective_mode_id")
            if not all([team_raw, map_id, mode_id]):
                return Response({"detail": "team, map/map_id, and mode/mode_id are required"},
                                status=status.HTTP_400_BAD_REQUEST)
            team = _as_team_code(s, team_raw)
            TSDMachine(pk).pick_objective_combo(team, int(mode_id), int(map_id))
            return Response({"detail": "Objective combo picked"}, status=status.HTTP_200_OK)
        except (GuardError, TurnError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="pick_slayer_map", url_name="series-pick-slayer-map")
    def pick_slayer_map(self, request, pk=None):
        """Pick a slayer map using TSD machine"""
        try:
            s = get_object_or_404(Series, pk=pk)
            team_raw = request.data.get("team")
            map_id = request.data.get("map") or request.data.get("map_id")
            if not all([team_raw, map_id]):
                return Response({"detail": "team and map/map_id are required"},
                                status=status.HTTP_400_BAD_REQUEST)
            team = _as_team_code(s, team_raw)
            TSDMachine(pk).pick_slayer_map(team, int(map_id))
            return Response({"detail": "Slayer map picked"}, status=status.HTTP_200_OK)
        except (GuardError, TurnError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    # ...existing code...

class ActionViewSet(viewsets.ModelViewSet):
    """
    CRUD for actions. On create/update, ensure the chosen mode is valid for the chosen map.
    """
    queryset = Action.objects.select_related('series', 'map', 'mode')
    serializer_class = ActionSerializer

    def _validate_map_mode(self, serializer):
        map_obj = serializer.validated_data.get('map')
        mode_obj = serializer.validated_data.get('mode')
        if map_obj and mode_obj and not map_obj.modes.filter(pk=mode_obj.pk).exists():
            raise ValidationError({"mode": "Selected mode is not allowed on this map."})

    def perform_create(self, serializer):
        self._validate_map_mode(serializer)
        serializer.save()

    def perform_update(self, serializer):
        self._validate_map_mode(serializer)
        serializer.save()


class MapModeComboView(APIView):
    """
    Flat list of allowed Map × Mode combos.

    Filters:
      ?mode=Slayer                -> only that mode
      ?type=objective|slayer      -> objective excludes Slayer (by flag), slayer == Slayer only
    """
    def get(self, request):
        q_mode = request.GET.get("mode")
        q_type = request.GET.get("type")  # objective | slayer

        combos = []
        maps = Map.objects.all().prefetch_related("modes")

        for m in maps:
            for gm in m.modes.all():
                if q_mode and gm.name.lower() != q_mode.lower():
                    continue

                # determine objective vs slayer
                # prefer the flag; fall back to name check if ever missing
                is_obj = getattr(gm, "is_objective", None)
                if is_obj is None:
                    is_obj = (gm.name != "Slayer")

                if q_type:
                    want_obj = (q_type.lower() == "objective")
                    if want_obj != bool(is_obj):
                        continue

                combos.append({
                    "map_id": m.id,
                    "map": m.name,
                    "mode_id": gm.id,
                    "mode": gm.name,
                    "is_objective": bool(is_obj),
                    "slug": f"{slugify(m.name)}--{slugify(gm.name)}"
                })

        combos.sort(key=lambda x: (x["mode"], x["map"]))
        return Response(combos, status=status.HTTP_200_OK)

class MapModeGroupedView(APIView):
    """
    Returns combos grouped by Objective vs Slayer, then by Mode.

    GET /api/maps/combos/grouped/
      ?type=objective|slayer   # optional
      ?mode=Slayer             # optional (filters to a single mode)
    Response shape:
    {
      "objective": [
        { "mode_id": 4, "mode": "King of the Hill", "combos": [ {map_id, map, slug}, ... ] },
        ...
      ],
      "slayer": [
        { "mode_id": 1, "mode": "Slayer", "combos": [ ... ] }
      ]
    }
    """
    def get(self, request):
        q_type = (request.GET.get("type") or "").lower()  # objective|slayer|""(all)
        q_mode = request.GET.get("mode")

        maps = Map.objects.all().prefetch_related("modes")

        # mode_id -> {"mode_id", "mode", "is_objective", "combos":[{map_id,map,slug}]}
        bucket = {}

        for m in maps:
            for gm in m.modes.all():
                # filter by single mode (exact, case-insensitive)
                if q_mode and gm.name.lower() != q_mode.lower():
                    continue

                is_obj = bool(gm.is_objective) if gm.is_objective is not None else (gm.name != "Slayer")
                if q_type:
                    want_obj = (q_type == "objective")
                    if want_obj != is_obj:
                        continue

                if gm.id not in bucket:
                    bucket[gm.id] = {
                        "mode_id": gm.id,
                        "mode": gm.name,
                        "is_objective": is_obj,
                        "combos": []
                    }
                bucket[gm.id]["combos"].append({
                    "map_id": m.id,
                    "map": m.name,
                    "slug": f"{slugify(m.name)}--{slugify(gm.name)}"
                })

        # sort combos by map name
        for v in bucket.values():
            v["combos"].sort(key=lambda x: x["map"])

        # split into objective vs slayer arrays
        objective = []
        slayer = []
        for v in bucket.values():
            (objective if v["is_objective"] else slayer).append(v)

        # sort modes alphabetically within each group
        objective.sort(key=lambda x: x["mode"])
        slayer.sort(key=lambda x: x["mode"])

        return Response({"objective": objective, "slayer": slayer}, status=status.HTTP_200_OK)


class GameModeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GameMode.objects.all().order_by('name')
    serializer_class = GameModeSerializer