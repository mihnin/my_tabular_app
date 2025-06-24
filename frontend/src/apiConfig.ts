// src/apiConfig.ts
// Централизованный доступ к переменным окружения для API

export const BACKEND_ADDRESS = import.meta.env.VITE_BACKEND_ADDRESS || 'http://localhost';
export const BACKEND_PORT = import.meta.env.VITE_BACKEND_PORT || '8000';
export const BACKEND_URL = `${BACKEND_ADDRESS}:${BACKEND_PORT}`;
