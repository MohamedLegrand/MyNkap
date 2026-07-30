import { useEffect, useState } from 'react';

// Partagé entre la landing page, le dashboard client et la console admin
// (auparavant dupliqué à l'identique dans les trois) — themeParDefaut
// permet à la console admin de démarrer en mode sombre sans dupliquer le
// hook pour autant.
export const useDarkMode = (themeParDefaut: 'light' | 'dark' = 'light') => {
  const [theme, setTheme] = useState(localStorage.getItem('theme') || themeParDefaut);

  useEffect(() => {
    const root = window.document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));

  return { theme, toggleTheme };
};
