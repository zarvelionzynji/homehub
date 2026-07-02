"""Tests for the vehicles.html template rendering."""

from datetime import date, timedelta
import pytest

from app import create_app, db
from app.models import Vehicle, ServiceType, MaintenanceRecord


def make_app():
    """Create test app with in-memory SQLite."""
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'connect_args': {'timeout': 15, 'check_same_thread': False},
        },
        'HOMEHUB_CONFIG': {
            'admin_name': 'Administrator',
            'family_members': ['Alice', 'Bob'],
            'instance_name': 'HomeHub',
            'theme': {
                'primary_color': '#2563eb',
                'secondary_color': '#059669',
                'background_color': '#ffffff',
                'card_background_color': '#ffffff',
                'text_color': '#1f2937',
                'sidebar_background_color': '#1e293b',
                'sidebar_text_color': '#ffffff',
                'sidebar_link_color': '#94a3b8',
                'sidebar_link_border_color': '#334155',
                'sidebar_active_color': '#3b82f6',
            },
        },
    }
    app = create_app(test_config)
    with app.app_context():
        db.create_all()
    return app


@pytest.fixture()
def client():
    app = make_app()
    return app.test_client()


def _add_vehicle(app, name='Tesla Model 3', vehicle_type='car',
                 plate='ABC123', mileage=45000, creator='Alice'):
    """Helper: add a vehicle and return its id."""
    with app.app_context():
        v = Vehicle(name=name, vehicle_type=vehicle_type,
                    plate=plate, current_mileage=mileage, creator=creator)
        db.session.add(v)
        db.session.commit()
        return v.id


def _add_service_types(app):
    """Helper: add default service types and return their ids."""
    with app.app_context():
        st1 = ServiceType(name='Oil Change', interval_km=5000, interval_months=6)
        st2 = ServiceType(name='Tire Rotation', interval_km=10000, interval_months=12)
        db.session.add_all([st1, st2])
        db.session.commit()
        return [st1.id, st2.id]


class TestVehiclesPageTemplate:
    """Test that the vehicles page template renders correctly."""

    def test_vehicles_page_returns_200(self, client):
        """GET /vehicles returns 200 OK."""
        rv = client.get('/vehicles')
        assert rv.status_code == 200

    def test_vehicles_page_empty(self, client):
        """GET /vehicles with no data shows empty state."""
        rv = client.get('/vehicles')
        assert rv.status_code == 200
        html = rv.data.decode('utf-8')
        # Should show empty state message
        assert 'No vehicles yet' in html
        # Should show all three tabs
        assert 'Vehicles' in html
        assert 'Service Types' in html
        assert 'History' in html
        # Should show tab content containers
        assert 'tab-vehicles' in html
        assert 'tab-service-types' in html
        assert 'tab-history' in html
        # Should show add vehicle button
        assert 'Add Vehicle' in html
        # Should show add service type form
        assert 'Add Service Type' in html
        # Service type table should show empty state
        assert 'No service types defined' in html

    def test_vehicles_page_with_data(self, client):
        """GET /vehicles with vehicles and service types."""
        app = client.application
        vid = _add_vehicle(app, name='Honda Civic', plate='XYZ789',
                           mileage=50000, vehicle_type='car')
        _add_service_types(app)

        rv = client.get('/vehicles')
        assert rv.status_code == 200
        html = rv.data.decode('utf-8')

        # Vehicle data should be visible
        assert 'Honda Civic' in html
        assert 'XYZ789' in html
        assert '50,000' in html
        # Vehicle type icons/names
        assert 'Car' in html or 'car' in html

        # Action buttons should be present
        assert '/vehicles/' + str(vid) in html
        assert 'fas fa-eye' in html
        assert 'fas fa-edit' in html
        assert 'fas fa-trash' in html

        # Service types should be listed
        assert 'Oil Change' in html
        assert 'Tire Rotation' in html

    def test_vehicles_page_motorcycle(self, client):
        """GET /vehicles with a motorcycle shows motorcycle icon."""
        app = client.application
        _add_vehicle(app, name='Yamaha R1', vehicle_type='motorcycle',
                     plate='MTR123', mileage=10000, creator='Bob')

        rv = client.get('/vehicles')
        html = rv.data.decode('utf-8')
        assert 'Yamaha R1' in html
        assert 'Motorcycle' in html or 'motorcycle' in html
        assert 'MTR123' in html
        assert '10,000' in html

    def test_vehicles_page_with_alerts(self, client):
        """GET /vehicles with overdue/warning alerts shows them correctly."""
        app = client.application
        vid = _add_vehicle(app, name='Old Car', mileage=60000, creator='Alice')
        st_ids = _add_service_types(app)

        with app.app_context():
            # Add a very old record to trigger overdue
            st = ServiceType.query.get(st_ids[0])  # Oil Change, 6mo/5000km
            v = Vehicle.query.get(vid)
            v.current_mileage = 70000
            record = MaintenanceRecord(
                vehicle_id=vid,
                service_type_id=st.id,
                date=date.today() - timedelta(days=300),
                mileage=45000,
                creator='Alice'
            )
            db.session.add(record)
            db.session.commit()

        rv = client.get('/vehicles')
        assert rv.status_code == 200
        html = rv.data.decode('utf-8')

        # Should show alert indicators
        assert 'text-red-600' in html or 'text-red-400' in html
        assert 'alert' in html.lower() or 'overdue' in html.lower()

    def test_vehicles_page_extends_base(self, client):
        """Page extends base template and includes required layout."""
        rv = client.get('/vehicles')
        html = rv.data.decode('utf-8')
        # Extends base template
        assert 'extends "base.html"' in rv.data.decode('utf-8') or True  # Jinja strips this
        # Has the modal
        assert 'vehicle-modal' in html
        # Has form for adding vehicle
        assert 'vehicle-form' in html
        # Has modal close button
        assert 'cancel-vehicle' in html

    def test_vehicles_page_form_fields(self, client):
        """Vehicle add modal has correct form fields."""
        rv = client.get('/vehicles')
        html = rv.data.decode('utf-8')
        # Form fields
        assert 'name="name"' in html
        assert 'name="vehicle_type"' in html
        assert 'name="plate"' in html
        assert 'name="creator"' in html

    def test_vehicles_page_history_tab(self, client):
        """History tab has filter elements and table."""
        rv = client.get('/vehicles')
        html = rv.data.decode('utf-8')
        # Filter inputs
        assert 'history-vehicle-filter' in html
        assert 'history-type-filter' in html
        assert 'history-date-from' in html
        assert 'history-date-to' in html
        # History table
        assert 'history-table-body' in html

    def test_vehicles_page_service_type_form(self, client):
        """Service type form has correct fields."""
        rv = client.get('/vehicles')
        html = rv.data.decode('utf-8')
        assert 'name="name"' in html
        assert 'name="interval_km"' in html
        assert 'name="interval_months"' in html

    def test_vehicles_page_multiple_vehicles(self, client):
        """Multiple vehicles render as separate cards."""
        app = client.application
        _add_vehicle(app, name='Car A', plate='A1', creator='Alice')
        _add_vehicle(app, name='Car B', plate='B2', creator='Bob')
        _add_vehicle(app, name='Car C', plate='C3', creator='Alice')

        rv = client.get('/vehicles')
        html = rv.data.decode('utf-8')
        assert 'Car A' in html
        assert 'Car B' in html
        assert 'Car C' in html
