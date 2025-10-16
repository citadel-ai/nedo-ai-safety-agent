/**
 * UsefulPlaces Component
 * Displays government offices and public facilities with Google Maps links
 */

import { FiMapPin } from 'react-icons/fi';

export default function UsefulPlaces({ places, isLoading }) {
  const hasPlaces = places && places.length > 0;

  return (
    <div className="rounded-xl shadow-sm h-full relative bg-gradient-to-br from-gray-100 via-gray-200 to-gray-100 p-[2px]">
      <div className="bg-white rounded-[10px] p-6 h-full relative flex flex-col">
      <h2 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
        <FiMapPin className="w-6 h-6 text-gray-700" />
        Useful Places
      </h2>

      {!hasPlaces ? (
        <div className="text-gray-500 text-center flex-1 flex flex-col items-center justify-center">
          <p className="mb-2">No places found yet.</p>
          <p className="text-sm">Government offices will appear here.</p>
        </div>
      ) : (
        <div className={`space-y-3 ${isLoading ? 'opacity-50' : ''}`}>
          {places.map((place, index) => (
            <a
              key={index}
              href={place.maps_url}
              target="_blank"
              rel="noopener noreferrer"
              className="block border-b border-gray-100 pb-3 last:border-b-0 hover:bg-gray-50 rounded-lg p-2 -mx-2 transition-colors"
            >
              <div>
                <div className="text-gray-900 font-medium">
                  {place.name}
                </div>
                <div className="text-sm text-gray-600">{place.address}</div>
                <div className="text-xs text-blue-500 mt-1 flex items-center gap-1">
                  View on Google Maps
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </div>
              </div>
            </a>
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
