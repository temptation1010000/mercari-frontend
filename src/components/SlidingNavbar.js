import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import Icon from './Icons';
import '../styles.css';

// 内联登出图标组件
const LogoutIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="#ffffff" xmlns="http://www.w3.org/2000/svg">
    <path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z" />
  </svg>
);

function SlidingNavbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const [activeIndex, setActiveIndex] = useState(0);
  const isAdmin = localStorage.getItem('isAdmin') === 'true';
  const username = localStorage.getItem('username');

  // 根据用户角色定义不同的导航项，去掉了退出选项
  const adminNavItems = [
    { icon: 'home', text: '管理', path: '/admin' },
    { icon: 'settings', text: '设置', path: '/settings' },
    { icon: 'status', text: '状态', path: '/monitor' }
  ];

  // 删除多余的重复项，只保留首页和监控两个选项
  const userNavItems = [
    { icon: 'home', text: '首页', path: '/settings' },
    { icon: 'monitor', text: '监控', path: '/monitor' }
  ];

  const navItems = isAdmin ? adminNavItems : userNavItems;

  useEffect(() => {
    // 根据当前路径设置活跃索引
    const currentPath = location.pathname;
    const index = navItems.findIndex(item => currentPath === item.path);
    if (index !== -1) {
      setActiveIndex(index);
    } else if (currentPath.includes('/admin')) {
      setActiveIndex(0); // 管理员页面默认选中第一项
    } else if (currentPath.includes('/settings')) {
      setActiveIndex(isAdmin ? 1 : 0); // 设置页面
    } else if (currentPath.includes('/monitor')) {
      setActiveIndex(isAdmin ? 2 : 1); // 监控页面
    }
  }, [location.pathname, isAdmin, navItems]);

  // 处理导航项点击
  const handleNavClick = (index) => {
    setActiveIndex(index);
    navigate(navItems[index].path);
  };

  // 处理退出登录
  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    localStorage.removeItem('isAdmin');
    navigate('/login');
  };

  return (
    <nav className="sliding-nav">
      <div className="username-badge">{username || '用户'}</div>
      
      {/* 独立的登出按钮 */}
      <div className="logout-floating-button" onClick={handleLogout} title="退出登录">
        <LogoutIcon />
      </div>
      
      <div className="nav-container">
        {navItems.map((item, index) => (
          <div 
            key={index}
            className={`nav-item ${index === activeIndex ? 'active' : ''}`}
            onClick={() => handleNavClick(index)}
          >
            <span className="nav__icon">
              <Icon name={item.icon} size={24} color={index === activeIndex ? "#4caf50" : "#666"} />
            </span>
            <span className="text">{item.text}</span>
          </div>
        ))}
        <div 
          className="nav-overlay" 
          style={{ left: `${activeIndex * (isAdmin ? 33.333 : 50)}%`, width: isAdmin ? '33.333%' : '50%' }}
        ></div>
      </div>
    </nav>
  );
}

export default SlidingNavbar; 