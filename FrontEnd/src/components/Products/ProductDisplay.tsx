import React from 'react';
import { Product, Business } from '../../types/business';
import { getBusinessConfig } from '../../config/businessConfigs';
import { 
  MdRestaurant, 
  MdGavel, 
  MdContentCut, 
  MdHotel, 
  MdBuild,
  MdSchedule,
  MdAttachMoney,
  MdInfo
} from 'react-icons/md';

interface ProductDisplayProps {
  business: Business;
  products: Product[];
  onProductClick?: (product: Product) => void;
}

export const ProductDisplay: React.FC<ProductDisplayProps> = ({ 
  business, 
  products, 
  onProductClick 
}) => {
  const config = getBusinessConfig(business.business_type);
  
  // Group products by category
  const productsByCategory = products.reduce((acc, product) => {
    const category = product.category || 'Other';
    if (!acc[category]) acc[category] = [];
    acc[category].push(product);
    return acc;
  }, {} as Record<string, Product[]>);

  // Get category icon based on business type
  const getCategoryIcon = (category: string) => {
    if (business.business_type === 'restaurant') {
      return <MdRestaurant className="text-lg" />;
    } else if (business.business_type === 'legal_visa') {
      return <MdGavel className="text-lg" />;
    } else if (business.business_type === 'salon') {
      return <MdContentCut className="text-lg" />;
    } else if (business.business_type === 'hotel') {
      return <MdHotel className="text-lg" />;
    }
    return <MdInfo className="text-lg" />;
  };

  // Format price based on business type
  const formatPrice = (price: number, productType?: string) => {
    if (business.business_type === 'hotel' && productType === 'accommodation') {
      return `$${price}/night`;
    }
    return `$${price}`;
  };

  // Render product details based on business type
  const renderProductDetails = (product: Product) => {
    const details = [];

    // Universal fields
    if (product.duration) {
      details.push(
        <span key="duration" className="flex items-center gap-1 text-sm text-gray-600">
          <MdSchedule className="text-sm" />
          {product.duration}
        </span>
      );
    }

    // Restaurant-specific
    if (business.business_type === 'restaurant') {
      if (product.ingredients?.length) {
        details.push(
          <p key="ingredients" className="text-sm text-gray-600 mt-1">
            <span className="font-semibold">Ingredients:</span> {product.ingredients.join(', ')}
          </p>
        );
      }
      if (product.allergens?.length) {
        details.push(
          <p key="allergens" className="text-sm text-red-600 mt-1">
            <span className="font-semibold">Contains:</span> {product.allergens.join(', ')}
          </p>
        );
      }
      if (product.dietary_tags?.length) {
        details.push(
          <div key="dietary" className="flex gap-1 mt-2">
            {product.dietary_tags.map(tag => (
              <span key={tag} className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded">
                {tag}
              </span>
            ))}
          </div>
        );
      }
    }

    // Service-specific (legal, salon, medical)
    if (['legal_visa', 'salon', 'medical'].includes(business.business_type)) {
      if (product.features?.length) {
        details.push(
          <ul key="features" className="mt-2 space-y-1">
            {product.features.slice(0, 3).map((feature, idx) => (
              <li key={idx} className="text-sm text-gray-600 flex items-start">
                <span className="text-green-500 mr-1">✓</span>
                {feature}
              </li>
            ))}
          </ul>
        );
      }
    }

    // Hotel-specific
    if (business.business_type === 'hotel' && product.product_type === 'accommodation') {
      if (product.capacity) {
        details.push(
          <p key="capacity" className="text-sm text-gray-600">
            Sleeps up to {product.capacity} guests
          </p>
        );
      }
      if (product.room_size) {
        details.push(
          <p key="size" className="text-sm text-gray-600">
            Room size: {product.room_size}
          </p>
        );
      }
    }

    return details;
  };

  return (
    <div className="space-y-8">
      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-2">
          Our {config.productLabel}
        </h2>
        <p className="text-gray-600">
          {business.description || `Browse our ${config.productLabel.toLowerCase()}`}
        </p>
      </div>

      {Object.entries(productsByCategory).map(([category, categoryProducts]) => (
        <div key={category} className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            {getCategoryIcon(category)}
            <h3 className="text-xl font-semibold text-gray-800">
              {category}
            </h3>
            <span className="text-sm text-gray-500">
              ({categoryProducts.length} items)
            </span>
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {categoryProducts.map((product) => (
              <div
                key={product.id}
                className={`
                  bg-white rounded-lg shadow-md p-4 hover:shadow-lg transition-shadow
                  ${onProductClick ? 'cursor-pointer' : ''}
                `}
                onClick={() => onProductClick?.(product)}
              >
                <div className="flex justify-between items-start mb-2">
                  <h4 className="font-semibold text-lg text-gray-800">
                    {product.name}
                  </h4>
                  <span className="text-lg font-bold" style={{ color: config.primaryColor }}>
                    {formatPrice(product.price, product.product_type)}
                  </span>
                </div>

                {product.description && (
                  <p className="text-gray-600 text-sm mb-2">
                    {product.description}
                  </p>
                )}

                {renderProductDetails(product)}

                {!product.available && (
                  <div className="mt-2 text-sm text-red-600 font-semibold">
                    Currently Unavailable
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}

      {products.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          <p>No {config.productLabel.toLowerCase()} available at the moment.</p>
        </div>
      )}
    </div>
  );
};