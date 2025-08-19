import pytest
from django.test import TestCase
from django.urls import reverse


@pytest.mark.django_db
class VetoSeriesFlowTests(TestCase):

    def setUp(self):
        from rest_framework.test import APIClient
        from veto.models import Series, Map, GameMode

        self.client = APIClient()

        # Create game modes
        self.slayer_mode = GameMode.objects.create(name="Slayer", is_objective=False)
        self.koth_mode = GameMode.objects.create(name="King of the Hill", is_objective=True)

        # Create maps
        self.map1 = Map.objects.create(name="Guardian")
        self.map1.modes.set([self.slayer_mode, self.koth_mode])

        self.map2 = Map.objects.create(name="Lockout")
        self.map2.modes.set([self.slayer_mode])

        # Create series
        self.series = Series.objects.create(
            team_a="Team Alpha",
            team_b="Team Beta",
            state="IDLE"
        )

    def test_create_action_via_veto_endpoint(self):
        from rest_framework import status
        from veto.models import Action

        url = reverse('series-series-veto', kwargs={'pk': self.series.pk})
        data = {
            'team': 'Team Alpha',
            'map': self.map1.pk,
            'mode': self.slayer_mode.pk
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        action = Action.objects.get(series=self.series)
        self.assertEqual(action.team, 'A')
        self.assertEqual(action.map, self.map1)
        self.assertEqual(action.mode, self.slayer_mode)

    def test_undo_action(self):
        """Test undoing the last ban using TSDMachine directly"""
        from rest_framework import status
        from veto.machine_tsd import TSDMachine
        from veto.models import SeriesBan

        # Set up series for ban phase
        machine = TSDMachine(self.series.pk)
        machine.assign_roles("Team Alpha", "Team Beta")
        machine.confirm_tsd(series_type="Bo3")

        # Perform a ban (step 0 = OBJECTIVE_COMBO by Team A)
        machine.ban_objective_combo(
            team="A",
            objective_mode_id=self.koth_mode.pk,
            map_id=self.map1.pk,
        )

        # Sanity check: one ban exists
        assert SeriesBan.objects.filter(series=self.series).count() == 1

        # Undo it via API
        undo_url = reverse('series-series-undo', kwargs={'pk': self.series.pk})
        undo_response = self.client.post(undo_url)
        assert undo_response.status_code == status.HTTP_200_OK

        # Verify it's been removed
        assert SeriesBan.objects.filter(series=self.series).count() == 0


    def test_reset_series(self):
        from rest_framework import status
        from veto.machine_tsd import TSDMachine
        from veto.models import Action

        # Set up and perform a real veto action
        machine = TSDMachine(self.series.pk)
        machine.assign_roles("Team Alpha", "Team Beta")
        machine.confirm_tsd(series_type="Bo3")

        url = reverse('series-series-veto', kwargs={'pk': self.series.pk})
        data = {
            'team': 'Team Alpha',
            'map': self.map1.pk,
            'mode': self.koth_mode.pk,
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Action.objects.filter(series=self.series).count(), 1)

        # Call reset endpoint
        reset_url = reverse('series-series-reset', kwargs={'pk': self.series.pk})
        reset_response = self.client.post(reset_url, format='json')
        self.assertEqual(reset_response.status_code, status.HTTP_200_OK)
        self.assertEqual(Action.objects.filter(series=self.series).count(), 0)

    def test_veto_endpoint_invalid_team(self):
        from rest_framework import status

        url = reverse('series-series-veto', kwargs={'pk': self.series.pk})
        data = {
            'team': 'Invalid Team',
            'map': self.map1.pk,
            'mode': self.slayer_mode.pk
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Invalid or missing team', response.data['detail'])

    def test_series_state_endpoint(self):
        from rest_framework import status

        url = reverse('series-series-state', kwargs={'pk': self.series.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['state'], 'IDLE')

    def test_machine_state_flow(self):
        from veto.machine_tsd import TSDMachine

        machine = TSDMachine(self.series.pk)

        # Start in IDLE
        self.assertEqual(self.series.state, "IDLE")

        # Reset via machine
        machine.reset()
        self.series.refresh_from_db()
        self.assertEqual(self.series.state, "IDLE")
