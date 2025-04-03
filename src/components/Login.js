import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import '../styles.css';
import PasswordToggle from './PasswordToggle';

function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      const response = await axios.post('/api/login', { username, password });
      
      if (response.data && response.data.token) {
        localStorage.setItem('token', response.data.token);
        localStorage.setItem('username', username);
        localStorage.setItem('isAdmin', response.data.isAdmin);
        
        navigate('/dashboard');
      } else {
        setError('登录失败，请重试');
      }
    } catch (error) {
      setError(error.response?.data?.error || '登录失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const goToRegister = () => {
    navigate('/register');
  };

  return (
    <div className="page-wrapper">
      <div className="login-container">
        <div className="hero-section">
          <div className="hero-content">
            <h1>Mercari 监控系统</h1>
            <p>实时监控您感兴趣的商品，第一时间收到新品通知</p>
            <div className="hero-image">
              <img src="/assets/hero-illustration.png" alt="监控系统插图" />
            </div>
          </div>
        </div>
        
        <div className="form-section">
          <div className="login-form">
            <h2>登录</h2>
            {error && <div className="error-message">{error}</div>}
            
            <form onSubmit={handleLogin}>
              <div className="form-group">
                <label htmlFor="username">用户名</label>
                <input
                  type="text"
                  id="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  placeholder="请输入用户名"
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="password">密码</label>
                <div className="password-field" style={{position: 'relative'}}>
                  <input
                    type={showPassword ? "text" : "password"}
                    id="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    placeholder="请输入密码"
                  />
                  <PasswordToggle 
                    showPassword={showPassword} 
                    togglePassword={() => setShowPassword(!showPassword)} 
                  />
                </div>
              </div>
              
              <button 
                type="submit" 
                className="login-button" 
                disabled={loading}
              >
                {loading ? '登录中...' : '登录'}
              </button>
            </form>
            
            <div className="login-footer">
              <p>还没有账号？</p>
              <button 
                onClick={goToRegister} 
                className="register-link"
                disabled={loading}
              >
                注册新账号
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Login;