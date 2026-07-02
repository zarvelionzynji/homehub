# Vehicle Maintenance Log — Design Specification

**Date:** 2026-07-02  
**Feature:** Vehicle/Equipment Maintenance Tracking  
**Scope:** Cars + motorcycles, service records, cost tracking, mileage-based reminders

---

## 1. Overview

HomeHub **Vehicle Maintenance Log** lets families track maintenance on multiple vehicles (cars, motorcycles). Each vehicle stores:
- Service history (oil changes, repairs, inspections, taxes)
- Mileage at each service
- Costs & provider info
- Automatic cost integration with existing Expense tracker
- Smart service alerts (overdue/warning based on time or mileage)

---

## 2. Data Model

### Vehicle
```python
class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)          # "Mobil Keluarga", "Motor Ayah"
    vehicle_type = db.Column(db.String(16), nullable=False)   # 'car' | 'motorcycle'
    plate = db.Column(db.String(32))                          # Plat nomor
    current_mileage = db.Column(db.Float, default=0)          # km terakhir direcord
    creator = db.Column(db.String(64))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
```

**Rationale:**
- `name` + `plate` identify vehicle for UI display
- `current_mileage` updated on each maintenance record → enable mileage-based alerts
- `vehicle_type` for UI/filtering (car icon vs motorcycle icon)

---

### ServiceType
```python
class ServiceType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)          # "Oil Change", "Pajak Tahunan", "STNK"
    interval_km = db.Column(db.Float, default=0)              # 0 = not applicable
    interval_months = db.Column(db.Integer, default=0)        # 0 = not applicable
    is_active = db.Column(db.Boolean, default=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
```

**Examples:**
- Oil Change: `interval_km=5000, interval_months=3` (every 5k km OR 3 months, whichever first)
- Pajak Tahunan: `interval_km=0, interval_months=12` (time-only)
- Tire Rotation: `interval_km=10000, interval_months=6` (mileage-primary)

**Rationale:**
- Dual-interval supports real-world service schedules
- `is_active` allows archiving old service types without deleting history

---

### MaintenanceRecord
```python
class MaintenanceRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    service_type_id = db.Column(db.Integer, db.ForeignKey('service_type.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)                 # Service date
    mileage = db.Column(db.Float, nullable=False)             # Odometer at service
    cost = db.Column(db.Float, default=0)
    provider = db.Column(db.String(256))                      # Bengkel/service center name
    notes = db.Column(db.Text)
    attachment_path = db.Column(db.String(512))               # Receipt/invoice file
    expense_id = db.Column(db.Integer, db.ForeignKey('expense_entry.id'))  # linked expense
    creator = db.Column(db.String(64))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    vehicle = db.relationship('Vehicle', backref='maintenance_records')
    service_type = db.relationship('ServiceType')
    expense = db.relationship('ExpenseEntry')
```

**Rationale:**
- `mileage` required for km-based interval calculation
- `expense_id` link enables cost queries without JOIN (performance)
- Relationships enable eager-loading vehicle + service type for list views

---

## 3. Core Features

### 3.1 Vehicle Management
**Routes:**
- `GET /vehicles` → List vehicles + service status
- `POST /vehicles/add` → Create vehicle
- `POST /vehicles/edit/<id>` → Update vehicle (name, type, mileage)
- `POST /vehicles/delete/<id>` → Delete vehicle + all records
- `GET /vehicles/<id>` → Vehicle detail + full service history

**Behavior:**
- Vehicle deletion cascades to maintenance records (SQLAlchemy cascade)
- `current_mileage` auto-updated when new record added (set to record.mileage)
- Vehicle list shows service status per vehicle (section 3.3)

---

### 3.2 Maintenance Logging
**Routes:**
- `POST /vehicles/<id>/service/add` → Log maintenance + auto-create expense
- `POST /vehicles/service/edit/<id>` → Update record + linked expense
- `POST /vehicles/service/delete/<id>` → Delete record + cascade expense

**Behavior:**

