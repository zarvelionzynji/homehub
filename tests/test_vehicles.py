import pytest
from datetime import datetime, date
from app import create_app, db
from app.models import Vehicle, ServiceType, MaintenanceRecord, ExpenseEntry


@pytest.fixture
def app():
    """Create app with testing config."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def app_context(app):
    """Push app context for use in tests."""
    with app.app_context():
        yield app


def test_vehicle_creation(app_context):
    """Test creating a Vehicle."""
    vehicle = Vehicle(
        name='Tesla Model 3',
        vehicle_type='car',
        plate='ABC123',
        current_mileage=50000,
        creator='Alice'
    )
    db.session.add(vehicle)
    db.session.commit()

    retrieved = Vehicle.query.first()
    assert retrieved.name == 'Tesla Model 3'
    assert retrieved.vehicle_type == 'car'
    assert retrieved.plate == 'ABC123'
    assert retrieved.current_mileage == 50000
    assert retrieved.creator == 'Alice'
    assert retrieved.timestamp is not None


def test_service_type_creation(app_context):
    """Test creating a ServiceType."""
    service = ServiceType(
        name='Oil Change',
        interval_km=5000,
        interval_months=3,
        is_active=True
    )
    db.session.add(service)
    db.session.commit()

    retrieved = ServiceType.query.first()
    assert retrieved.name == 'Oil Change'
    assert retrieved.interval_km == 5000
    assert retrieved.interval_months == 3
    assert retrieved.is_active is True
    assert retrieved.timestamp is not None


def test_maintenance_record_creation(app_context):
    """Test creating a MaintenanceRecord with relationships."""
    vehicle = Vehicle(
        name='Honda Civic',
        vehicle_type='car',
        plate='XYZ789',
        current_mileage=75000,
        creator='Bob'
    )
    db.session.add(vehicle)
    db.session.flush()

    service = ServiceType(
        name='Tire Rotation',
        interval_km=10000,
        interval_months=6,
        is_active=True
    )
    db.session.add(service)
    db.session.flush()

    record = MaintenanceRecord(
        vehicle_id=vehicle.id,
        service_type_id=service.id,
        date=date(2026, 7, 1),
        mileage=75050,
        cost=45.50,
        provider='Local Garage',
        notes='All tires rotated successfully',
        creator='Bob'
    )
    db.session.add(record)
    db.session.commit()

    retrieved = MaintenanceRecord.query.first()
    assert retrieved.date == date(2026, 7, 1)
    assert retrieved.mileage == 75050
    assert retrieved.cost == 45.50
    assert retrieved.provider == 'Local Garage'
    assert retrieved.notes == 'All tires rotated successfully'


def test_maintenance_record_vehicle_relationship(app_context):
    """Test MaintenanceRecord vehicle relationship."""
    vehicle = Vehicle(
        name='Yamaha Bike',
        vehicle_type='motorcycle',
        plate='MOTO1',
        creator='Charlie'
    )
    db.session.add(vehicle)
    db.session.flush()

    service = ServiceType(name='Chain Maintenance', is_active=True)
    db.session.add(service)
    db.session.flush()

    record = MaintenanceRecord(
        vehicle_id=vehicle.id,
        service_type_id=service.id,
        date=date(2026, 6, 15),
        mileage=12000,
        creator='Charlie'
    )
    db.session.add(record)
    db.session.commit()

    # Test relationship from maintenance record to vehicle
    retrieved_record = MaintenanceRecord.query.first()
    assert retrieved_record.vehicle.name == 'Yamaha Bike'
    assert retrieved_record.vehicle.vehicle_type == 'motorcycle'

    # Test backref from vehicle to maintenance records
    retrieved_vehicle = Vehicle.query.first()
    assert len(retrieved_vehicle.maintenance_records) == 1
    assert retrieved_vehicle.maintenance_records[0].date == date(2026, 6, 15)


def test_maintenance_record_service_type_relationship(app_context):
    """Test MaintenanceRecord service_type relationship."""
    vehicle = Vehicle(name='Test Car', vehicle_type='car', creator='Test')
    db.session.add(vehicle)
    db.session.flush()

    service = ServiceType(name='Battery Replacement', interval_months=48)
    db.session.add(service)
    db.session.flush()

    record = MaintenanceRecord(
        vehicle_id=vehicle.id,
        service_type_id=service.id,
        date=date(2026, 7, 2),
        mileage=100000,
        creator='Test'
    )
    db.session.add(record)
    db.session.commit()

    retrieved_record = MaintenanceRecord.query.first()
    assert retrieved_record.service_type.name == 'Battery Replacement'
    assert retrieved_record.service_type.interval_months == 48


def test_maintenance_record_expense_relationship(app_context):
    """Test MaintenanceRecord expense relationship."""
    vehicle = Vehicle(name='Test Car', vehicle_type='car', creator='Test')
    db.session.add(vehicle)
    db.session.flush()

    service = ServiceType(name='Brake Pads', is_active=True)
    db.session.add(service)
    db.session.flush()

    expense = ExpenseEntry(
        date=date(2026, 7, 2),
        title='Brake Pads Service',
        amount=120.00
    )
    db.session.add(expense)
    db.session.flush()

    record = MaintenanceRecord(
        vehicle_id=vehicle.id,
        service_type_id=service.id,
        date=date(2026, 7, 2),
        mileage=85000,
        cost=120.00,
        expense_id=expense.id,
        creator='Test'
    )
    db.session.add(record)
    db.session.commit()

    retrieved_record = MaintenanceRecord.query.first()
    assert retrieved_record.expense is not None
    assert retrieved_record.expense.title == 'Brake Pads Service'
    assert retrieved_record.expense.amount == 120.00


def test_multiple_records_per_vehicle(app_context):
    """Test a vehicle with multiple maintenance records."""
    vehicle = Vehicle(
        name='Ford F-150',
        vehicle_type='car',
        current_mileage=120000,
        creator='Dave'
    )
    db.session.add(vehicle)
    db.session.flush()

    oil_change = ServiceType(name='Oil Change', interval_km=5000)
    tire_rotation = ServiceType(name='Tire Rotation', interval_km=10000)
    db.session.add_all([oil_change, tire_rotation])
    db.session.flush()

    records = [
        MaintenanceRecord(
            vehicle_id=vehicle.id,
            service_type_id=oil_change.id,
            date=date(2026, 6, 1),
            mileage=115000,
            cost=35.00,
            creator='Dave'
        ),
        MaintenanceRecord(
            vehicle_id=vehicle.id,
            service_type_id=tire_rotation.id,
            date=date(2026, 6, 15),
            mileage=117500,
            cost=50.00,
            creator='Dave'
        ),
    ]
    db.session.add_all(records)
    db.session.commit()

    retrieved_vehicle = Vehicle.query.first()
    assert len(retrieved_vehicle.maintenance_records) == 2
    costs = sorted([r.cost for r in retrieved_vehicle.maintenance_records])
    assert costs == [35.00, 50.00]


def test_maintenance_record_defaults(app_context):
    """Test MaintenanceRecord field defaults."""
    vehicle = Vehicle(name='Test', vehicle_type='car', creator='Test')
    db.session.add(vehicle)
    db.session.flush()

    service = ServiceType(name='Test Service')
    db.session.add(service)
    db.session.flush()

    record = MaintenanceRecord(
        vehicle_id=vehicle.id,
        service_type_id=service.id,
        date=date(2026, 7, 2),
        mileage=50000
    )
    db.session.add(record)
    db.session.commit()

    retrieved = MaintenanceRecord.query.first()
    assert retrieved.cost == 0
    assert retrieved.provider is None
    assert retrieved.notes is None
    assert retrieved.attachment_path is None
    assert retrieved.expense_id is None
    assert retrieved.creator is None
    assert retrieved.timestamp is not None
