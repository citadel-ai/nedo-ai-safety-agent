import MessageBubble from './MessageBubble';
import { ChatMessage } from '../types';

interface MessageListProps {
  messages: ChatMessage[];
  onQuickReply?: (reply: string) => void;
}

const MessageList: React.FC<MessageListProps> = ({ messages, onQuickReply }) => {
  return (
    <div className="space-y-6">
      {messages.map((message, index) => (
        <div
          key={message.id}
          className={`animate-slide-up`}
          style={{ animationDelay: `${index * 0.1}s` }}
        >
          <MessageBubble message={message} onQuickReply={onQuickReply} />
        </div>
      ))}
    </div>
  );
};

export default MessageList;
