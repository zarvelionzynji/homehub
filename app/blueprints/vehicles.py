from flask import render_template, request, redirect, url_for, flash, current_app, send_from_directory, send_file, abort
from datetime import datetime, date
import calendar
import os
from ..i18n import _
from ..models import db, Vehicle, ServiceType, MaintenanceRecord, ExpenseEntry
from ..security import sanitize_text
from ..blueprints import main_bp
from ..utils import handle_expense_attachment
import bleach


def add_months(d: date, months: int) -> date:
    """Add months to a date, handling month-end edge cases."""
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    last_day = calendar.monthrange(y, m)[1]
    day = min(d.day, last_day)
    return date(y, m, day)


def get_service_status(vehicle, service_type, last_record):
    """Return (status, alert_text) for a service on a vehicle.

    status: 'overdue' | 'warning' | 'ok'
    alert_text: human-readable alert message
    """
    if not last_record:
        return 'ok', ''

    status = 'ok'
    alerts = []

    # Time-based interval
    if service_type.interval_months > 0:
        next_date = add_months(last_record.date, service_type.interval_months)
        days_left = (next_date - date.today()).days
        if days_left < 0:
            status = 'overdue'
            alerts.append(f"Overdue {-days_left} days")
        elif days_left <= 14:
            if status == 'ok':
                status = 'warning'
            alerts.append(f"Due in {days_left} days")

    # Mileage-based interval
    if service_type.interval_km > 0:
        km_left = service_type.interval_km - (vehicle.current_mileage - last_record.mileage)
        if km_left < 0:
            status = 'overdue'
            alerts.append(f"Overdue {-km_left:.0f} km")
        elif km_left <= 500:
            if status == 'ok':
                status = 'warning'
            alerts.append(f"Due in {km_left:.0f} km")

    return status, " | ".join(alerts)


@main_bp.route('/vehicles', methods=['GET'])
def vehicles():
    """Main vehicles page with service status alerts."""
    vehicles_list = Vehicle.query.order_by(Vehicle.timestamp.desc()).all()
    service_types = ServiceType.query.filter_by(is_active=True).order_by(ServiceType.name).all()

    vehicle_data = []
    for v in vehicles_list:
        alerts = []
        for st in service_types:
            last_record = MaintenanceRecord.query.filter_by(
                vehicle_id=v.id, service_type_id=st.id
            ).order_by(MaintenanceRecord.date.desc()).first()
            status, alert = get_service_status(v, st, last_record)
            if status in ('overdue', 'warning'):
                alerts.append({'service_type': st.name, 'status': status, 'alert': alert})
        vehicle_data.append({'vehicle': v, 'alerts': alerts})

    config = current_app.config['HOMEHUB_CONFIG']
    return render_template('vehicles.html', vehicle_data=vehicle_data, service_types=service_types, config=config)


@main_bp.route('/vehicles/add', methods=['POST'])
def add_vehicle():
    """Create new vehicle."""
    name = bleach.clean(request.form.get('name', ''))
    vehicle_type = bleach.clean(request.form.get('vehicle_type', 'car'))
    plate = bleach.clean(request.form.get('plate', ''))
    creator = bleach.clean(request.form.get('creator', ''))

    if not name:
        flash(_('Vehicle name required.'), 'error')
        return redirect(url_for('main.vehicles'))

    v = Vehicle(name=name, vehicle_type=vehicle_type, plate=plate, creator=creator)
    db.session.add(v)
    db.session.commit()
    flash(_('Vehicle "%(name)s" added.') % {'name': name}, 'success')
    return redirect(url_for('main.vehicles'))


@main_bp.route('/vehicles/edit/<int:vid>', methods=['POST'])
def edit_vehicle(vid):
    """Edit vehicle details."""
    v = Vehicle.query.get_or_404(vid)
    v.name = bleach.clean(request.form.get('name', v.name))
    v.vehicle_type = bleach.clean(request.form.get('vehicle_type', v.vehicle_type))
    v.plate = bleach.clean(request.form.get('plate', v.plate))
    db.session.commit()
    flash(_('Vehicle updated.'), 'success')
    return redirect(url_for('main.vehicle_detail', vid=vid))


@main_bp.route('/vehicles/delete/<int:vid>', methods=['POST'])
def delete_vehicle(vid):
    """Delete vehicle (cascades maintenance records)."""
    v = Vehicle.query.get_or_404(vid)
    name = v.name
    db.session.delete(v)
    db.session.commit()
    flash(_('Vehicle "%(name)s" deleted.') % {'name': name}, 'success')
    return redirect(url_for('main.vehicles'))


@main_bp.route('/vehicles/<int:vid>', methods=['GET'])
def vehicle_detail(vid):
    """Vehicle detail page with maintenance history."""
    v = Vehicle.query.get_or_404(vid)
    records = MaintenanceRecord.query.filter_by(vehicle_id=vid).order_by(MaintenanceRecord.date.desc()).all()
    service_types = ServiceType.query.filter_by(is_active=True).all()
    config = current_app.config['HOMEHUB_CONFIG']
    return render_template('vehicles_detail.html', vehicle=v, records=records, service_types=service_types, config=config)


