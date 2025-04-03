import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

function UserSettings() {
  const [keywords, setKeywords] = useState('');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  const token = localStorage.getItem('token');
  const navigate = useNavigate();

  // 在组件加载时获取用户配置
  useEffect(() => {
    const fetchUserConfig = async () => {
      try {
        setLoading(true);
        const username = localStorage.getItem('username');
        const response = await axios.get(`/api/user/info?username=${username}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        
        setKeywords(response.data.keywords || '');
        setEmail(response.data.email || '');
        setLoading(false);
      } catch (error) {
        setError('获取用户配置失败');
        setLoading(false);
      }
    };
    
    fetchUserConfig();
  }, [token]);

  const handleUpdate = async () => {
    try {
      const username = localStorage.getItem('username');
      await axios.post(
        `/api/user/update?username=${username}`,
        { keywords, email },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      alert('设置已更新');
    } catch (error) {
      alert('更新失败');
    }
  };

  const handleDeleteAccount = async () => {
    try {
      setDeleteError('');
      const username = localStorage.getItem('username');
      
      const response = await axios.post(
        `/api/user/delete?username=${encodeURIComponent(username)}`,
        {},
        {
          headers: { 
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
        }
      );
      
      // 清除本地存储
      localStorage.removeItem('token');
      localStorage.removeItem('username');
      localStorage.removeItem('isAdmin');
      
      // 显示成功信息
      alert('您的账户已成功注销');
      
      // 跳转到登录页面
      navigate('/login');
    } catch (error) {
      console.error('注销错误:', error);
      
      const errorMessage = error.response && error.response.data && error.response.data.error
        ? error.response.data.error
        : '注销账户失败';
      
      setDeleteError(errorMessage);
      alert(errorMessage);
    }
  };

  // 确认对话框组件
  const ConfirmationDialog = () => (
    <div className="confirmation-dialog">
      <div className="confirmation-content">
        <h3>确认注销账户</h3>
        <p>您确定要注销账户吗？此操作<strong>不可逆转</strong>，将删除您的所有数据。</p>
        {deleteError && <p className="error">{deleteError}</p>}
        <div className="button-group">
          <button 
            onClick={() => setShowConfirmation(false)} 
            className="cancel-button"
          >
            取消
          </button>
          <button 
            onClick={handleDeleteAccount} 
            className="delete-button"
          >
            确认注销
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="page-container">
      <div className="container">
        <h2>用户设置</h2>
        
        {loading ? (
          <p>加载中...</p>
        ) : error ? (
          <p className="error">{error}</p>
        ) : (
          <>
            <div className="current-config">
              <h3>当前配置</h3>
              <p><strong>关键词：</strong> {keywords || '未设置'}</p>
              <p><strong>邮箱：</strong> {email || '未设置'}</p>
            </div>
            
            <h3>修改配置</h3>
            <input
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              placeholder="关键词"
            />
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="邮箱"
            />
            <button onClick={handleUpdate}>保存</button>
          </>
        )}
        
        {/* 添加注销账户部分 */}
        <div className="delete-account-section">
          <h3>危险操作</h3>
          <p>注销账户将永久删除您的所有信息，此操作不可撤销。</p>
          <button 
            onClick={() => setShowConfirmation(true)} 
            className="delete-account-button"
          >
            注销我的账户
          </button>
        </div>
        
        {/* 显示确认对话框 */}
        {showConfirmation && <ConfirmationDialog />}
      </div>
    </div>
  );
}

export default UserSettings;