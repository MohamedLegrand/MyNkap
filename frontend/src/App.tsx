import React from 'react';
import { AppRoutes } from './routes';
import './index.css';

const App: React.FC = () => {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <AppRoutes />
    </div>
  );
};

export default App;
