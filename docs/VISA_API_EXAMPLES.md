# Visa Agency API Examples

This document provides comprehensive examples of using the visa agency API endpoints.

## Authentication

All visa endpoints require the `MIA_VISA_ENABLED=true` environment variable. No additional authentication is required for the examples below, but in production you should implement proper authentication.

## Complete Visa Application Flow

### 1. Create a Lead

```bash
curl -X POST "http://localhost:8000/visa/leads" \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "Sarah Johnson",
    "client_email": "sarah@example.com",
    "client_whatsapp": "+1-555-0123",
    "business_id": "jakarta_visa_agency"
  }'
```

**Response:**
```json
{
  "lead_id": "550e8400-e29b-41d4-a716-446655440000",
  "profile": {
    "client_name": "Sarah Johnson",
    "client_email": "sarah@example.com",
    "client_whatsapp": "+1-555-0123"
  },
  "completeness": 0.15,
  "status": "created"
}
```

### 2. Chat to Collect Profile Information

```bash
curl -X POST "http://localhost:8000/visa/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I want to visit Indonesia for tourism for 2 weeks",
    "client_id": "550e8400-e29b-41d4-a716-446655440000",
    "restaurant_id": "jakarta_visa_agency"
  }'
```

**Response:**
```json
{
  "answer": "Great! I can help you with your Indonesian tourist visa. I see you want to visit for 2 weeks for tourism. To recommend the best visa option, I need a few more details:\n\n1. What is your nationality?\n2. When are you planning to travel?\n\nThese details will help me suggest the most suitable visa type for your trip.",
  "response_id": "profiler",
  "confidence_score": 0.9
}
```

### 3. Continue Profile Collection

```bash
curl -X POST "http://localhost:8000/visa/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I am American and planning to travel in March 2025",
    "client_id": "550e8400-e29b-41d4-a716-446655440000", 
    "restaurant_id": "jakarta_visa_agency"
  }'
```

**Response:**
```json
{
  "answer": "Perfect! As an American citizen planning a 2-week tourist trip to Indonesia in March 2025, I can recommend the best visa options for you:\n\n**Recommended Options:**\n\n1. **A1 - Tourist Visa (Single Entry)** - Score: 0.95\n   - Stay: 30 days, extendable to 60 days\n   - Government fee: IDR 500,000 (~$33)\n   - Processing: 3 days\n   - Perfect for your 2-week trip\n\n2. **B1 - Tourist Visa (Multiple Entry)** - Score: 0.90\n   - Stay: 30 days per entry, valid 1 year\n   - Government fee: IDR 1,000,000 (~$67)\n   - Processing: 5 days\n   - Good if you plan multiple trips\n\nFor your 2-week tourism trip, the **A1 visa** is ideal and most cost-effective. Would you like me to start your application or provide more details about requirements?",
  "response_id": "recommender",
  "confidence_score": 0.9
}
```

### 4. Get Detailed Requirements

```bash
curl -X GET "http://localhost:8000/visa/products?business_id=jakarta_visa_agency"
```

**Response:**
```json
{
  "business_id": "jakarta_visa_agency",
  "products": [
    {
      "product_code": "A1",
      "name": "Tourist Visa (Single Entry)",
      "category": "tourism",
      "entry_type": "single",
      "first_stay_days": 30,
      "extendable_to_days": 60,
      "convertible": false,
      "sponsor_needed": false,
      "gov_fee_idr": 500000,
      "processing_sla_days": 3,
      "notes": "Standard tourist visa for leisure travel"
    }
  ]
}
```

### 5. Evaluate Eligibility

```bash
curl -X POST "http://localhost:8000/visa/leads/550e8400-e29b-41d4-a716-446655440000/evaluate" \
  -H "Content-Type: application/json" \
  -d '{
    "business_id": "jakarta_visa_agency"
  }'
```

**Response:**
```json
{
  "lead_id": "550e8400-e29b-41d4-a716-446655440000",
  "profile_completeness": 0.75,
  "options": [
    {
      "product_code": "A1",
      "eligibility": "eligible",
      "blocking_reasons": [],
      "warnings": [],
      "stay_days": 30,
      "extendable_to_days": 60,
      "convertible": false,
      "sponsor_needed": false,
      "gov_fee_idr": 500000,
      "processing_sla_days": 3,
      "score": 0.95
    }
  ],
  "policy_version": "2025-01"
}
```

### 6. Create Application

```bash
curl -X POST "http://localhost:8000/visa/applications" \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": "550e8400-e29b-41d4-a716-446655440000",
    "business_id": "jakarta_visa_agency",
    "product_code": "A1"
  }'
```

**Response:**
```json
{
  "application_id": "660e8400-e29b-41d4-a716-446655440001",
  "product_code": "A1",
  "checklist": [
    {
      "key": "passport_validity",
      "label": "Passport Validity",
      "uploaded": false,
      "verified": false,
      "mandatory": true,
      "spec": "Minimum 6 months validity",
      "comment": ""
    },
    {
      "key": "photo_spec",
      "label": "Photo Spec",
      "uploaded": false,
      "verified": false,
      "mandatory": true,
      "spec": "2 passport photos (4x6cm, white background)",
      "comment": ""
    }
  ],
  "status": "created"
}
```

### 7. Upload Documents

```bash
curl -X POST "http://localhost:8000/visa/applications/660e8400-e29b-41d4-a716-446655440001/upload" \
  -H "Content-Type: application/json" \
  -d '{
    "document_key": "passport_validity",
    "file_id": "passport_scan_12345"
  }'
```

