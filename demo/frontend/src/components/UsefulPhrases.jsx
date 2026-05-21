/**
 * UsefulPhrases Component
 * Displays contextually relevant Japanese terms/nouns with loading overlay and copy functionality
 */

import { useState } from 'react';
import { FiMessageSquare } from 'react-icons/fi';

export default function UsefulPhrases({ phrases, isLoading }) {
  const hasPhrases = phrases && phrases.length > 0;
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [showingCopiedIcon, setShowingCopiedIcon] = useState(null);

  const handleCopy = (phrase, index) => {
    const textToCopy = `${phrase.japanese} (${phrase.romaji}) - ${phrase.english}`;
    navigator.clipboard.writeText(textToCopy).then(() => {
      setCopiedIndex(index);
      setShowingCopiedIcon(index);
      // Keep the copied state for 2s, then fade out
      setTimeout(() => {
        setCopiedIndex(null);
        // Delay icon change until after fade-out animation completes
        setTimeout(() => setShowingCopiedIcon(null), 200);
      }, 2000);
    }).catch(err => {
      console.error('Failed to copy:', err);
    });
  };

  return (
    <div className="rounded-xl shadow-sm h-full relative bg-gradient-to-br from-gray-100 via-gray-200 to-gray-100  p-[2px]">
      <div className="bg-white rounded-[10px] p-4 sm:p-6 h-full relative flex flex-col">
      <h2 className="text-lg sm:text-xl font-bold text-gray-800 mb-3 sm:mb-4 flex items-center gap-2">
        <FiMessageSquare className="w-5 h-5 sm:w-6 sm:h-6 text-gray-700" />
        Key Terms
      </h2>

      {!hasPhrases ? (
        <div className="text-gray-500 text-center flex-1 flex flex-col items-center justify-center">
          <p className="mb-2">No terms extracted yet.</p>
          <p className="text-sm">Essential Japanese vocabulary will appear here.</p>
        </div>
      ) : (
        <div className={`space-y-3 ${isLoading ? 'opacity-50' : ''}`}>
          {phrases.map((phrase, index) => (
            <div key={index} className="border-b border-gray-100 pb-3 last:border-b-0 group relative">
              <div className="flex items-center justify-between gap-2">
                <div className="flex-1">
                  <div className="text-gray-900 font-medium text-lg">{phrase.japanese}</div>
                  <div className="text-sm text-gray-600 italic">{phrase.romaji}</div>
                  <div className="text-sm text-gray-700 mt-1">{phrase.english}</div>
                </div>
                <div className="relative flex-shrink-0">
                  <button
                    onClick={() => handleCopy(phrase, index)}
                    disabled={isLoading}
                    className={`${copiedIndex === index ? 'bg-green-100 scale-100 opacity-100' : 'bg-gray-100 hover:bg-gray-200 scale-0 group-hover:scale-100 opacity-0 group-hover:opacity-100'} transition-all duration-200 w-6 h-6 rounded-md flex items-center justify-center disabled:opacity-30`}
                    title="Copy to clipboard"
                    aria-label={`Copy ${phrase.japanese}`}
                  >
                    {showingCopiedIcon === index ? (
                      <svg
                        className="w-4 h-4 text-green-600"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                    ) : (
                      <svg
                        className="w-4 h-4 text-gray-600"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                        />
                      </svg>
                    )}
                  </button>
                  {copiedIndex === index && (
                    <div className="absolute top-1/2 -translate-y-1/2 right-full mr-2 bg-green-600 text-white text-xs font-medium px-3 py-1.5 rounded-md shadow-lg whitespace-nowrap z-10" style={{ animation: 'fadeIn 0.15s ease-out' }}>
                      Copied!
                    </div>
                  )}
                </div>
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
      </div>
    </div>
  );
}
