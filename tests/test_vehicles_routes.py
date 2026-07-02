from datetime import date, timedelta
import pytest

from app import create_app, db
from app.models import Vehicle, ServiceType, MaintenanceRecord, ExpenseEntry


def make_app():
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


def _add_vehicle_for_test(app, name='Tesla Model 3', vehicle_type='car', plate='ABC123', creator='Alice'):
    with app.app_context():
        v = Vehicle(name=name, vehicle_type=vehicle_type, plate=plate, creator=creator)
        db.session.add(v)
        db.session.commit()
        return v.id


def _add_service_types_for_test(app):
    with app.app_context():
        st1 = ServiceType(name='Oil Change', interval_km=5000, interval_months=6)
        st2 = ServiceType(name='Tire Rotation', interval_km=10000, interval_months=12)
        db.session.add_all([st1, st2])
        db.session.commit()
        return [st1.id, st2.id]


class TestVehicleCrud:
    """Test basic vehicle CRUD operations."""

    def test_vehicles_page_empty(self, client):
        """GET /vehicles returns 200."""
        rv = client.get('/vehicles')
        assert rv.status_code == 200

    def test_add_vehicle(self, client):
        """POST /vehicles/add creates a vehicle."""
        rv = client.post('/vehicles/add', data={
            'name': 'Honda Civic',
            'vehicle_type': 'car',
            'plate': 'XYZ789',
            'creator': 'Alice'
        }, follow_redirects=False)
        assert rv.status_code == 302

        with client.application.app_context():
            v = Vehicle.query.filter_by(name='Honda Civic').first()
            assert v is not None
            assert v.plate == 'XYZ789'
            assert v.creator == 'Alice'

    def test_add_vehicle_missing_name(self, client):
        """POST /vehicles/add with missing name returns error."""
        rv = client.post('/vehicles/add', data={
            'name': '',
            'vehicle_type': 'car',
            'plate': 'XYZ789',
            'creator': 'Alice'
        }, follow_redirects=True)
        assert b'Vehicle name required' in rv.data

    def test_edit_vehicle(self, client):
        """POST /vehicles/edit/<vid> updates vehicle."""
        vid = _add_vehicle_for_test(client.application)
        rv = client.post(f'/vehicles/edit/{vid}', data={
            'name': 'Tesla Model 3 Updated',
            'vehicle_type': 'car',
            'plate': 'NEW123',
        }, follow_redirects=False)
        assert rv.status_code == 302

        with client.application.app_context():
            v = Vehicle.query.get(vid)
            assert v.name == 'Tesla Model 3 Updated'
            assert v.plate == 'NEW123'

    def test_delete_vehicle(self, client):
        """POST /vehicles/delete/<vid> deletes vehicle."""
        vid = _add_vehicle_for_test(client.application)
        rv = client.post(f'/vehicles/delete/{vid}', follow_redirects=False)
        assert rv.status_code == 302

        with client.application.app_context():
            v = Vehicle.query.get(vid)
            assert v is None

    def test_vehicle_detail_page(self, client):
        """GET /vehicles/<vid> shows vehicle details."""
        vid = _add_vehicle_for_test(client.application)
        _add_service_types_for_test(client.application)
        rv = client.get(f'/vehicles/{vid}')
        assert rv.status_code == 200

    def test_vehicle_detail_page_not_found(self, client):
        """GET /vehicles/<vid> returns 404 for missing vehicle."""
        rv = client.get('/vehicles/9999')
        assert rv.status_code == 404


