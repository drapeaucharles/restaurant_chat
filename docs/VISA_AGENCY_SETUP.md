# Visa Agency Setup Guide

This guide explains how to set up and use the visa agency vertical alongside the existing restaurant system.

## Overview

The visa agency system is a complete vertical that clones the working restaurant system pattern but for visa processing. It includes:

- **Multi-flow AI orchestration** (router → profiler → normalizer → recommender → clarifier → explainer/quote → application/checklist → tracker)
- **GPU-first processing** with MIA backend integration
- **Profile-driven recommendations** based on customer data
- **Robust handling of partial answers** and incomplete profiles
- **Complete application lifecycle** from inquiry to visa collection

## Feature Flag

The visa agency system is controlled by the `MIA_VISA_ENABLED` environment variable:

```bash
# Enable visa agency features
export MIA_VISA_ENABLED=true

# Disable visa agency features (default)
export MIA_VISA_ENABLED=false
```

When disabled, the system falls back to restaurant functionality without any impact.

## Database Setup

### 1. Run Migrations

```bash
# Run visa database migrations
python3 migrations/run_migrations.py

# Or with force flag if MIA_VISA_ENABLED is false
python3 migrations/run_migrations.py --force
```

### 2. Seed Sample Data

```bash
# Seed sample visa agency and products
python3 seeds/visa_seed_data.py

# Or with force flag
python3 seeds/visa_seed_data.py --force
```

This creates:
- Sample visa agency: `jakarta_visa_agency`
- Indonesian visa policy pack (IDN jurisdiction)
- Visa products: A1, B1, C1, C10, C11, E28A, E28B
- Requirements and eligibility rules

## API Endpoints

### Chat Endpoint
```http
POST /visa/chat
Content-Type: application/json

{
  "message": "I want to visit Indonesia for tourism",
  "client_id": "uuid-here",
  "restaurant_id": "jakarta_visa_agency"
}
```

### Lead Management
```http
# Create lead
POST /visa/leads
{
  "client_name": "John Doe",
  "client_email": "john@example.com", 
  "client_whatsapp": "+1234567890",
  "business_id": "uuid-here"
}

# Evaluate eligibility
POST /visa/leads/{lead_id}/evaluate
{
  "business_id": "uuid-here"
}
```

### Application Management
```http
# Create application
POST /visa/applications
{
  "lead_id": "uuid-here",
  "business_id": "uuid-here", 
  "product_code": "C1"
}

# Upload document
POST /visa/applications/{app_id}/upload
{
  "document_key": "passport_validity",
  "file_id": "uploaded-file-id"
}

# Check status
GET /visa/applications/{app_id}/status
```

### Product Catalog
```http
# Get all products
GET /visa/products?business_id=uuid-here

# Get requirements for specific product
GET /visa/catalog/requirements?business_id=uuid-here&product_code=C1
```

### Payments
```http
# Create payment intent
POST /visa/payments/intent
{
  "app_id": "uuid-here",
  "payment_type": "full"  # or "government_fee", "service_fee"
}
```

## Business Types

The system supports multiple business types in the same database:

- `restaurant` - Original restaurant functionality
- `visa_agency` - New visa agency functionality

Business type is determined by:
1. `businesses.type` field (new businesses table)
2. `restaurant_extensions.business_type` field (compatibility)
3. Defaults to `restaurant` if not specified

## Flow Orchestration

The visa system uses multi-flow AI orchestration:

### 1. Router Flow
Classifies user intent and extracts profile data:
- `provide_profile_data` - User providing personal information
- `ask_recommendation` - Asking for visa recommendations
- `ask_status` - Checking application status
- `upload_document` - Document upload requests
- `ask_price` - Pricing inquiries
- `ask_requirements` - Requirements questions
- `ask_processing_time` - Timeline questions
- `handoff_human` - Request human agent

### 2. Profiler Flow
Manages profile completion:
- Tracks missing fields with priority ordering
- Asks targeted questions to complete profile
- Handles partial answers gracefully
- Priority: purpose → nationality → stay_days → travel_date → passport_validity

### 3. Recommender Flow
Provides visa recommendations:
- Uses rules engine to evaluate eligibility
- Scores options based on profile fit
- Explains blocking reasons and fixes needed
- Compares visa types with key differences