@main_bp.route('/vehicles/<int:vid>/service/add', methods=['POST'])
def add_maintenance_record(vid):
    """Log maintenance record and auto-create expense if cost > 0."""
    v = Vehicle.query.get_or_404(vid)

    service_type_id = request.form.get('service_type_id', type=int)
    date_s = request.form.get('date')
    mileage = request.form.get('mileage', type=float)
    cost = request.form.get('cost', type=float) or 0
    provider = bleach.clean(request.form.get('provider', ''))
    notes = bleach.clean(request.form.get('notes', ''))
    creator = bleach.clean(request.form.get('creator', ''))

    if not service_type_id or not date_s or mileage is None:
        flash(_('Service type, date, and mileage required.'), 'error')
        return redirect(url_for('main.vehicle_detail', vid=vid))

    try:
        d = datetime.strptime(date_s, '%Y-%m-%d').date()
    except ValueError:
        flash(_('Invalid date format.'), 'error')
        return redirect(url_for('main.vehicle_detail', vid=vid))

    st = ServiceType.query.get_or_404(service_type_id)

    # Handle attachment
    attachment = request.files.get('attachment')
    upload_dir = os.path.abspath(os.path.join(current_app.root_path, '..', 'uploads'))
    attachment_path = handle_expense_attachment(attachment, upload_dir) if attachment else None

    # Create maintenance record
    record = MaintenanceRecord(
        vehicle_id=vid,
        service_type_id=service_type_id,
        date=d,
        mileage=mileage,
        cost=cost,
        provider=provider,
        notes=notes,
        attachment_path=attachment_path,
        creator=creator
    )
    db.session.add(record)
    db.session.flush()

    # Auto-create expense if cost > 0
    if cost > 0:
        expense = ExpenseEntry(
            date=d,
            title=f"[{v.name}] {st.name}",
            category="Vehicle",
            amount=cost,
            unit_price=cost,
            quantity=1,
            payer=creator,
            is_paid=True,
            attachment_path=attachment_path
        )
        db.session.add(expense)
        db.session.flush()
        record.expense_id = expense.id

    # Update vehicle mileage
    v.current_mileage = mileage

    db.session.commit()
    flash(_('Maintenance record logged.'), 'success')
    return redirect(url_for('main.vehicle_detail', vid=vid))


@main_bp.route('/vehicles/service/edit/<int:rid>', methods=['POST'])
def edit_maintenance_record(rid):
    """Edit maintenance record and update linked expense."""
    r = MaintenanceRecord.query.get_or_404(rid)

    service_type_id = request.form.get('service_type_id', type=int)
    date_s = request.form.get('date')
    mileage = request.form.get('mileage', type=float)
    cost = request.form.get('cost', type=float)
    provider = bleach.clean(request.form.get('provider', ''))
    notes = bleach.clean(request.form.get('notes', ''))

    if service_type_id:
        r.service_type_id = service_type_id
    if date_s:
        try:
            r.date = datetime.strptime(date_s, '%Y-%m-%d').date()
        except ValueError:
            pass
    if mileage is not None:
        r.mileage = mileage
    if cost is not None:
        r.cost = cost
    if provider:
        r.provider = provider
    if notes:
        r.notes = notes

    # Handle attachment
    attachment = request.files.get('attachment')
    if attachment and attachment.filename:
        upload_dir = os.path.abspath(os.path.join(current_app.root_path, '..', 'uploads'))
        new_path = handle_expense_attachment(attachment, upload_dir)
        if new_path:
            r.attachment_path = new_path

    # Update linked expense
    if r.expense:
        r.expense.date = r.date
        r.expense.amount = r.cost
        r.expense.title = f"[{r.vehicle.name}] {r.service_type.name}"

    db.session.commit()
    flash(_('Maintenance record updated.'), 'success')
    return redirect(url_for('main.vehicle_detail', vid=r.vehicle_id))


@main_bp.route('/vehicles/service/delete/<int:rid>', methods=['POST'])
def delete_maintenance_record(rid):
    """Delete maintenance record (cascades to linked expense)."""
    r = MaintenanceRecord.query.get_or_404(rid)
    vid = r.vehicle_id

    if r.expense:
        db.session.delete(r.expense)
    db.session.delete(r)
    db.session.commit()
    flash(_('Maintenance record deleted.'), 'success')
    return redirect(url_for('main.vehicle_detail', vid=vid))


@main_bp.route('/vehicles/service-types/add', methods=['POST'])
def add_service_type():
    """Create service type."""
    name = bleach.clean(request.form.get('name', ''))
    interval_km = request.form.get('interval_km', type=float)
    interval_months = request.form.get('interval_months', type=int)

    if not name:
        flash(_('Service type name required.'), 'error')
        return redirect(url_for('main.vehicles'))

    st = ServiceType(
        name=name,
        interval_km=interval_km or 0,
        interval_months=interval_months or 0
    )
    db.session.add(st)
    db.session.commit()
    flash(_('Service type "%(name)s" added.') % {'name': name}, 'success')
    return redirect(url_for('main.vehicles', _anchor='tab-service-types'))


@main_bp.route('/vehicle-attachment/<path:filename>')
def vehicle_attachment(filename):
    """Serve attachment files for vehicle maintenance records from uploads/."""
    base_dir = os.path.abspath(os.path.join(current_app.root_path, '..'))
    file_path = os.path.join(base_dir, 'uploads', filename)
    if not os.path.exists(file_path):
        abort(404)
    return send_file(file_path)
