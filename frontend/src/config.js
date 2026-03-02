// Central API configuration — reads from .env
// To switch between localhost and tunnl.gg, change VITE_API_URL in .env
export const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
