import { Bars3Icon, GlobeAltIcon } from '@heroicons/react/24/outline';

interface HeaderProps {
  onMenuClick: () => void;
  sessionId: string | null;
}

const Header: React.FC<HeaderProps> = ({ onMenuClick, sessionId }) => {
  return (
    <header className="bg-gradient-to-r from-white to-blue-50 border-b-2 border-japan-blue shadow-sm px-4 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <button
            onClick={onMenuClick}
            className="p-2 rounded-lg text-warm-gray-500 hover:text-japan-blue hover:bg-white transition-colors duration-200 lg:hidden shadow-sm"
            aria-label="Open menu"
          >
            <Bars3Icon className="w-6 h-6" />
          </button>
          
          <div className="flex items-center space-x-3">
            <div className="relative">
              <div className="flex items-center justify-center w-10 h-10 bg-gradient-to-br from-japan-red to-red-600 rounded-xl shadow-md">
                <GlobeAltIcon className="w-6 h-6 text-white" />
              </div>
              <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full border-2 border-white"></div>
            </div>
            <div>
              <h1 className="text-xl font-bold text-warm-gray-900 tracking-tight">
                🇯🇵 Japan Helpdesk
              </h1>
              <p className="text-xs text-warm-gray-600 font-medium">
                Your AI Assistant for Life in Japan
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          {sessionId && (
            <div className="hidden sm:flex items-center space-x-2 px-3 py-1.5 bg-white rounded-full shadow-sm border border-warm-gray-200">
              <span className="text-xs font-medium text-warm-gray-500">Session</span>
              <span className="text-xs font-mono text-japan-blue">{sessionId.slice(-8)}</span>
            </div>
          )}
          
          <div className="flex items-center space-x-2 px-3 py-1.5 bg-green-50 rounded-full border border-green-200">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-xs font-semibold text-green-700">Online</span>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
