import React from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import Login from './components/Login';
import Register from './components/Register';
import UserSettings from './components/UserSettings';
import MonitorStatus from './components/MonitorStatus';
import AdminPanel from './components/AdminPanel';
import SlidingNavbar from './components/SlidingNavbar';  // 只保留滑动导航栏组件

// 创建一个包含路由的组件
function AppContent() {
  const location = useLocation();
  const isLoggedIn = localStorage.getItem('token');
  const isLoginPage = location.pathname === '/login' || location.pathname === '/register' || location.pathname === '/';
  
  return (
    <div className="app">
      <div className="content">
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/settings" element={<UserSettings />} />
          <Route path="/monitor" element={<MonitorStatus />} />
          <Route path="/admin" element={<AdminPanel />} />
        </Routes>
      </div>
      {/* 只在登录状态且不在登录/注册页面显示底部导航栏 */}
      {isLoggedIn && !isLoginPage && <SlidingNavbar />}
    </div>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;