class TestMaintenanceRecords:
    """Test maintenance record CRUD and linked expenses."""

    def test_add_maintenance_record(self, client):
        """POST /vehicles/<vid>/service/add creates maintenance record."""
        app = client.application
        vid = _add_vehicle_for_test(app)
        st_ids = _add_service_types_for_test(app)
        st_id = st_ids[0]
        today = date.today().isoformat()

        rv = client.post(f'/vehicles/{vid}/service/add', data={
            'service_type_id': st_id,
            'date': today,
            'mileage': 50000,
            'cost': 100,
            'provider': "Joe's Auto Shop",
            'notes': 'Regular maintenance',
            'creator': 'Alice'
        }, follow_redirects=False)
        assert rv.status_code == 302

        with app.app_context():
            record = MaintenanceRecord.query.filter_by(vehicle_id=vid).first()
            assert record is not None
            assert record.mileage == 50000
            assert record.cost == 100
            assert record.provider == "Joe's Auto Shop"

    def test_add_maintenance_record_creates_expense(self, client):
        """Adding maintenance record with cost > 0 auto-creates expense."""
        app = client.application
        vid = _add_vehicle_for_test(app)
        st_ids = _add_service_types_for_test(app)
        st_id = st_ids[0]
        today = date.today().isoformat()

        with app.app_context():
            st = ServiceType.query.get(st_id)
            v = Vehicle.query.get(vid)

        rv = client.post(f'/vehicles/{vid}/service/add', data={
            'service_type_id': st_id,
            'date': today,
            'mileage': 50000,
            'cost': 150,
            'provider': 'Auto Shop',
            'notes': 'Oil change',
            'creator': 'Alice'
        }, follow_redirects=False)
        assert rv.status_code == 302

        with app.app_context():
            record = MaintenanceRecord.query.filter_by(vehicle_id=vid).first()
            assert record is not None
            assert record.expense_id is not None

            expense = ExpenseEntry.query.get(record.expense_id)
            assert expense is not None
            assert expense.amount == 150
            assert 'Tesla Model 3' in expense.title
            assert 'Oil Change' in expense.title
            assert expense.category == 'Vehicle'

    def test_add_maintenance_record_no_expense_if_cost_zero(self, client):
        """Adding maintenance record with cost 0 does not create expense."""
        app = client.application
        vid = _add_vehicle_for_test(app)
        st_ids = _add_service_types_for_test(app)
        st_id = st_ids[0]
        today = date.today().isoformat()

        rv = client.post(f'/vehicles/{vid}/service/add', data={
            'service_type_id': st_id,
            'date': today,
            'mileage': 50000,
            'cost': 0,
            'provider': 'DIY',
            'notes': 'Self-service',
            'creator': 'Alice'
        }, follow_redirects=False)
        assert rv.status_code == 302

        with app.app_context():
            record = MaintenanceRecord.query.filter_by(vehicle_id=vid).first()
            assert record is not None
            assert record.expense_id is None

    def test_add_maintenance_record_missing_required_fields(self, client):
        """POST with missing required fields returns error."""
        app = client.application
        vid = _add_vehicle_for_test(app)

        rv = client.post(f'/vehicles/{vid}/service/add', data={
            'service_type_id': '',
            'date': '',
            'mileage': '',
            'cost': 0,
            'creator': 'Alice'
        }, follow_redirects=True)
        assert b'required' in rv.data.lower()

    def test_edit_maintenance_record(self, client):
        """POST /vehicles/service/edit/<rid> updates record."""
        app = client.application
        vid = _add_vehicle_for_test(app)
        st_ids = _add_service_types_for_test(app)
        st_id = st_ids[0]
        today = date.today().isoformat()

        with app.app_context():
            record = MaintenanceRecord(
                vehicle_id=vid,
                service_type_id=st_id,
                date=date.today(),
                mileage=50000,
                cost=100,
                provider='Shop A',
                notes='First service',
                creator='Alice'
            )
            db.session.add(record)
            db.session.commit()
            rid = record.id

        rv = client.post(f'/vehicles/service/edit/{rid}', data={
            'service_type_id': st_id,
            'date': today,
            'mileage': 51000,
            'cost': 120,
            'provider': 'Shop B',
            'notes': 'Updated service'
        }, follow_redirects=False)
        assert rv.status_code == 302

        with app.app_context():
            record = MaintenanceRecord.query.get(rid)
            assert record.mileage == 51000
            assert record.cost == 120
            assert record.provider == 'Shop B'

    def test_edit_maintenance_record_updates_linked_expense(self, client):
        """Editing maintenance record updates linked expense."""
        app = client.application
        vid = _add_vehicle_for_test(app)
        st_ids = _add_service_types_for_test(app)
        st_id = st_ids[0]
        today = date.today().isoformat()

        with app.app_context():
            st = ServiceType.query.get(st_id)
            v = Vehicle.query.get(vid)

            record = MaintenanceRecord(
                vehicle_id=vid,
                service_type_id=st_id,
                date=date.today(),
                mileage=50000,
                cost=100,
                provider='Shop A',
                creator='Alice'
            )
            db.session.add(record)
            db.session.flush()

            expense = ExpenseEntry(
                date=date.today(),
                title=f"[{v.name}] {st.name}",
                category="Vehicle",
                amount=100,
                payer='Alice',
                is_paid=True
            )
            db.session.add(expense)
            db.session.flush()
            record.expense_id = expense.id
            db.session.commit()
            rid = record.id

        rv = client.post(f'/vehicles/service/edit/{rid}', data={
            'service_type_id': st_id,
            'date': today,
            'mileage': 51000,
            'cost': 150,
            'provider': 'Shop B',
        }, follow_redirects=False)
        assert rv.status_code == 302

        with app.app_context():
            record = MaintenanceRecord.query.get(rid)
            expense = record.expense
            assert expense.amount == 150
            assert expense.date == date.today()

    def test_delete_maintenance_record(self, client):
        """POST /vehicles/service/delete/<rid> deletes record."""
        app = client.application
        vid = _add_vehicle_for_test(app)
        st_ids = _add_service_types_for_test(app)
        st_id = st_ids[0]

        with app.app_context():
            record = MaintenanceRecord(
                vehicle_id=vid,
                service_type_id=st_id,
                date=date.today(),
                mileage=50000,
                cost=100,
                creator='Alice'
            )
            db.session.add(record)
            db.session.commit()
            rid = record.id

        rv = client.post(f'/vehicles/service/delete/{rid}', follow_redirects=False)
        assert rv.status_code == 302

        with app.app_context():
            record = MaintenanceRecord.query.get(rid)
            assert record is None

    def test_delete_maintenance_record_cascades_expense(self, client):
        """Deleting maintenance record cascades to linked expense."""
        app = client.application
        vid = _add_vehicle_for_test(app)
        st_ids = _add_service_types_for_test(app)
        st_id = st_ids[0]

        with app.app_context():
            v = Vehicle.query.get(vid)
            st = ServiceType.query.get(st_id)

            record = MaintenanceRecord(
                vehicle_id=vid,
                service_type_id=st_id,
                date=date.today(),
                mileage=50000,
                cost=100,
                creator='Alice'
            )
            db.session.add(record)
            db.session.flush()

            expense = ExpenseEntry(
                date=date.today(),
                title=f"[{v.name}] {st.name}",
                category="Vehicle",
                amount=100,
                payer='Alice',
                is_paid=True
            )
            db.session.add(expense)
            db.session.flush()
            record.expense_id = expense.id
            db.session.commit()
            rid = record.id
            eid = expense.id

        rv = client.post(f'/vehicles/service/delete/{rid}', follow_redirects=False)
        assert rv.status_code == 302

        with app.app_context():
            record = MaintenanceRecord.query.get(rid)
            expense = ExpenseEntry.query.get(eid)
            assert record is None
            assert expense is None


