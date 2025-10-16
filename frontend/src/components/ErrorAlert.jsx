/**
 * ErrorAlert Component
 * Displays prominent error messages with dismiss functionality
 */

import { FiAlertCircle, FiX } from 'react-icons/fi';

export default function ErrorAlert({ message, onDismiss }) {
  if (!message) return null;

  return (
    <div className="fixed top-4 left-1/2 transform -translate-x-1/2 z-50 w-full max-w-2xl px-4">
      <div className="bg-red-50 border-2 border-red-200 rounded-xl p-4 shadow-lg animate-slide-down">
        <div className="flex items-start gap-3">
          <FiAlertCircle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-red-900 mb-1">Error</h3>
            <p className="text-sm text-red-800">{message}</p>
          </div>
          <button
            onClick={onDismiss}
            className="flex-shrink-0 text-red-400 hover:text-red-600 transition-colors"
            aria-label="Dismiss error"
          >
            <FiX className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}

