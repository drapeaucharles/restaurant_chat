// Universal business types that work for any business type
export type BusinessType = 'restaurant' | 'legal_visa' | 'salon' | 'hotel' | 'repair' | 'medical' | 'retail';

export interface Business {
  business_id: string;
  name: string;
  business_type: BusinessType;
  email: string;
  phone: string;
  address?: string;
  website?: string;
  description?: string;
  logo_url?: string;
  opening_hours?: Record<string, string>;
  metadata?: BusinessMetadata;
  rag_mode?: string;
  data?: any; // Flexible data field for business-specific info
  created_at?: string;
  updated_at?: string;
}

export interface BusinessMetadata {
  theme_color?: string;
  specialties?: string[];
  languages?: string[];
  certifications?: string[];
  years_experience?: number;
  amenities?: string[];
  stars?: number; // For hotels
  [key: string]: any; // Allow business-specific metadata
}

export interface Product {
  id: string;
  business_id: string;
  name: string;
  description?: string;
  price: number;
  category: string;
  product_type: ProductType;
  available: boolean;
  image_url?: string;
  
  // Universal optional fields
  duration?: string; // For services
  features?: string[];
  requirements?: ProductRequirements;
  tags?: string[];
  
  // Restaurant-specific (optional)
  ingredients?: string[];
  allergens?: string[];
  dietary_tags?: string[];
  
  // Service-specific (optional)
  staff_level?: string;
  booking_required?: boolean;
  
  // Accommodation-specific (optional)
  capacity?: number;
  room_size?: string;
  
  [key: string]: any; // Allow business-specific fields
}

export type ProductType = 
  | 'menu_item'      // Restaurant
  | 'service'        // Legal, Salon, Medical
  | 'accommodation'  // Hotel
  | 'product'        // Retail
  | 'repair_service' // Repair shop
  | 'package';       // Bundled services

export interface ProductRequirements {
  documents?: string[];
  eligibility?: string[];
  preparation?: string[];
  duration?: string;
  [key: string]: any;
}

// Business-specific configurations
export interface BusinessConfig {
  displayName: string;
  icon: string; // Icon name for react-icons
  primaryColor: string;
  sections: SectionConfig[];
  productLabel: string; // "Menu", "Services", "Rooms", etc.
  productCategories: string[];
  chatContext: string;
  formFields: FormFieldConfig[];
}

export interface SectionConfig {
  id: string;
  label: string;
  icon?: string;
  component: string; // Component to render
  visible: boolean;
}

export interface FormFieldConfig {
  name: string;
  label: string;
  type: 'text' | 'textarea' | 'select' | 'multi-select' | 'time' | 'price' | 'image';
  required: boolean;
  placeholder?: string;
  options?: { value: string; label: string }[];
  businessSpecific?: boolean;
}

// Backward compatibility - Restaurant types
export interface Restaurant extends Business {
  restaurant_id: string; // Maps to business_id
  restaurant_story?: string;
  restaurant_categories?: string;
  menu?: MenuItem[];
}

export interface MenuItem extends Product {
  dish?: string; // Maps to name
  sub_category?: string;
  item_description?: string; // Maps to description
}