class TestServiceStatus:
    """Test service status alert computation."""

    def test_status_ok_no_records(self, client):
        """Service with no records returns 'ok' status."""
        app = client.application
        with app.app_context():
            from app.blueprints.vehicles import get_service_status

            v = Vehicle(name='Test', vehicle_type='car', creator='Test')
            db.session.add(v)
            db.session.flush()
            st = ServiceType(name='Oil Change', interval_km=5000, interval_months=6)
            db.session.add(st)
            db.session.commit()

            status, alert = get_service_status(v, st, None)
            assert status == 'ok'
            assert alert == ''

    def test_status_warning_days(self, client):
        """Service due within 14 days returns 'warning'."""
        app = client.application
        with app.app_context():
            from app.blueprints.vehicles import get_service_status

            v = Vehicle(name='Test', vehicle_type='car', creator='Test')
            db.session.add(v)
            db.session.flush()
            st = ServiceType(name='Oil Change', interval_km=0, interval_months=1)
            db.session.add(st)
            db.session.flush()

            # Record 20 days ago with 1-month interval = due in about 10 days (warning zone)
            record = MaintenanceRecord(
                vehicle_id=v.id,
                service_type_id=st.id,
                date=date.today() - timedelta(days=20),
                mileage=40000,
                creator='Test'
            )
            db.session.add(record)
            db.session.commit()

            status, alert = get_service_status(v, st, record)
            assert status == 'warning'
            assert 'Due in' in alert

    def test_status_overdue_days(self, client):
        """Service past due date returns 'overdue'."""
        app = client.application
        with app.app_context():
            from app.blueprints.vehicles import get_service_status

            v = Vehicle(name='Test', vehicle_type='car', creator='Test')
            db.session.add(v)
            db.session.flush()
            st = ServiceType(name='Oil Change', interval_km=0, interval_months=6)
            db.session.add(st)
            db.session.flush()

            record = MaintenanceRecord(
                vehicle_id=v.id,
                service_type_id=st.id,
                date=date.today() - timedelta(days=215),
                mileage=40000,
                creator='Test'
            )
            db.session.add(record)
            db.session.commit()

            status, alert = get_service_status(v, st, record)
            assert status == 'overdue'
            assert 'Overdue' in alert

    def test_status_warning_km(self, client):
        """Service due within 500 km returns 'warning'."""
        app = client.application
        with app.app_context():
            from app.blueprints.vehicles import get_service_status

            v = Vehicle(name='Test', vehicle_type='car', creator='Test')
            v.current_mileage = 49600
            db.session.add(v)
            db.session.flush()
            st = ServiceType(name='Oil Change', interval_km=5000, interval_months=0)
            db.session.add(st)
            db.session.flush()

            record = MaintenanceRecord(
                vehicle_id=v.id,
                service_type_id=st.id,
                date=date.today(),
                mileage=45000,
                creator='Test'
            )
            db.session.add(record)
            db.session.commit()

            status, alert = get_service_status(v, st, record)
            assert status == 'warning'
            assert 'Due in' in alert and 'km' in alert

    def test_status_overdue_km(self, client):
        """Service past due mileage returns 'overdue'."""
        app = client.application
        with app.app_context():
            from app.blueprints.vehicles import get_service_status

            v = Vehicle(name='Test', vehicle_type='car', creator='Test')
            v.current_mileage = 50200
            db.session.add(v)
            db.session.flush()
            st = ServiceType(name='Oil Change', interval_km=5000, interval_months=0)
            db.session.add(st)
            db.session.flush()

            record = MaintenanceRecord(
                vehicle_id=v.id,
                service_type_id=st.id,
                date=date.today(),
                mileage=45000,
                creator='Test'
            )
            db.session.add(record)
            db.session.commit()

            status, alert = get_service_status(v, st, record)
            assert status == 'overdue'
            assert 'Overdue' in alert and 'km' in alert

    def test_status_combined_overdue(self, client):
        """Both time and km overdue shows both alerts."""
        app = client.application
        with app.app_context():
            from app.blueprints.vehicles import get_service_status

            v = Vehicle(name='Test', vehicle_type='car', creator='Test')
            v.current_mileage = 51000
            db.session.add(v)
            db.session.flush()
            st = ServiceType(name='Oil Change', interval_km=5000, interval_months=6)
            db.session.add(st)
            db.session.flush()

            record = MaintenanceRecord(
                vehicle_id=v.id,
                service_type_id=st.id,
                date=date.today() - timedelta(days=215),
                mileage=40000,
                creator='Test'
            )
            db.session.add(record)
            db.session.commit()

            status, alert = get_service_status(v, st, record)
            assert status == 'overdue'
            assert 'Overdue' in alert
            assert '|' in alert


