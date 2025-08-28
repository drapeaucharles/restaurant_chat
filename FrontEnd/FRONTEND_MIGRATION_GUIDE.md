# Frontend Migration Guide: Restaurant → Multi-Business

## Overview
This guide helps you migrate your existing restaurant frontend to support multiple business types.

## New Files Created

1. **Types**
   - `/src/types/business.ts` - Universal business and product types

2. **Configurations**
   - `/src/config/businessConfigs.ts` - Business type configurations

3. **Components**
   - `/src/components/Products/ProductDisplay.tsx` - Replaces MenuDisplay
   - `/src/components/Forms/BusinessForm.tsx` - Replaces RestaurantForm
   - `/src/components/Chat/BusinessChatInterface.tsx` - Business-aware chat

4. **Hooks**
   - `/src/hooks/useBusiness.ts` - Business data fetching

## Migration Steps

### 1. Update Your Existing Components

#### MenuDisplay → ProductDisplay
```tsx
// Before
import { MenuDisplay } from './components/Menu/MenuDisplay';
<MenuDisplay menu={restaurant.menu} />

// After
import { ProductDisplay } from './components/Products/ProductDisplay';
<ProductDisplay business={business} products={products} />
```

#### RestaurantForm → BusinessForm
```tsx
// Before
import { RestaurantForm } from './components/Forms/RestaurantForm';
<RestaurantForm restaurant={restaurant} onSubmit={handleSubmit} />

// After
import { BusinessForm } from './components/Forms/BusinessForm';
<BusinessForm business={business} onSubmit={handleSubmit} />
```

### 2. Update Your Pages

#### Chat Page
```tsx
// pages/Chat/ChatPage.tsx
import { useBusiness } from '../../hooks/useBusiness';
import { ProductDisplay } from '../../components/Products/ProductDisplay';
import { BusinessChatInterface } from '../../components/Chat/BusinessChatInterface';

export const ChatPage = () => {
  const { businessId } = useParams();
  const { business, products, loading, error } = useBusiness(businessId);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;
  if (!business) return <NotFound />;

  return (
    <div className="container mx-auto">
      <h1>{business.name}</h1>
      <ProductDisplay business={business} products={products} />
      <BusinessChatInterface business={business} />
    </div>
  );
};
```

#### Admin Pages
```tsx
// pages/Admin/CreateBusiness.tsx (replaces CreateRestaurant.tsx)
import { BusinessForm } from '../../components/Forms/BusinessForm';

export const CreateBusiness = () => {
  const handleSubmit = async (businessData, products) => {
    // Submit to /api/businesses endpoint
    const response = await fetch('/api/businesses', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...businessData,
        products
      })
    });
  };

  return <BusinessForm onSubmit={handleSubmit} />;
};
```

### 3. Update API Calls

#### Fetching Business Data
```tsx
// Before - Restaurant specific
const response = await fetch(`/api/restaurants/${restaurantId}`);

// After - Universal business
const response = await fetch(`/api/businesses/${businessId}`);
// Falls back to restaurant endpoint for backward compatibility
```

#### Chat Endpoint
```tsx
// No change needed - still uses restaurant_id parameter
await fetch('/api/chat', {
  method: 'POST',
  body: JSON.stringify({
    restaurant_id: business.business_id, // Works for any business
    message: userMessage,
    client_id: clientId
  })
});
```

### 4. Add Business Selector

#### For Multiple Businesses
```tsx
import { useBusinessList } from '../../hooks/useBusiness';

export const BusinessSelector = () => {
  const [selectedType, setSelectedType] = useState('all');
  const { businesses, loading } = useBusinessList(selectedType);

  return (
    <div>
      {/* Type Filter */}
      <select onChange={(e) => setSelectedType(e.target.value)}>
        <option value="all">All Businesses</option>
        <option value="restaurant">Restaurants</option>
        <option value="legal_visa">Legal Services</option>
        <option value="salon">Beauty Salons</option>
        <option value="hotel">Hotels</option>
      </select>

      {/* Business Grid */}
      <div className="grid grid-cols-3 gap-4">
        {businesses.map(business => (
          <BusinessCard key={business.business_id} business={business} />
        ))}
      </div>
    </div>
  );
};
```

### 5. Backward Compatibility

The system maintains backward compatibility:

1. **Restaurant Types Still Work**
   ```tsx
   // Old restaurant interface still works
   interface Restaurant extends Business {
     restaurant_id: string; // Maps to business_id
     menu?: MenuItem[]; // Maps to products
   }
   ```

2. **API Endpoints**
   - `/api/restaurants/*` endpoints still work
   - New `/api/businesses/*` endpoints for new features

3. **Chat Integration**
   - Still uses `restaurant_id` parameter for compatibility
   - Works with any business type

### 6. Styling Based on Business Type

```tsx
import { getBusinessConfig } from '../config/businessConfigs';

const BusinessHeader = ({ business }) => {
  const config = getBusinessConfig(business.business_type);
  
  return (
    <header style={{ backgroundColor: config.primaryColor }}>
      <h1>{business.name}</h1>
      <p>{config.displayName}</p>
    </header>
  );
};
```

### 7. Quick Start Example

```tsx
// App.tsx - Add business routes
import { BrowserRouter, Routes, Route } from 'react-router-dom';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Business listing */}
        <Route path="/businesses" element={<BusinessList />} />
        
        {/* Business chat (works for any type) */}
        <Route path="/chat/:businessId" element={<ChatPage />} />
        
        {/* Admin routes */}
        <Route path="/admin/business/create" element={<CreateBusiness />} />
        <Route path="/admin/business/:id/edit" element={<EditBusiness />} />
        
        {/* Legacy restaurant routes (still work) */}
        <Route path="/restaurant/:id" element={<ChatPage />} />
      </Routes>
    </BrowserRouter>
  );
}
```

## Testing Different Business Types

1. **Legal Business**: `bali-legal-consulting`
2. **Restaurant**: Any existing restaurant ID
3. **Create Test Businesses**: Use the admin panel

## Common Issues

### Issue: Menu items not showing
**Solution**: Products are fetched separately now. Use the `useBusiness` hook which handles conversion.

### Issue: Form fields missing
**Solution**: Check `businessConfigs.ts` for business-specific fields.

### Issue: Chat not working
**Solution**: Ensure you're passing `restaurant_id` (not `business_id`) to the chat endpoint.

## Next Steps

1. Test with different business types
2. Customize UI themes per business type
3. Add business-specific features
4. Update SEO/meta tags based on business type