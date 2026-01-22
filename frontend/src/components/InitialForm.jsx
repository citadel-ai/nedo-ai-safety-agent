/**
 * InitialForm Component
 * Collects user's visa type and location before starting chat
 * Displays inline in chat area with explanation
 */

import { useState } from 'react';

const VISA_TYPES = [
  "Student (留学)",
  "Engineer/Specialist (技術・人文知識・国際業務)",
  "Skilled Labor (技能)",
  "Spouse of Japanese National (日本人の配偶者等)",
  "Dependent (家族滞在)",
  "Other",
];

const OTHER_VISA_TYPES = [
  "Highly Skilled Professional (高度専門職)",
  "Business Manager (経営・管理)",
  "Permanent Resident (永住者)",
  "Long-term Resident (定住者)",
  "Tourist (短期滞在)",
  "Intra-company Transferee (企業内転勤)",
  "Instructor (教授)",
  "Researcher (研究)",
  "Education (教育)",
  "Artist (芸術)",
  "Religious Activities (宗教)",
  "Journalist (報道)",
  "Legal/Accounting Services (法律・会計業務)",
  "Medical Services (医療)",
  "Nursing Care (介護)",
  "Designated Activities (特定活動)",
  "Cultural Activities (文化活動)",
  "Technical Intern Training (技能実習)",
  "Trainee (研修)",
  "Spouse of Permanent Resident (永住者の配偶者等)",
  "Diplomatic (外交)",
  "Official (公用)",
];

const LOCATIONS = [
  "Tokyo",
  "Yokohama",
  "Osaka",
  "Kyoto",
  "Fukuoka",
  "Other",
];

export default function InitialForm({ onSubmit }) {
  const [visaType, setVisaType] = useState('');
  const [location, setLocation] = useState('');
  const [customVisaType, setCustomVisaType] = useState('');
  const [customLocation, setCustomLocation] = useState('');
  const [conversationMode, setConversationMode] = useState('multi'); // 'single' or 'multi'

  const handleSubmit = (e) => {
    e.preventDefault();
    const finalVisaType = visaType === 'Other' ? customVisaType : visaType;
    // Capitalize first letter of each word in custom location
    const finalLocation = location === 'Other' 
      ? customLocation.split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()).join(' ')
      : location;
    onSubmit(finalVisaType, finalLocation, conversationMode);
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header - matches Chat header */}
      <div className="pb-3 sm:pb-4">
        <div className="max-w-2xl mx-auto px-1">
          <div className="flex items-center gap-2 sm:gap-3">
            <img src="/full-pic.png" alt="Japan Helpdesk" className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg" />
            <div>
              <h1 className="text-lg sm:text-xl font-bold text-gray-900">Japan Helpdesk</h1>
              <p className="text-xs text-gray-600">AI assistant for foreign residents</p>
            </div>
          </div>
        </div>
      </div>

      {/* Form Content */}
      <div className="flex-1 overflow-y-auto px-1">
        <div className="max-w-2xl mx-auto">
          {/* Explanation Card */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 sm:p-4 mb-4 sm:mb-6 mt-2 sm:mt-3">
            <div className="flex items-start gap-2 sm:gap-3">
              <div className="text-xl sm:text-2xl">ℹ️</div>
              <div>
                <h3 className="font-semibold text-blue-900 mb-1 text-sm sm:text-base">Before we start</h3>
                <p className="text-xs sm:text-sm text-blue-800">
                  We'll use your visa type and location to provide more relevant information 
                  and narrow down search results to what applies to your specific situation.
                </p>
              </div>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-6">
            {/* Conversation Mode Selection */}
            <div>
              <label className="block text-base font-semibold text-gray-900 mb-3">
                Conversation Mode
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setConversationMode('single')}
                  className={`px-3 sm:px-4 py-3 sm:py-4 rounded-xl border text-left transition-all ${
                    conversationMode === 'single'
                      ? 'bg-gray-900 text-white border-gray-900'
                      : 'bg-white text-gray-800 border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="font-medium mb-1 text-sm sm:text-base">Single Turn</div>
                  <div className={`text-xs ${conversationMode === 'single' ? 'text-gray-300' : 'text-gray-500'}`}>
                    Ask one question and get one answer
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => setConversationMode('multi')}
                  className={`px-3 sm:px-4 py-3 sm:py-4 rounded-xl border text-left transition-all ${
                    conversationMode === 'multi'
                      ? 'bg-gray-900 text-white border-gray-900'
                      : 'bg-white text-gray-800 border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="font-medium mb-1 text-sm sm:text-base">Multi Turn</div>
                  <div className={`text-xs ${conversationMode === 'multi' ? 'text-gray-300' : 'text-gray-500'}`}>
                    Have a back-and-forth conversation
                  </div>
                </button>
              </div>
            </div>

            {/* Visa Type Selection */}
            <div>
              <label className="block text-base font-semibold text-gray-900 mb-3">
                Your Visa Type
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {VISA_TYPES.map(type => {
                  // Split English and Japanese parts
                  const match = type.match(/^(.+?)\s*\(([^)]+)\)$/);
                  const english = match ? match[1] : type;
                  const japanese = match ? match[2] : null;

                  return (
                    <button
                      key={type}
                      type="button"
                      onClick={() => setVisaType(type)}
                      className={`px-4 py-3 rounded-xl border text-sm font-medium transition-all text-left ${
                        visaType === type
                          ? 'bg-gray-900 text-white border-gray-900'
                          : 'bg-white text-gray-800 border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="leading-tight">
                        <div>{english}</div>
                        {japanese && (
                          <div className={`text-xs mt-1 ${visaType === type ? 'text-blue-100' : 'text-gray-500'}`}>{japanese}</div>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
              {visaType === 'Other' && (
                <div className="relative mt-3">
                  <select
                    value={customVisaType}
                    onChange={(e) => setCustomVisaType(e.target.value)}
                    className="w-full px-4 py-3 pr-10 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white appearance-none cursor-pointer"
                    required
                  >
                    <option value="">Select a visa type...</option>
                    {OTHER_VISA_TYPES.map((type) => (
                      <option key={type} value={type}>{type}</option>
                    ))}
                  </select>
                  <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
                    <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </div>
                </div>
              )}
            </div>

            {/* Location Selection */}
            <div>
              <label className="block text-base font-semibold text-gray-900 mb-3">
                Your Location in Japan
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {LOCATIONS.map(loc => (
                  <button
                    key={loc}
                    type="button"
                    onClick={() => setLocation(loc)}
                    className={`px-4 py-3 rounded-xl border text-sm font-medium transition-all ${
                      location === loc
                        ? 'bg-gray-900 text-white border-gray-900'
                        : 'bg-white text-gray-800 border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    {loc}
                  </button>
                ))}
              </div>
              {location === 'Other' && (
                <input
                  type="text"
                  value={customLocation}
                  onChange={(e) => setCustomLocation(e.target.value)}
                  placeholder="Enter your location"
                  className="mt-3 w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  required
                />
              )}
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={!visaType || !location || (visaType === 'Other' && !customVisaType) || (location === 'Other' && !customLocation)}
              className="w-full bg-gray-900 text-white py-3 px-6 rounded-xl font-semibold hover:bg-black transition-all disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              Start Chat
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
