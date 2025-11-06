/**
 * Navigation Component
 *
 * Main navigation menu for switching between pages
 */

import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import './Navigation.css';

const Navigation: React.FC = () => {
  const location = useLocation();

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  return (
    <nav className="main-navigation">
      <Link
        to="/options"
        className={`nav-link ${isActive('/options') || isActive('/') ? 'active' : ''}`}
      >
        Options Analysis
      </Link>
      <Link
        to="/technical"
        className={`nav-link ${isActive('/technical') ? 'active' : ''}`}
      >
        Technical Analysis
      </Link>
    </nav>
  );
};

export default Navigation;