When adding maintenance record:
1. Create `MaintenanceRecord` (vehicle_id, service_type_id, date, mileage, cost, provider, notes, attachment)
2. Auto-create `ExpenseEntry`:
   ```
   title = f"[{vehicle.name}] {service_type.name}"
   category = "Vehicle"
   amount = maintenance_record.cost
   date = maintenance_record.date
   attachment_path = maintenance_record.attachment_path (shared)
   payer = creator
   ```
3. Link expense: `maintenance_record.expense_id = expense.id`
4. Update vehicle: `vehicle.current_mileage = maintenance_record.mileage`

**Attachment handling:** Use existing `handle_expense_attachment()` utility (app/utils.py) — compress images, store in `uploads/` folder.

---

### 3.3 Service Alerts & Status

Compute on-demand for vehicle list page. **Status logic:**

```python
def get_service_status(vehicle, service_type, last_record):
    """Returns ('overdue' | 'warning' | 'ok', details_text)"""
    
    status = 'ok'
    alerts = []
    
    # Time-based check
    if service_type.interval_months > 0 and last_record:
        next_date = add_months(last_record.date, service_type.interval_months)
        days_left = (next_date - date.today()).days
        if days_left < 0:
            status = 'overdue'
            alerts.append(f"Overdue {-days_left} days")
        elif days_left <= 14:
            status = 'warning' if status == 'ok' else status
            alerts.append(f"Due in {days_left} days")
    
    # Mileage-based check
    if service_type.interval_km > 0:
        if last_record:
            km_left = service_type.interval_km - (vehicle.current_mileage - last_record.mileage)
        else:
            km_left = service_type.interval_km - vehicle.current_mileage
        
        if km_left < 0:
            status = 'overdue'
            alerts.append(f"Overdue {-km_left:.0f} km")
        elif km_left <= 500:
            status = 'warning' if status == 'ok' else status
            alerts.append(f"Due in {km_left:.0f} km")
    
    return status, " | ".join(alerts)
```

**Display on `/vehicles` list:**
- 🔴 **Overdue** — red badge
- 🟡 **Warning** (≤14 days or ≤500km) — yellow badge
- 🟢 **OK** — no badge

---

### 3.4 Service Types Management
**Routes:**
- `GET /vehicles` (tab: Service Types) → List predefined types
- `POST /vehicles/service-types/add` → Add type
- `POST /vehicles/service-types/edit/<id>` → Update interval
- `POST /vehicles/service-types/delete/<id>` → Soft-delete (is_active=False)

**Pre-populated defaults:**
```
Oil Change           | 5000 km | 3 months
Tire Rotation        | 10000 km | 6 months
Air Filter Change    | 15000 km | 12 months
Pajak Tahunan        | — | 12 months
STNK Perpanjangan    | — | 5 years (60 months)
Inspeksi Rutin       | 10000 km | —
Repair/Service       | — | —
```

---

## 4. User Interface

### 4.1 Main Page: `/vehicles`

Tab-driven layout (similar to expenses.html):

**Tab 1: Vehicles (default)**
```
[Vehicles]  [Service Types]  [History]

📋 My Vehicles
─────────────────────────────────────────
🚗 Mobil Keluarga (B 1234 ABC)
   Current: 45,000 km
   
   🔴 Oil Change overdue (44,700 km, 120 days)
   🟡 Pajak Tahunan due in 15 days
   
   [View]  [Add Service]  [Edit]  [Delete]

─────────────────────────────────────────
🏍️ Motor Ayah (D 5678 XYZ)
   Current: 12,500 km
   ✅ All services OK
   
   [View]  [Add Service]  [Edit]  [Delete]

─────────────────────────────────────────
[+ Add Vehicle]
```

**Tab 2: Service Types**
```
Predefined Service Types

Oil Change
├─ Interval: 5000 km or 3 months
├─ [Edit]  [Delete]

Pajak Tahunan
├─ Interval: 12 months
├─ [Edit]  [Delete]

[+ Add Service Type]
```

**Tab 3: History**
```
All Maintenance Records

Filters: [Vehicle ▼] [Type ▼] [Date Range]

2026-06-28 | Oil Change | 45,000 km | Rp 150,000 | Bengkel XYZ
2026-05-15 | Pajak Tahunan | 44,500 km | Rp 2,000,000 | Dishub
2026-04-10 | Tire Rotation | 43,000 km | Rp 200,000 | Bengkel XYZ
```