class TestCascadingDeletes:
    """Test cascading delete behavior."""

    def test_delete_vehicle_cascades_maintenance_records(self, client):
        """Deleting vehicle cascades to maintenance records."""
        app = client.application
        vid = _add_vehicle_for_test(app)
        st_ids = _add_service_types_for_test(app)
        st_id = st_ids[0]

        with app.app_context():
            for i in range(3):
                record = MaintenanceRecord(
                    vehicle_id=vid,
                    service_type_id=st_id,
                    date=date.today() - timedelta(days=i * 30),
                    mileage=40000 + i * 1000,
                    cost=100,
                    creator='Alice'
                )
                db.session.add(record)
            db.session.commit()

            records_before = MaintenanceRecord.query.filter_by(vehicle_id=vid).count()
            assert records_before == 3

        rv = client.post(f'/vehicles/delete/{vid}', follow_redirects=False)
        assert rv.status_code == 302

        with app.app_context():
            records_after = MaintenanceRecord.query.filter_by(vehicle_id=vid).count()
            assert records_after == 0


class TestServiceTypes:
    """Test service type management."""

    def test_add_service_type(self, client):
        """POST /vehicles/service-types/add creates service type."""
        rv = client.post('/vehicles/service-types/add', data={
            'name': 'Brake Inspection',
            'interval_km': 15000,
            'interval_months': 12
        }, follow_redirects=False)
        assert rv.status_code == 302

        with client.application.app_context():
            st = ServiceType.query.filter_by(name='Brake Inspection').first()
            assert st is not None
            assert st.interval_km == 15000
            assert st.interval_months == 12

    def test_add_service_type_missing_name(self, client):
        """POST /vehicles/service-types/add with missing name returns error."""
        rv = client.post('/vehicles/service-types/add', data={
            'name': '',
            'interval_km': 15000,
            'interval_months': 12
        }, follow_redirects=True)
        assert b'required' in rv.data.lower()
