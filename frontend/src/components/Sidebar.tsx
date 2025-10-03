import { useState, useEffect } from 'react';
import { 
  XMarkIcon, 
  TrashIcon, 
  InformationCircleIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline';
import { getHealth, getWorkflowVisualization } from '../api';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onClearChat: () => void;
  sessionId: string | null;
  messageCount: number;
}

const Sidebar: React.FC<SidebarProps> = ({ 
  isOpen, 
  onClose, 
  onClearChat, 
  sessionId, 
  messageCount 
}) => {
  const [systemInfo, setSystemInfo] = useState<any>(null);
  const [workflowInfo, setWorkflowInfo] = useState<any>(null);
  const [showWorkflow, setShowWorkflow] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadSystemInfo();
    }
  }, [isOpen]);

  const loadSystemInfo = async () => {
    try {
      const health = await getHealth();
      setSystemInfo(health);
    } catch (error) {
      console.error('Failed to load system info:', error);
    }
  };

  const loadWorkflowInfo = async () => {
    try {
      const workflow = await getWorkflowVisualization();
      setWorkflowInfo(workflow);
      setShowWorkflow(true);
    } catch (error) {
      console.error('Failed to load workflow info:', error);
    }
  };

  const handleClearChat = () => {
    if (window.confirm('Are you sure you want to clear the chat history?')) {
      onClearChat();
      onClose();
    }
  };

  return (
    <>
      <div className={`fixed inset-y-0 left-0 z-50 w-80 bg-gradient-to-b from-white to-warm-gray-50 shadow-2xl transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0 ${
        isOpen ? 'translate-x-0' : '-translate-x-full'
      }`}>
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b-2 border-japan-blue bg-white">
            <h2 className="text-lg font-bold text-warm-gray-900 flex items-center">
              <span className="mr-2">📋</span>
              Menu
            </h2>
            <button
              onClick={onClose}
              className="p-2 rounded-lg text-warm-gray-500 hover:text-japan-blue hover:bg-blue-50 transition-colors duration-200 lg:hidden"
              aria-label="Close menu"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-6">
            {/* Session Info */}
            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-4 border border-blue-100 shadow-sm">
              <h3 className="text-sm font-bold text-warm-gray-900 mb-3 flex items-center">
                <span className="mr-2">💬</span>
                Current Session
              </h3>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-warm-gray-600">Status</span>
                  <span className="font-semibold text-japan-blue">
                    {sessionId ? 'Active' : 'Not started'}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-warm-gray-600">Messages</span>
                  <span className="font-semibold text-warm-gray-900">{messageCount}</span>
                </div>
                {sessionId && (
                  <div className="text-xs text-warm-gray-500 mt-2 font-mono bg-white rounded px-2 py-1">
                    ID: {sessionId.slice(-12)}
                  </div>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="space-y-2">
              <h3 className="text-sm font-bold text-warm-gray-900 mb-2 flex items-center">
                <span className="mr-2">⚡</span>
                Quick Actions
              </h3>
              <button
                onClick={handleClearChat}
                className="w-full flex items-center space-x-3 px-4 py-3 text-left text-warm-gray-700 hover:text-japan-blue bg-white hover:bg-blue-50 rounded-xl transition-all duration-200 border border-warm-gray-200 hover:border-japan-blue shadow-sm hover:shadow-md group"
              >
                <TrashIcon className="w-5 h-5 group-hover:scale-110 transition-transform" />
                <span className="font-medium">Clear Chat History</span>
              </button>

              <button
                onClick={loadWorkflowInfo}
                className="w-full flex items-center space-x-3 px-4 py-3 text-left text-warm-gray-700 hover:text-japan-blue bg-white hover:bg-blue-50 rounded-xl transition-all duration-200 border border-warm-gray-200 hover:border-japan-blue shadow-sm hover:shadow-md group"
              >
                <ChartBarIcon className="w-5 h-5 group-hover:scale-110 transition-transform" />
                <span className="font-medium">View AI Workflow</span>
              </button>
            </div>

            {/* System Information */}
            {systemInfo && (
              <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-4 border border-green-100 shadow-sm">
                <h3 className="text-sm font-bold text-green-900 mb-3 flex items-center">
                  <InformationCircleIcon className="w-5 h-5 mr-2" />
                  System Status
                </h3>
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-warm-gray-600">Status</span>
                    <span className="font-semibold text-green-700">{systemInfo.status}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-warm-gray-600">Version</span>
                    <span className="font-mono text-green-700">{systemInfo.version}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-warm-gray-600">Framework</span>
                    <span className="font-semibold text-green-700">{systemInfo.workflow_type}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Workflow Visualization */}
            {showWorkflow && workflowInfo && (
              <div className="bg-warm-gray-50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-medium text-warm-gray-900">Workflow</h3>
                  <button
                    onClick={() => setShowWorkflow(false)}
                    className="text-warm-gray-500 hover:text-warm-gray-700"
                  >
                    <XMarkIcon className="w-4 h-4" />
                  </button>
                </div>
                <div className="text-xs text-warm-gray-600 space-y-2">
                  <pre className="whitespace-pre-wrap font-mono text-xs overflow-x-auto">
                    {workflowInfo.description}
                  </pre>
                </div>
              </div>
            )}

            {/* About This Demo */}
            <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-4 border border-purple-100 shadow-sm">
              <h3 className="text-sm font-bold text-purple-900 mb-3 flex items-center">
                <span className="mr-2">ℹ️</span>
                About This Demo
              </h3>
              <div className="space-y-2 text-xs text-warm-gray-700">
                <p className="leading-relaxed">
                  This is a <span className="font-semibold text-purple-700">reference implementation</span> showcasing production-ready AI best practices.
                </p>
                <div className="space-y-1.5 mt-3">
                  <div className="flex items-start space-x-2">
                    <span className="text-purple-600 mt-0.5">✓</span>
                    <span><strong>Governance Guardrails:</strong> Input validation, safety checks, scope enforcement</span>
                  </div>
                  <div className="flex items-start space-x-2">
                    <span className="text-purple-600 mt-0.5">✓</span>
                    <span><strong>Observability:</strong> Full tracing, monitoring, and error handling</span>
                  </div>
                  <div className="flex items-start space-x-2">
                    <span className="text-purple-600 mt-0.5">✓</span>
                    <span><strong>Production Patterns:</strong> Circuit breakers, retry logic, graceful degradation</span>
                  </div>
                  <div className="flex items-start space-x-2">
                    <span className="text-purple-600 mt-0.5">✓</span>
                    <span><strong>Enterprise Ready:</strong> Security, compliance, and scalability built-in</span>
                  </div>
                </div>
                <div className="mt-3 pt-3 border-t border-purple-200">
                  <p className="text-xs text-purple-700 font-medium">
                    Demonstrates enterprise-grade agentic AI workflows with comprehensive safety and control mechanisms.
                  </p>
                </div>
              </div>
            </div>

            {/* AI Capabilities */}
            <div className="space-y-3">
              <h3 className="text-sm font-bold text-warm-gray-900 flex items-center">
                <span className="mr-2">🤖</span>
                AI Capabilities
              </h3>
              <div className="space-y-2 text-sm">
                <div className="flex items-center space-x-3 p-2 rounded-lg bg-white">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-warm-gray-700">Smart Input Detection</span>
                </div>
                <div className="flex items-center space-x-3 p-2 rounded-lg bg-white">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-warm-gray-700">Context-Aware Responses</span>
                </div>
                <div className="flex items-center space-x-3 p-2 rounded-lg bg-white">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-warm-gray-700">Knowledge Base Search</span>
                </div>
                <div className="flex items-center space-x-3 p-2 rounded-lg bg-white">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-warm-gray-700">Real-time Web Search</span>
                </div>
                <div className="flex items-center space-x-3 p-2 rounded-lg bg-white">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-warm-gray-700">Legal Compliance Check</span>
                </div>
              </div>
            </div>

            {/* Supported Topics */}
            <div className="space-y-3">
              <h3 className="text-sm font-bold text-warm-gray-900 flex items-center">
                <span className="mr-2">📚</span>
                Topics Covered
              </h3>
              <div className="flex flex-wrap gap-2">
                {[
                  { icon: '🛂', label: 'Visa' },
                  { icon: '🏠', label: 'Housing' },
                  { icon: '🏥', label: 'Healthcare' },
                  { icon: '🏦', label: 'Banking' },
                  { icon: '💼', label: 'Employment' },
                  { icon: '📋', label: 'Tax' },
                  { icon: '🎓', label: 'Education' },
                  { icon: '🚇', label: 'Transport' }
                ].map((topic) => (
                  <span
                    key={topic.label}
                    className="inline-flex items-center space-x-1 px-3 py-1.5 bg-gradient-to-r from-japan-blue to-blue-600 text-white text-xs font-medium rounded-full shadow-sm hover:shadow-md transition-shadow"
                  >
                    <span>{topic.icon}</span>
                    <span>{topic.label}</span>
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="p-4 border-t-2 border-warm-gray-200 bg-white">
            <div className="text-center space-y-2">
              <p className="text-sm font-bold text-warm-gray-900">Japan Helpdesk AI</p>
              <p className="text-xs text-warm-gray-500">Production AI Assistant</p>
              <div className="flex items-center justify-center space-x-2 mt-2">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-xs text-green-600 font-medium">Always Learning</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default Sidebar;
