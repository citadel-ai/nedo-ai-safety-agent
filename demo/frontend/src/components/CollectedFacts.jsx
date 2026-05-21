/**
 * Collected Facts Card Component
 * Displays extracted user information with ability to remove facts
 * Loading: Shows overlay with spinner, content remains visible but disabled
 */

import { useState } from 'react';
import { FiFileText } from 'react-icons/fi';

export default function CollectedFacts({ facts, isLoading, onRemoveFact }) {
  const hasFacts = facts && facts.length > 0;
  const [factToDelete, setFactToDelete] = useState(null);

  return (
    <div className={`rounded-xl shadow-sm relative bg-gradient-to-br from-gray-100 via-gray-200 to-gray-100 p-[2px] ${!hasFacts ? 'h-full' : ''}`}>
      <div className={`bg-white rounded-[10px] p-4 sm:p-6 relative flex flex-col ${!hasFacts ? 'h-full' : ''}`}>
      <h2 className="text-lg sm:text-xl font-bold text-gray-800 mb-3 sm:mb-4 flex items-center gap-2">
        <FiFileText className="w-5 h-5 sm:w-6 sm:h-6 text-gray-700" />
        Collected Facts
      </h2>

      {!hasFacts ? (
        <div className="text-gray-500 text-center flex-1 flex flex-col items-center justify-center">
          <p className="mb-2">No facts collected yet.</p>
          <p className="text-sm">Information about your situation will appear here.</p>
        </div>
      ) : (
        <div className={`space-y-4 ${isLoading ? 'opacity-50' : ''}`}>
          {facts.map((fact, index) => (
            <div
              key={index}
              className="pl-4 relative group border-l-4 border-gray-300"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex-1">
                  <div className="text-sm text-gray-600 font-medium">{fact.label}</div>
                  <div className="text-gray-800">{fact.value}</div>
                </div>
                <button
                  onClick={() => setFactToDelete(fact.label)}
                  disabled={isLoading}
                  className="scale-0 group-hover:scale-100 opacity-0 group-hover:opacity-100 transition-all duration-200 flex-shrink-0 w-5 h-5 rounded-full bg-red-100 hover:bg-red-200 flex items-center justify-center disabled:opacity-30"
                  title="Remove this fact"
                  aria-label={`Remove ${fact.label}`}
                >
                  <svg
                    className="w-3 h-3 text-red-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      
      {/* Loading Overlay */}
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-60 rounded-xl pointer-events-none">
          <div className="flex gap-2">
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce loading-dot"></div>
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce loading-dot"></div>
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce loading-dot"></div>
          </div>
        </div>
      )}
      
      {/* Delete Confirmation Dialog */}
      {factToDelete && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-sm mx-4 shadow-2xl">
            <h3 className="text-lg font-bold text-gray-900 mb-2">Remove Fact?</h3>
            <p className="text-gray-600 mb-6">
              Are you sure you want to remove "{factToDelete}"? This action cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setFactToDelete(null)}
                className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  onRemoveFact && onRemoveFact(factToDelete);
                  setFactToDelete(null);
                }}
                className="px-4 py-2 text-white bg-red-600 hover:bg-red-700 rounded-lg font-medium transition-colors"
              >
                Remove
              </button>
            </div>
          </div>
        </div>
      )}
      </div>
    </div>
  );
}
