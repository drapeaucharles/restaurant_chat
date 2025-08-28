import { BusinessConfig, BusinessType } from '../types/business';
import { 
  MdRestaurant, 
  MdGavel, 
  MdContentCut, 
  MdHotel, 
  MdBuild,
  MdLocalHospital,
  MdStore 
} from 'react-icons/md';

export const businessConfigs: Record<BusinessType, BusinessConfig> = {
  restaurant: {
    displayName: 'Restaurant',
    icon: 'MdRestaurant',
    primaryColor: '#4CAF50',
    productLabel: 'Menu',
    chatContext: 'Ask me about our menu, ingredients, allergens, or dietary options!',
    sections: [
      { id: 'menu', label: 'Menu', icon: 'MdRestaurant', component: 'MenuDisplay', visible: true },
      { id: 'hours', label: 'Hours', icon: 'MdSchedule', component: 'HoursDisplay', visible: true },
      { id: 'about', label: 'Our Story', icon: 'MdInfo', component: 'AboutDisplay', visible: true },
    ],
    productCategories: [
      'Breakfast',
      'Lunch',
      'Dinner',
      'Appetizers',
      'Main Course',
      'Desserts',
      'Beverages',
      'Specials'
    ],
    formFields: [
      { name: 'name', label: 'Dish Name', type: 'text', required: true },
      { name: 'description', label: 'Description', type: 'textarea', required: false },
      { name: 'price', label: 'Price', type: 'price', required: true },
      { name: 'category', label: 'Category', type: 'select', required: true },
      { name: 'ingredients', label: 'Ingredients', type: 'textarea', required: false, businessSpecific: true },
      { name: 'allergens', label: 'Allergens', type: 'multi-select', required: false, businessSpecific: true },
      { name: 'dietary_tags', label: 'Dietary Tags', type: 'multi-select', required: false, businessSpecific: true },
    ]
  },
  
  legal_visa: {
    displayName: 'Legal & Visa Services',
    icon: 'MdGavel',
    primaryColor: '#2196F3',
    productLabel: 'Services',
    chatContext: 'I can help you with visa applications, legal consultations, and document processing!',
    sections: [
      { id: 'services', label: 'Services', icon: 'MdGavel', component: 'ServicesDisplay', visible: true },
      { id: 'process', label: 'Process', icon: 'MdTimeline', component: 'ProcessDisplay', visible: true },
      { id: 'about', label: 'About Us', icon: 'MdInfo', component: 'AboutDisplay', visible: true },
    ],
    productCategories: [
      'Visa Services',
      'Company Formation',
      'Legal Consultation',
      'Document Services',
      'Property Legal',
      'Immigration Services'
    ],
    formFields: [
      { name: 'name', label: 'Service Name', type: 'text', required: true },
      { name: 'description', label: 'Description', type: 'textarea', required: true },
      { name: 'price', label: 'Price', type: 'price', required: true },
      { name: 'category', label: 'Service Category', type: 'select', required: true },
      { name: 'duration', label: 'Processing Time', type: 'text', required: false, businessSpecific: true },
      { name: 'requirements', label: 'Requirements', type: 'textarea', required: false, businessSpecific: true },
      { name: 'features', label: 'What\'s Included', type: 'textarea', required: false, businessSpecific: true },
    ]
  },
  
  salon: {
    displayName: 'Beauty Salon',
    icon: 'MdContentCut',
    primaryColor: '#E91E63',
    productLabel: 'Services',
    chatContext: 'Welcome! Ask me about our beauty services, available appointments, or pricing!',
    sections: [
      { id: 'services', label: 'Services', icon: 'MdContentCut', component: 'ServicesDisplay', visible: true },
      { id: 'gallery', label: 'Gallery', icon: 'MdPhoto', component: 'GalleryDisplay', visible: true },
      { id: 'team', label: 'Our Team', icon: 'MdPeople', component: 'TeamDisplay', visible: true },
    ],
    productCategories: [
      'Hair Services',
      'Nail Services',
      'Facial Treatments',
      'Body Treatments',
      'Makeup',
      'Packages'
    ],
    formFields: [
      { name: 'name', label: 'Service Name', type: 'text', required: true },
      { name: 'description', label: 'Description', type: 'textarea', required: true },
      { name: 'price', label: 'Price', type: 'price', required: true },
      { name: 'category', label: 'Service Category', type: 'select', required: true },
      { name: 'duration', label: 'Duration', type: 'text', required: true, placeholder: '60 minutes', businessSpecific: true },
      { name: 'staff_level', label: 'Stylist Level', type: 'select', required: false, businessSpecific: true,
        options: [
          { value: 'junior', label: 'Junior Stylist' },
          { value: 'senior', label: 'Senior Stylist' },
          { value: 'master', label: 'Master Stylist' }
        ]
      },
    ]
  },
  
  hotel: {
    displayName: 'Hotel',
    icon: 'MdHotel',
    primaryColor: '#FF5722',
    productLabel: 'Accommodations',
    chatContext: 'Welcome! I can help you with room availability, amenities, and reservations!',
    sections: [
      { id: 'rooms', label: 'Rooms', icon: 'MdHotel', component: 'RoomsDisplay', visible: true },
      { id: 'amenities', label: 'Amenities', icon: 'MdPool', component: 'AmenitiesDisplay', visible: true },
      { id: 'location', label: 'Location', icon: 'MdPlace', component: 'LocationDisplay', visible: true },
    ],
    productCategories: [
      'Standard Rooms',
      'Deluxe Rooms',
      'Suites',
      'Villas',
      'Conference Rooms',
      'Services'
    ],
    formFields: [
      { name: 'name', label: 'Room/Service Name', type: 'text', required: true },
      { name: 'description', label: 'Description', type: 'textarea', required: true },
      { name: 'price', label: 'Price per Night', type: 'price', required: true },
      { name: 'category', label: 'Category', type: 'select', required: true },
      { name: 'capacity', label: 'Guest Capacity', type: 'text', required: false, businessSpecific: true },
      { name: 'room_size', label: 'Room Size', type: 'text', required: false, placeholder: '30 sqm', businessSpecific: true },
      { name: 'features', label: 'Room Features', type: 'textarea', required: false, businessSpecific: true },
    ]
  },
  
  repair: {
    displayName: 'Repair Shop',
    icon: 'MdBuild',
    primaryColor: '#607D8B',
    productLabel: 'Services',
    chatContext: 'Need a repair? Tell me about your device issue and I\'ll help you find the right service!',
    sections: [
      { id: 'services', label: 'Services', icon: 'MdBuild', component: 'ServicesDisplay', visible: true },
      { id: 'warranty', label: 'Warranty', icon: 'MdVerifiedUser', component: 'WarrantyDisplay', visible: true },
      { id: 'contact', label: 'Contact', icon: 'MdPhone', component: 'ContactDisplay', visible: true },
    ],
    productCategories: [
      'Phone Repair',
      'Laptop Repair',
      'Tablet Repair',
      'Computer Repair',
      'Accessories',
      'Diagnostic Services'
    ],
    formFields: [
      { name: 'name', label: 'Service Name', type: 'text', required: true },
      { name: 'description', label: 'Description', type: 'textarea', required: true },
      { name: 'price', label: 'Starting Price', type: 'price', required: true },
      { name: 'category', label: 'Device Category', type: 'select', required: true },
      { name: 'duration', label: 'Repair Time', type: 'text', required: false, placeholder: '1-2 hours', businessSpecific: true },
      { name: 'warranty', label: 'Warranty Period', type: 'text', required: false, businessSpecific: true },
    ]
  },
  
  medical: {
    displayName: 'Medical Clinic',
    icon: 'MdLocalHospital',
    primaryColor: '#00BCD4',
    productLabel: 'Services',
    chatContext: 'Welcome to our clinic. I can help you with appointment scheduling and service information.',
    sections: [
      { id: 'services', label: 'Services', icon: 'MdLocalHospital', component: 'ServicesDisplay', visible: true },
      { id: 'doctors', label: 'Our Doctors', icon: 'MdPeople', component: 'DoctorsDisplay', visible: true },
      { id: 'insurance', label: 'Insurance', icon: 'MdSecurity', component: 'InsuranceDisplay', visible: true },
    ],
    productCategories: [
      'General Consultation',
      'Specialist Services',
      'Diagnostic Tests',
      'Vaccinations',
      'Health Checkups',
      'Emergency Services'
    ],
    formFields: [
      { name: 'name', label: 'Service Name', type: 'text', required: true },
      { name: 'description', label: 'Description', type: 'textarea', required: true },
      { name: 'price', label: 'Price', type: 'price', required: true },
      { name: 'category', label: 'Service Category', type: 'select', required: true },
      { name: 'duration', label: 'Appointment Duration', type: 'text', required: false, businessSpecific: true },
      { name: 'preparation', label: 'Preparation Required', type: 'textarea', required: false, businessSpecific: true },
    ]
  },
  
  retail: {
    displayName: 'Retail Store',
    icon: 'MdStore',
    primaryColor: '#9C27B0',
    productLabel: 'Products',
    chatContext: 'Welcome to our store! Ask me about products, availability, or current promotions!',
    sections: [
      { id: 'products', label: 'Products', icon: 'MdStore', component: 'ProductsDisplay', visible: true },
      { id: 'promotions', label: 'Promotions', icon: 'MdLocalOffer', component: 'PromotionsDisplay', visible: true },
      { id: 'location', label: 'Store Location', icon: 'MdPlace', component: 'LocationDisplay', visible: true },
    ],
    productCategories: [
      'Electronics',
      'Clothing',
      'Home & Garden',
      'Sports & Outdoors',
      'Books & Media',
      'Toys & Games'
    ],
    formFields: [
      { name: 'name', label: 'Product Name', type: 'text', required: true },
      { name: 'description', label: 'Description', type: 'textarea', required: true },
      { name: 'price', label: 'Price', type: 'price', required: true },
      { name: 'category', label: 'Category', type: 'select', required: true },
      { name: 'brand', label: 'Brand', type: 'text', required: false, businessSpecific: true },
      { name: 'sku', label: 'SKU', type: 'text', required: false, businessSpecific: true },
      { name: 'stock', label: 'Stock Quantity', type: 'text', required: false, businessSpecific: true },
    ]
  }
};

// Helper function to get icon component
export const getIconComponent = (iconName: string) => {
  const iconMap: Record<string, any> = {
    MdRestaurant,
    MdGavel,
    MdContentCut,
    MdHotel,
    MdBuild,
    MdLocalHospital,
    MdStore,
  };
  return iconMap[iconName] || MdStore;
};

// Helper to get business config with defaults
export const getBusinessConfig = (businessType: BusinessType): BusinessConfig => {
  return businessConfigs[businessType] || businessConfigs.restaurant;
};