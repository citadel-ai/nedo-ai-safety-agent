import axios from 'axios';
import { ChatRequest, ChatResponse, FeedbackData } from './types';

// Use relative URLs when deployed (same origin), localhost for development
const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? '' // Use relative URLs in production (same origin as frontend)
  : 'http://localhost:8080'; // Use localhost for development 

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 seconds timeout for LLM responses
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const sendMessage = async (request: ChatRequest): Promise<ChatResponse> => {
  try {
    const response = await api.post<ChatResponse>('/chat', request);
    return response.data;
  } catch (error) {
    console.error('Error sending message:', error);
    throw new Error('Failed to send message. Please try again.');
  }
};

export const sendFeedback = async (feedback: FeedbackData): Promise<void> => {
  try {
    await api.post('/feedback', feedback);
  } catch (error) {
    console.error('Error sending feedback:', error);
    throw new Error('Failed to send feedback.');
  }
};

export const getHealth = async (): Promise<{ status: string; version: string; workflow_type: string }> => {
  try {
    const response = await api.get('/health');
    return response.data;
  } catch (error) {
    console.error('Error checking health:', error);
    throw new Error('Failed to check service health.');
  }
};

export const getWorkflowVisualization = async (): Promise<{ workflow: string; description: string }> => {
  try {
    const response = await api.get('/workflow/visualization');
    return response.data;
  } catch (error) {
    console.error('Error getting workflow visualization:', error);
    throw new Error('Failed to get workflow visualization.');
  }
};