**Response:**
```json
{
  "application_id": "660e8400-e29b-41d4-a716-446655440001",
  "document_key": "passport_validity",
  "checklist": [
    {
      "key": "passport_validity",
      "label": "Passport Validity", 
      "uploaded": true,
      "verified": false,
      "mandatory": true,
      "spec": "Minimum 6 months validity",
      "file_id": "passport_scan_12345",
      "uploaded_at": "2025-01-15T10:30:00Z"
    },
    {
      "key": "photo_spec",
      "label": "Photo Spec",
      "uploaded": false,
      "verified": false,
      "mandatory": true,
      "spec": "2 passport photos (4x6cm, white background)",
      "comment": ""
    }
  ],
  "missing": ["photo_spec"],
  "status": "uploaded"
}
```

### 8. Create Payment Intent

```bash
curl -X POST "http://localhost:8000/visa/payments/intent" \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": "660e8400-e29b-41d4-a716-446655440001",
    "payment_type": "full"
  }'
```

**Response:**
```json
{
  "payment_intent_id": "PI20250115103000app12345",
  "paylink": "https://payment.visaagency.com/pay/PI20250115103000app12345?amount=1000000",
  "amount_idr": 1000000,
  "expires_at": "2025-01-16T10:30:00Z",
  "status": "created"
}
```

### 9. Check Application Status

```bash
curl -X GET "http://localhost:8000/visa/applications/660e8400-e29b-41d4-a716-446655440001/status"
```

**Response:**
```json
{
  "application_id": "660e8400-e29b-41d4-a716-446655440001",
  "stage": "docs_pending",
  "substatus": "Documents: 1/2",
  "progress": 0.5,
  "next_actions": ["Upload Photo Spec"],
  "estimated_completion": "2025-01-20",
  "documents": {
    "total": 2,
    "uploaded": 1,
    "verified": 0
  }
}
```

## Chat Examples

### Tourism Inquiry
```bash
curl -X POST "http://localhost:8000/visa/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I want to visit Bali for vacation",
    "client_id": "new-client-123",
    "restaurant_id": "jakarta_visa_agency"
  }'
```

### Business Visa Inquiry
```bash
curl -X POST "http://localhost:8000/visa/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I need a visa to attend a conference in Jakarta",
    "client_id": "business-client-456", 
    "restaurant_id": "jakarta_visa_agency"
  }'
```

### Investment Visa Inquiry
```bash
curl -X POST "http://localhost:8000/visa/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I am interested in investing in Indonesian real estate and need a long-term visa",
    "client_id": "investor-client-789",
    "restaurant_id": "jakarta_visa_agency"
  }'
```

### Status Check
```bash
curl -X POST "http://localhost:8000/visa/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the status of my application?",
    "client_id": "existing-client-123",
    "restaurant_id": "jakarta_visa_agency"
  }'
```

### Pricing Inquiry
```bash
curl -X POST "http://localhost:8000/visa/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How much does a tourist visa cost?",
    "client_id": "price-inquiry-456",
    "restaurant_id": "jakarta_visa_agency"
  }'
```

## Error Handling Examples

### Feature Disabled
```bash
# When MIA_VISA_ENABLED=false
curl -X POST "http://localhost:8000/visa/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello",
    "client_id": "test",
    "restaurant_id": "test"
  }'
```

**Response:**
```json
{
  "detail": "Visa services are not currently available"
}
```

### Invalid Business ID
```bash
curl -X POST "http://localhost:8000/visa/leads" \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "Test User",
    "business_id": "nonexistent_business"
  }'
```

**Response:**
```json
{
  "detail": "Failed to create visa lead"
}
```

### Missing Application
```bash
curl -X GET "http://localhost:8000/visa/applications/nonexistent-app-id/status"
```

**Response:**
```json
{
  "detail": "Failed to get application status"
}
```

## Health Check

```bash
curl -X GET "http://localhost:8000/visa/health"
```

**Response (when enabled):**
```json
{
  "service": "visa_agency",
  "status": "available",
  "version": "v1"
}
```

**Response (when disabled):**
```json
{
  "service": "visa_agency", 
  "status": "disabled",
  "version": "v1"
}
```

## Postman Collection

You can import these examples into Postman by creating a collection with the following structure:

```json
{
  "info": {
    "name": "Visa Agency API",
    "description": "Complete visa agency API examples"
  },
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:8000"
    },
    {
      "key": "business_id", 
      "value": "jakarta_visa_agency"
    },
    {
      "key": "client_id",
      "value": "{{$guid}}"
    }
  ],
  "item": [
    {
      "name": "Create Lead",
      "request": {
        "method": "POST",
        "url": "{{base_url}}/visa/leads",
        "body": {
          "mode": "raw",
          "raw": "{\n  \"client_name\": \"Test User\",\n  \"client_email\": \"test@example.com\",\n  \"business_id\": \"{{business_id}}\"\n}"
        }
      }
    }
  ]
}
```

## Testing with Different Scenarios

### Scenario 1: Complete Tourist Application
1. Create lead with basic info
2. Chat to collect profile (nationality, purpose, dates)
3. Get recommendations (A1 visa recommended)
4. Create application
5. Upload all required documents
6. Make payment
7. Check status until completion

### Scenario 2: Business Visa with Missing Documents
1. Create lead for business traveler
2. Get C10 visa recommendation
3. Create application
4. Upload some documents (missing invitation letter)
5. Check status (shows missing documents)
6. Upload remaining documents
7. Complete application

### Scenario 3: Investment Visa Consultation
1. Create lead for investor
2. Chat about investment plans
3. Get E28A recommendation with high requirements
4. Discuss requirements and timeline
5. Request human agent consultation

These examples demonstrate the complete visa agency workflow from initial inquiry to visa collection.
