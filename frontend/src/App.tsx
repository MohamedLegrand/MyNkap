import React from 'react';
import { AppRoutes } from './routes';
import './index.css';

const App: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <AppRoutes />
    </div>
  );
};

export default App;
