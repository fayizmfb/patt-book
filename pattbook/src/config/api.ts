// Patt Book API Configuration
export const API_CONFIG = {
  BASE_URL: 'https://patt-book.onrender.com/api',
  ENDPOINTS: {
    SEND_OTP: '/auth/send-otp',
    VERIFY_OTP: '/auth/verify-otp',
    CREATE_ACCOUNT: '/auth/create-account',
  },
  TIMEOUT: 10000, // 10 seconds
};

// Helper function to build full URLs
export const buildApiUrl = (endpoint: string): string => {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
};