---

### 4.2 Vehicle Detail: `/vehicles/<id>`

```
🚗 Mobil Keluarga
Plat: B 1234 ABC | Type: Car
Current Mileage: 45,000 km

[Edit Vehicle]  [Delete Vehicle]

─────────────────────────────────────────
Service History (newest first)

2026-06-28  Oil Change  45,000 km
            Bengkel XYZ
            Rp 150,000
            Ganti oli + filter udara
            [Attachment: receipt.jpg]
            [Edit]  [Delete]

2026-05-15  Pajak Tahunan  44,500 km
            Dishub
            Rp 2,000,000
            [Edit]  [Delete]

─────────────────────────────────────────
[+ Add Service Record]
```

---

### 4.3 Add/Edit Forms

**Add Maintenance Record Modal:**
```
Vehicle: [Mobil Keluarga ▼]
Service Type: [Oil Change ▼]
Date: [2026-06-28]
Mileage: [45000]
Cost: [150000]
Provider: [Bengkel XYZ]
Notes: [Ganti oli + filter udara]
Attachment: [Upload receipt]
Auto-create Expense: [✓ Yes]

[Save]  [Cancel]
```

---

## 5. Integration Points

### 5.1 Expense Integration
- Maintenance record → auto-creates ExpenseEntry with category "Vehicle"
- User sees cost in `/expenses` dashboard under vehicle name
- Expense linked bidirectionally (can view originating maintenance from expense)

### 5.2 Recurring Reminders (Future)
Optional: Create reminder from maintenance record (e.g., "Tire rotation due"). Could use existing `RecurringReminder` model, but MVP skips this (alerts computed inline).

### 5.3 Dashboard Widget (Future)
Could add "Service Alerts" widget to homepage showing overdue/warning vehicles. MVP places alerts only on `/vehicles`.

---

## 6. File Structure

```
app/
├─ models.py               # Add Vehicle, ServiceType, MaintenanceRecord
├─ blueprints/
│  ├─ vehicles.py          # New blueprint (routes)
│  └─ __init__.py           # Register vehicle_bp
templates/
├─ vehicles.html            # Main page (tabs, list, forms)
└─ vehicles_detail.html     # Vehicle detail view
```

---

## 7. Error Handling

- **Vehicle not found:** 404 (GET /vehicles/<id>)
- **Delete vehicle with records:** Confirm dialog → cascade delete
- **Invalid mileage:** Flash warning, don't update current_mileage
- **Missing attachment:** No file required, optional
- **Expense creation fails:** Log error, rollback, flash user message

---

## 8. Testing

Test files: `tests/test_vehicles.py`

**Coverage:**
- Create/edit/delete vehicle
- Log maintenance record (cost, mileage auto-update)
- Expense auto-creation + linking
- Service status alerts (overdue/warning/ok)
- Mileage delta calculations
- Attachment handling (file cleanup on delete)

---

## 9. Appendix: Sample Data

**Vehicles:**
```
1. Mobil Keluarga | car | B 1234 ABC | 45000 km
2. Motor Ayah | motorcycle | D 5678 XYZ | 12500 km
```

**ServiceTypes:**
```
1. Oil Change | 5000 km | 3 months
2. Pajak Tahunan | 0 km | 12 months
3. STNK | 0 km | 60 months
```

**MaintenanceRecords:**
```
1. Vehicle 1 | Type 1 | 2026-06-28 | 45000 km | Rp 150,000 | Bengkel XYZ
2. Vehicle 1 | Type 2 | 2026-05-15 | 44500 km | Rp 2,000,000 | Dishub
```

---

## 10. Success Criteria

✅ User can add/view/edit/delete vehicles
✅ User can log maintenance with mileage + cost
✅ Maintenance cost auto-links to expense entry
✅ Vehicle list shows service status (overdue/warning/ok)
✅ Service type intervals configurable
✅ Full maintenance history queryable per vehicle