### 4. Application Flow
Manages application lifecycle:
- Creates applications with document checklists
- Tracks upload progress and verification
- Manages payment intents and processing
- Provides status updates and next actions

## Rules Engine

The visa eligibility rules are defined in policy packs with a flexible DSL:

### Purpose Mapping
```json
{
  "purpose_map": {
    "tourism": ["A1", "B1", "C1"],
    "business_event": ["C10", "C11"],
    "investment": ["E28A", "E28B", "E28C"]
  }
}
```

### Hard Blocks
```json
{
  "hard_blocks": [
    {
      "if": "passport_validity_months < 6",
      "reason": "passport_validity",
      "message": "Passport must be valid for at least 6 months"
    }
  ]
}
```

### Scoring System
```json
{
  "scoring": {
    "base": {"A1": 0.95, "B1": 0.90, "C1": 0.85},
    "bonuses": [
      {
        "when": "intended_stay_days <= 30",
        "add": {"A1": 0.03, "B1": 0.01}
      }
    ],
    "penalties": [
      {
        "when": "funds_usd < 2000", 
        "sub": {"C1": 0.35}
      }
    ]
  }
}
```

## Adding New Countries/Agencies

### 1. Create New Business
```python
from models.visa_models import Business

agency = Business(
    business_id='singapore_visa_agency',
    type='visa_agency',
    name='Singapore Visa Services',
    password='hashed_password',
    data={
        'description': 'Professional visa services for Singapore',
        'contact_email': 'info@sgvisa.com'
    }
)
```

### 2. Create Policy Pack
```python
from models.visa_models import PolicyPack

policy = PolicyPack(
    business_id=agency.id,
    jurisdiction='SGP',
    version='2025-01',
    data_json={
        # Singapore-specific rules
        "purpose_map": {
            "tourism": ["SG_TOURIST"],
            "business": ["SG_BUSINESS"]
        },
        # ... other rules
    }
)
```

### 3. Create Catalog and Products
```python
from models.visa_models import Catalog, VisaProduct

catalog = Catalog(business_id=agency.id)

product = VisaProduct(
    catalog_id=catalog.id,
    product_code='SG_TOURIST',
    name='Singapore Tourist Visa',
    category='tourism',
    entry_type='single',
    first_stay_days=30,
    gov_fee_idr=750000,
    processing_sla_days=5
)
```

## Testing

### Unit Tests
```bash
# Run visa-specific tests
python3 -m pytest tests/visa/ -v

# Run all tests including visa
python3 -m pytest tests/ -v
```

### Integration Tests
```bash
# Test full visa flow
python3 tests/integration/test_visa_flow.py

# Test with sample data
python3 tests/integration/test_visa_with_seed_data.py
```

### Manual Testing
```bash
# Test chat endpoint
curl -X POST http://localhost:8000/visa/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I want to visit Indonesia",
    "client_id": "test-client-123",
    "restaurant_id": "jakarta_visa_agency"
  }'
```

## Rollback Plan

If issues arise, you can safely rollback:

### 1. Disable Feature Flag
```bash
export MIA_VISA_ENABLED=false
```

### 2. Rollback Database (if needed)
```bash
python3 migrations/run_migrations.py --rollback
```

### 3. Remove Code (if needed)
```bash
# Remove visa-specific files
rm -rf services/visa/
rm -rf routes/visa.py
rm -rf models/visa_models.py
```

The restaurant system will continue working normally as all visa functionality is additive and feature-flagged.

## Monitoring and Logs

### Key Metrics to Monitor
- Visa chat response times
- Profile completion rates
- Application conversion rates
- Payment success rates
- Error rates by flow type

### Log Locations
- Visa flow orchestration: `services/visa/v1/flows.py`
- Tool execution: `services/visa/v1/tools.py`
- API endpoints: `routes/visa.py`
- Chat service: `services/visa_chat_service.py`

### Health Check
```bash
curl http://localhost:8000/visa/health
```

## Support

For issues or questions:
1. Check the logs for specific error messages
2. Verify `MIA_VISA_ENABLED=true` is set
3. Ensure database migrations have been run
4. Test with seed data first
5. Check that MIA backend is accessible

The visa system is designed to be completely independent of restaurant functionality, so issues in one vertical should not affect the other.
