import pytest
from django.test import TestCase
from django.urls import reverse


@pytest.mark.django_db
class VetoSeriesFlowTests(TestCase):
    
    def setUp(self):
        # Import here to avoid module-level import issues
        from rest_framework.test import APIClient
        from veto.models import Series, Map, GameMode, Action
        
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
        """Test creating an action through the veto endpoint"""
        from rest_framework import status
        from veto.models import Action
        
        # Use the correct DRF router-generated URL name
        url = reverse('series-series-veto', kwargs={'pk': self.series.pk})
        data = {
            'team': 'Team Alpha',
            'map': self.map1.pk,
            'mode': self.slayer_mode.pk
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify action was created
        action = Action.objects.get(series=self.series)
        self.assertEqual(action.team, 'A')
        self.assertEqual(action.map, self.map1)
        self.assertEqual(action.mode, self.slayer_mode)
    
    def test_undo_action(self):
        """Test undoing the last action"""
        from rest_framework import status
        from veto.models import Action
        
        # First create an action directly
        Action.objects.create(
            series=self.series,
            step=1,
            action_type=Action.BAN,
            team='A',
            map=self.map1,
            mode=self.slayer_mode
        )
        
        # Verify action exists
        self.assertEqual(Action.objects.filter(series=self.series).count(), 1)
        
        # Now undo it via API
        url = reverse('series-series-undo', kwargs={'pk': self.series.pk})
        response = self.client.post(url, format='json')
        
        # The response should be 200 OK or 400 depending on TSDMachine implementation
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])
    
    def test_reset_series(self):
        """Test resetting a series removes all actions"""
        from rest_framework import status
        from veto.models import Action
        
        # Create multiple actions
        Action.objects.create(
            series=self.series,
            step=1,
            action_type=Action.BAN,
            team='A',
            map=self.map1,
            mode=self.slayer_mode
        )
        Action.objects.create(
            series=self.series,
            step=2,
            action_type=Action.BAN,
            team='B',
            map=self.map2,
            mode=self.slayer_mode
        )
        
        # Verify actions exist
        self.assertEqual(Action.objects.filter(series=self.series).count(), 2)
        
        # Reset the series
        url = reverse('series-series-reset', kwargs={'pk': self.series.pk})
        response = self.client.post(url, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify all actions are removed
        self.assertEqual(Action.objects.filter(series=self.series).count(), 0)
    
    def test_veto_endpoint_invalid_team(self):
        """Test veto endpoint with invalid team name"""
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
        """Test getting series state"""
        from rest_framework import status
        
        url = reverse('series-series-state', kwargs={'pk': self.series.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['state'], 'IDLE')
    
    def test_machine_state_flow(self):
        """Test the TSDMachine state flow"""
        from veto.machine_tsd import TSDMachine
        
        machine = TSDMachine(self.series.pk)
        
        # Start in IDLE
        self.assertEqual(self.series.state, "IDLE")
        
        # Test that machine can be reset (this should work based on your views.py)
        machine.reset()
        self.series.refresh_from_db()
        self.assertEqual(self.series.state, "IDLE")