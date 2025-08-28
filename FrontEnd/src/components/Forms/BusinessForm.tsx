import React, { useState } from 'react';
import { Business, Product, BusinessType } from '../../types/business';
import { getBusinessConfig } from '../../config/businessConfigs';
import { 
  MdAdd, 
  MdDelete, 
  MdEdit,
  MdBusiness,
  MdEmail,
  MdPhone,
  MdLocationOn,
  MdLanguage
} from 'react-icons/md';

interface BusinessFormProps {
  business?: Business;
  onSubmit: (businessData: Partial<Business>, products: Product[]) => void;
  onCancel: () => void;
}

export const BusinessForm: React.FC<BusinessFormProps> = ({ 
  business, 
  onSubmit, 
  onCancel 
}) => {
  const [businessType, setBusinessType] = useState<BusinessType>(
    business?.business_type || 'restaurant'
  );
  const [formData, setFormData] = useState<Partial<Business>>({
    name: business?.name || '',
    email: business?.email || '',
    phone: business?.phone || '',
    address: business?.address || '',
    website: business?.website || '',
    description: business?.description || '',
    business_type: businessType,
    opening_hours: business?.opening_hours || {},
    metadata: business?.metadata || {},
    ...business
  });
  
  const [products, setProducts] = useState<Product[]>(
    business?.data?.products || []
  );
  
  const [showProductForm, setShowProductForm] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);

  const config = getBusinessConfig(businessType);

  // Handle business type change
  const handleBusinessTypeChange = (newType: BusinessType) => {
    setBusinessType(newType);
    setFormData({ ...formData, business_type: newType });
  };

  // Handle basic field changes
  const handleFieldChange = (field: string, value: any) => {
    setFormData({ ...formData, [field]: value });
  };

  // Handle metadata changes
  const handleMetadataChange = (field: string, value: any) => {
    setFormData({
      ...formData,
      metadata: { ...formData.metadata, [field]: value }
    });
  };

  // Product management
  const handleAddProduct = (product: Product) => {
    if (editingProduct) {
      setProducts(products.map(p => p.id === editingProduct.id ? product : p));
      setEditingProduct(null);
    } else {
      setProducts([...products, { ...product, id: Date.now().toString() }]);
    }
    setShowProductForm(false);
  };

  const handleEditProduct = (product: Product) => {
    setEditingProduct(product);
    setShowProductForm(true);
  };

  const handleDeleteProduct = (productId: string) => {
    setProducts(products.filter(p => p.id !== productId));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData, products);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Business Type Selection */}
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold mb-4">Business Type</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(businessConfigs).map(([type, config]) => {
            const Icon = getIconComponent(config.icon);
            return (
              <button
                key={type}
                type="button"
                onClick={() => handleBusinessTypeChange(type as BusinessType)}
                className={`
                  p-4 rounded-lg border-2 transition-all
                  ${businessType === type 
                    ? 'border-blue-500 bg-blue-50' 
                    : 'border-gray-200 hover:border-gray-300'
                  }
                `}
              >
                <Icon className="text-2xl mb-2 mx-auto" style={{ 
                  color: businessType === type ? config.primaryColor : '#666' 
                }} />
                <p className="text-sm font-medium">{config.displayName}</p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Basic Information */}
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold mb-4">Basic Information</h3>
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">
              <MdBusiness className="inline mr-1" />
              Business Name *
            </label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => handleFieldChange('name', e.target.value)}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder={`Enter ${config.displayName.toLowerCase()} name`}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              <MdEmail className="inline mr-1" />
              Email *
            </label>
            <input
              type="email"
              required
              value={formData.email}
              onChange={(e) => handleFieldChange('email', e.target.value)}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              <MdPhone className="inline mr-1" />
              Phone *
            </label>
            <input
              type="tel"
              required
              value={formData.phone}
              onChange={(e) => handleFieldChange('phone', e.target.value)}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              <MdLanguage className="inline mr-1" />
              Website
            </label>
            <input
              type="url"
              value={formData.website || ''}
              onChange={(e) => handleFieldChange('website', e.target.value)}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="https://example.com"
            />
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium mb-1">
              <MdLocationOn className="inline mr-1" />
              Address
            </label>
            <input
              type="text"
              value={formData.address || ''}
              onChange={(e) => handleFieldChange('address', e.target.value)}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium mb-1">
              Description
            </label>
            <textarea
              value={formData.description || ''}
              onChange={(e) => handleFieldChange('description', e.target.value)}
              rows={3}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder={`Describe your ${config.displayName.toLowerCase()}...`}
            />
          </div>
        </div>
      </div>

      {/* Business-specific fields */}
      {businessType === 'restaurant' && (
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h3 className="text-lg font-semibold mb-4">Restaurant Details</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">
                Restaurant Story
              </label>
              <textarea
                value={formData.data?.restaurant_story || ''}
                onChange={(e) => handleFieldChange('data', { 
                  ...formData.data, 
                  restaurant_story: e.target.value 
                })}
                rows={4}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="Tell your restaurant's story..."
              />
            </div>
          </div>
        </div>
      )}

      {businessType === 'hotel' && (
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h3 className="text-lg font-semibold mb-4">Hotel Details</h3>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">
                Star Rating
              </label>
              <select
                value={formData.metadata?.stars || ''}
                onChange={(e) => handleMetadataChange('stars', parseInt(e.target.value))}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select rating</option>
                {[1, 2, 3, 4, 5].map(star => (
                  <option key={star} value={star}>{star} Star{star > 1 ? 's' : ''}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">
                Amenities
              </label>
              <input
                type="text"
                value={formData.metadata?.amenities?.join(', ') || ''}
                onChange={(e) => handleMetadataChange('amenities', 
                  e.target.value.split(',').map(a => a.trim()).filter(a => a)
                )}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="Pool, Spa, Gym, Restaurant"
              />
            </div>
          </div>
        </div>
      )}

      {/* Products/Services */}
      <div className="bg-white p-6 rounded-lg shadow-md">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">{config.productLabel}</h3>
          <button
            type="button"
            onClick={() => {
              setEditingProduct(null);
              setShowProductForm(true);
            }}
            className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          >
            <MdAdd /> Add {config.productLabel.slice(0, -1)}
          </button>
        </div>

        {products.length === 0 ? (
          <p className="text-gray-500 text-center py-8">
            No {config.productLabel.toLowerCase()} added yet
          </p>
        ) : (
          <div className="space-y-2">
            {products.map((product) => (
              <div key={product.id} className="flex items-center justify-between p-3 border rounded-lg">
                <div>
                  <h4 className="font-medium">{product.name}</h4>
                  <p className="text-sm text-gray-600">
                    {product.category} - ${product.price}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => handleEditProduct(product)}
                    className="p-2 text-blue-600 hover:bg-blue-50 rounded"
                  >
                    <MdEdit />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDeleteProduct(product.id)}
                    className="p-2 text-red-600 hover:bg-red-50 rounded"
                  >
                    <MdDelete />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Submit Buttons */}
      <div className="flex justify-end gap-4">
        <button
          type="button"
          onClick={onCancel}
          className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          {business ? 'Update' : 'Create'} Business
        </button>
      </div>

      {/* Product Form Modal */}
      {showProductForm && (
        <ProductFormModal
          config={config}
          product={editingProduct}
          businessType={businessType}
          onSave={handleAddProduct}
          onCancel={() => {
            setShowProductForm(false);
            setEditingProduct(null);
          }}
        />
      )}
    </form>
  );
};

// Product Form Modal Component
const ProductFormModal: React.FC<{
  config: any;
  product: Product | null;
  businessType: BusinessType;
  onSave: (product: Product) => void;
  onCancel: () => void;
}> = ({ config, product, businessType, onSave, onCancel }) => {
  const [formData, setFormData] = useState<Partial<Product>>(
    product || {
      name: '',
      description: '',
      price: 0,
      category: '',
      available: true,
      product_type: businessType === 'restaurant' ? 'menu_item' : 'service'
    }
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData as Product);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-semibold mb-4">
          {product ? 'Edit' : 'Add'} {config.productLabel.slice(0, -1)}
        </h3>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          {config.formFields.map((field: any) => (
            <div key={field.name}>
              <label className="block text-sm font-medium mb-1">
                {field.label} {field.required && '*'}
              </label>
              
              {field.type === 'textarea' ? (
                <textarea
                  required={field.required}
                  value={formData[field.name] || ''}
                  onChange={(e) => setFormData({ ...formData, [field.name]: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  rows={3}
                  placeholder={field.placeholder}
                />
              ) : field.type === 'select' ? (
                <select
                  required={field.required}
                  value={formData[field.name] || ''}
                  onChange={(e) => setFormData({ ...formData, [field.name]: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select {field.label}</option>
                  {(field.options || config.productCategories).map((opt: any) => (
                    <option key={opt.value || opt} value={opt.value || opt}>
                      {opt.label || opt}
                    </option>
                  ))}
                </select>
              ) : field.type === 'price' ? (
                <input
                  type="number"
                  step="0.01"
                  required={field.required}
                  value={formData.price || ''}
                  onChange={(e) => setFormData({ ...formData, price: parseFloat(e.target.value) })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="0.00"
                />
              ) : (
                <input
                  type={field.type}
                  required={field.required}
                  value={formData[field.name] || ''}
                  onChange={(e) => setFormData({ ...formData, [field.name]: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder={field.placeholder}
                />
              )}
            </div>
          ))}

          <div className="flex justify-end gap-4 mt-6">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
            >
              {product ? 'Update' : 'Add'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Import business configs
import { businessConfigs } from '../../config/businessConfigs';
import { getIconComponent } from '../../config/businessConfigs';