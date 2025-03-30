import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

function Navbar() {
  const location = useLocation();
  const isLoggedIn = localStorage.getItem('token');
  const username = localStorage.getItem('username');
  const isAdmin = localStorage.getItem('isAdmin') === 'true';
  
  // 如果未登录，不显示导航栏
  if (!isLoggedIn || location.pathname === '/login' || location.pathname === '/register') {
    return null;
  }

  return (
    <div className="navbar">
      <div className="navbar-container">
        <div className="navbar-logo">
          Mercari监控系统
        </div>
        <div className="navbar-links">
          {isAdmin && (
            <Link to="/admin" className={location.pathname === '/admin' ? 'active' : ''}>
              用户管理
            </Link>
          )}
          <Link to="/settings" className={location.pathname === '/settings' ? 'active' : ''}>
            个人设置
          </Link>
          <Link to="/monitor" className={location.pathname === '/monitor' ? 'active' : ''}>
            监控状态
          </Link>
          <span className="username">你好，{username}</span>
          <button 
            className="logout-button" 
            onClick={() => {
              localStorage.removeItem('token');
              localStorage.removeItem('username');
              localStorage.removeItem('isAdmin');
              window.location.href = '/login';
            }}
          >
            退出登录
          </button>
        </div>
      </div>
    </div>
  );
}

export default Navbar; 