import { useState, useEffect } from 'react';
import { Business, Product } from '../types/business';

interface UseBusinessReturn {
  business: Business | null;
  products: Product[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export const useBusiness = (businessId: string): UseBusinessReturn => {
  const [business, setBusiness] = useState<Business | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchBusinessData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch business details
      const businessResponse = await fetch(`/api/businesses/${businessId}`);
      if (!businessResponse.ok) {
        throw new Error('Business not found');
      }
      const businessData = await businessResponse.json();

      // For backward compatibility, check if it's using the old restaurant endpoint
      if (!businessData.business_id) {
        // Try restaurant endpoint
        const restaurantResponse = await fetch(`/api/restaurants/${businessId}`);
        if (restaurantResponse.ok) {
          const restaurantData = await restaurantResponse.json();
          // Convert restaurant data to business format
          businessData.business_id = restaurantData.restaurant_id;
          businessData.business_type = 'restaurant';
          businessData.data = {
            ...restaurantData,
            restaurant_story: restaurantData.restaurant_story,
            menu: restaurantData.menu
          };
        }
      }

      setBusiness(businessData);

      // Fetch products if not included
      if (!businessData.products && businessData.product_count > 0) {
        const productsResponse = await fetch(`/api/businesses/${businessId}/products`);
        if (productsResponse.ok) {
          const productsData = await productsResponse.json();
          setProducts(productsData.products || []);
        }
      } else if (businessData.data?.menu) {
        // Convert menu items to products for restaurants
        const menuProducts = businessData.data.menu.map((item: any) => ({
          id: item.id || `${businessId}_${item.dish?.replace(/\s+/g, '_')}`,
          business_id: businessId,
          name: item.dish || item.name,
          description: item.item_description || item.description,
          price: item.price || 0,
          category: item.category || 'Other',
          product_type: 'menu_item',
          available: item.available !== false,
          ingredients: item.ingredients || [],
          allergens: item.allergens || [],
          dietary_tags: item.dietary_tags || []
        }));
        setProducts(menuProducts);
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load business data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (businessId) {
      fetchBusinessData();
    }
  }, [businessId]);

  return {
    business,
    products,
    loading,
    error,
    refetch: fetchBusinessData
  };
};

// Hook for listing businesses
interface UseBusinessListReturn {
  businesses: Business[];
  loading: boolean;
  error: string | null;
  total: number;
  refetch: () => void;
}

export const useBusinessList = (
  businessType?: string,
  search?: string,
  skip: number = 0,
  limit: number = 20
): UseBusinessListReturn => {
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchBusinesses = async () => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams();
      if (businessType && businessType !== 'all') params.append('business_type', businessType);
      if (search) params.append('search', search);
      params.append('skip', skip.toString());
      params.append('limit', limit.toString());

      const response = await fetch(`/api/businesses?${params}`);
      if (!response.ok) {
        throw new Error('Failed to fetch businesses');
      }

      const data = await response.json();
      setBusinesses(data.businesses || []);
      setTotal(data.total || 0);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load businesses');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBusinesses();
  }, [businessType, search, skip, limit]);

  return {
    businesses,
    loading,
    error,
    total,
    refetch: fetchBusinesses
  };
};