import React from 'react';
import { CheckCircle, AlertTriangle, XCircle } from 'lucide-react';
import { Message } from '../types';

interface MessageBannerProps {
  message: Message;
}

const MessageBanner: React.FC<MessageBannerProps> = ({ message }) => {
  if (!message.text) return null;

  const getIcon = () => {
    switch (message.type) {
      case 'success':
        return <CheckCircle className="mr-2" size={20} />;
      case 'error':
        return <XCircle className="mr-2" size={20} />;
      default:
        return <AlertTriangle className="mr-2" size={20} />;
    }
  };

  const getStyles = () => {
    switch (message.type) {
      case 'success':
        return 'bg-green-50 text-green-800 border border-green-200';
      case 'error':
        return 'bg-red-50 text-red-800 border border-red-200';
      default:
        return 'bg-blue-50 text-blue-800 border border-blue-200';
    }
  };

  return (
    <div className={`mb-6 p-4 rounded-lg ${getStyles()}`}>
      <div className="flex items-center">
        {getIcon()}
        {message.text}
      </div>
    </div>
  );
};

export default MessageBanner;