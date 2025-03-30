import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import '../styles.css';
import PasswordToggle from './PasswordToggle';

function Register() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [codeSent, setCodeSent] = useState(false);
  const [usernameError, setUsernameError] = useState('');
  const [checkingUsername, setCheckingUsername] = useState(false);
  const [sendingCode, setSendingCode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();

  // 使用防抖检查用户名
  useEffect(() => {
    if (!username) {
      setUsernameError('');
      return;
    }
    
    const checkUsername = async () => {
      try {
        setCheckingUsername(true);
        const response = await axios.post('/api/check-username', { username });
        if (!response.data.available) {
          setUsernameError(response.data.message);
        } else {
          setUsernameError('');
        }
      } catch (error) {
        setUsernameError('检查用户名失败');
      } finally {
        setCheckingUsername(false);
      }
    };
    
    const timer = setTimeout(() => {
      if (username.length >= 3) {
        checkUsername();
      }
    }, 500);
    
    return () => clearTimeout(timer);
  }, [username]);

  const handleSendCode = async () => {
    if (!email.trim()) {
      setError('请输入邮箱地址');
      return;
    }
    
    try {
      setSendingCode(true);
      setError('');
      await axios.post('/api/send-code', { email });
      setCodeSent(true);
      setError('验证码已发送到您的邮箱');
    } catch (error) {
      setError('发送验证码失败');
    } finally {
      setSendingCode(false);
    }
  };

  const handleRegister = async () => {
    // 注册前再次验证字段
    if (!username.trim() || !password.trim() || !email.trim() || !verificationCode.trim()) {
      setError('请填写所有必填字段');
      return;
    }
    
    // 注册前再次验证用户名
    if (usernameError) {
      setError(usernameError);
      return;
    }
    
    try {
      setLoading(true);
      setError('');
      
      // 验证验证码
      const verifyResponse = await axios.post('/api/verify-code', { 
        email, 
        code: verificationCode
      });
      
      if (verifyResponse.data.error) {
        setError('验证码错误');
        setLoading(false);
        return;
      }

      // 如果验证码正确，继续注册
      await axios.post('/api/register', { username, password, email });
      navigate('/login');
    } catch (error) {
      if (error.response && error.response.data.error) {
        setError(error.response.data.error);
      } else {
        setError('注册失败');
      }
    } finally {
      setLoading(false);
    }
  };

  // 处理回车键提交
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !loading && !sendingCode) {
      if (!codeSent) {
        handleSendCode();
      } else {
        handleRegister();
      }
    }
  };

  return (
    <div className="page-wrapper">
      <div className="login-container">
        <div className="hero-section">
          <div className="hero-content">
            <h1>创建您的Mercari监控账户</h1>
            <p>注册账户后，您可以设置关键词、接收邮件通知随时掌握商品动态。</p>
            
            <div className="hero-image">
              <img 
                src="/frog.gif" 
                alt="可爱的青蛙" 
                style={{
                  maxWidth: '250px',
                  borderRadius: '10px',
                  boxShadow: '0 10px 30px rgba(0, 0, 0, 0.1)'
                }}
              />
            </div>
          </div>
        </div>

        <div className="form-section">
          <div className="login-form">
            <h2>账号注册</h2>
            <form onSubmit={(e) => e.preventDefault()}>
              <div className="form-group">
                <label htmlFor="username">用户名</label>
                <input 
                  type="text" 
                  id="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  onKeyPress={handleKeyPress}
                  className={usernameError ? 'error-input' : ''}
                  placeholder="请设置用户名"
                  required
                />
                {checkingUsername && <div className="form-success">检查用户名中...</div>}
                {usernameError && <div className="error-message">{usernameError}</div>}
              </div>
              
              <div className="form-group">
                <label htmlFor="password">密码</label>
                <div className="password-field" style={{position: 'relative'}}>
                  <input 
                    type={showPassword ? "text" : "password"}
                    id="password" 
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="请设置密码"
                    required
                  />
                  <PasswordToggle 
                    showPassword={showPassword} 
                    togglePassword={() => setShowPassword(!showPassword)} 
                  />
                </div>
              </div>
              
              <div className="form-group">
                <label htmlFor="email">电子邮箱</label>
                <div className="email-group" style={{display: 'flex', gap: '8px'}}>
                  <input 
                    type="email"
                    id="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="请输入邮箱"
                    required
                    style={{flex: '3'}}
                  />
                  <button 
                    type="button"
                    onClick={handleSendCode}
                    disabled={sendingCode || codeSent || !email.trim()}
                    className="send-code-button"
                    style={{flex: '1', maxWidth: '80px'}}
                  >
                    {sendingCode ? '发送中' : (codeSent ? '已发送' : '获取验证码')}
                  </button>
                </div>
              </div>
              
              {codeSent && (
                <div className="form-group">
                  <label htmlFor="code">验证码</label>
                  <input 
                    type="text"
                    id="code" 
                    value={verificationCode}
                    onChange={(e) => setVerificationCode(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="请输入验证码"
                    required
                  />
                </div>
              )}
              
              {error && <div className="error-message">{error}</div>}
              
              <button 
                type="button"
                className="login-button"
                onClick={handleRegister}
                disabled={loading || !username.trim() || !password.trim() || !email.trim() || !verificationCode.trim() || usernameError}
              >
                {loading ? '注册中...' : '立即注册'}
              </button>
            </form>
            
            <div className="login-footer">
              <p>已有账号？</p>
              <button 
                onClick={() => navigate('/login')} 
                className="register-link"
                disabled={loading}
              >
                立即登录
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Register;