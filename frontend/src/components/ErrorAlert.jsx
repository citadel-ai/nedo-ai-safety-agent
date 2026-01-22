/**
 * ErrorAlert Component
 * Displays prominent error messages with dismiss functionality
 */

import { FiAlertCircle, FiX } from 'react-icons/fi';

export default function ErrorAlert({ message, onDismiss }) {
  if (!message) return null;

  return (
    <div className="fixed top-2 sm:top-4 left-1/2 transform -translate-x-1/2 z-50 w-full max-w-2xl px-3 sm:px-4">
      <div className="bg-red-50 border-2 border-red-200 rounded-xl p-3 sm:p-4 shadow-lg animate-slide-down">
        <div className="flex items-start gap-2 sm:gap-3">
          <FiAlertCircle className="w-5 h-5 sm:w-6 sm:h-6 text-red-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <h3 className="text-xs sm:text-sm font-semibold text-red-900 mb-1">Error</h3>
            <p className="text-xs sm:text-sm text-red-800 break-words">{message}</p>
          </div>
          <button
            onClick={onDismiss}
            className="flex-shrink-0 text-red-400 hover:text-red-600 transition-colors p-1"
            aria-label="Dismiss error"
          >
            <FiX className="w-4 h-4 sm:w-5 sm:h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}

