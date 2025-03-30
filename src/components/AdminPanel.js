import React, { useState, useEffect } from 'react';
import axios from 'axios';
import '../styles.css';
import Icon from './Icons';

// 备用内联SVG图标
const RefreshIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="#ffffff" xmlns="http://www.w3.org/2000/svg" style={{marginRight: '6px'}}>
    <path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 9h7V2l-2.35 4.35z" />
  </svg>
);

const StatusIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="#ffffff" xmlns="http://www.w3.org/2000/svg" style={{marginRight: '6px'}}>
    <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z" />
  </svg>
);

const ChatIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="#ffffff" xmlns="http://www.w3.org/2000/svg" style={{marginRight: '6px'}}>
    <path d="M20 2H4c-1.1 0-1.99.9-1.99 2L2 22l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 9h12v2H6V9zm8 5H6v-2h8v2zm4-6H6V6h12v2z" />
  </svg>
);

function AdminPanel() {
  const [users, setUsers] = useState([]);
  const [monitorStatus, setMonitorStatus] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [perPage] = useState(10);
  const [showNotificationModal, setShowNotificationModal] = useState(false);
  const [notificationSubject, setNotificationSubject] = useState('');
  const [notificationContent, setNotificationContent] = useState('');
  const [notificationStatus, setNotificationStatus] = useState('');
  
  const token = localStorage.getItem('token');
  const username = localStorage.getItem('username');

  // 组件加载时获取用户列表
  useEffect(() => {
    fetchUsers();
  }, [currentPage]);

  // 当用户列表更新后获取监控状态
  useEffect(() => {
    if (users.length > 0) {
      fetchUsersMonitorStatus();
    }
  }, [users]);

  // 获取所有用户信息
  const fetchUsers = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/admin/users?username=${username}&page=${currentPage}&per_page=${perPage}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.data) {
        setUsers(response.data.users);
        setTotalPages(response.data.total_pages);
      } else {
        setError('返回数据格式不正确');
      }
    } catch (error) {
      setError('获取用户信息失败');
    } finally {
      setLoading(false);
    }
  };

  // 获取所有用户的监控状态
  const fetchUsersMonitorStatus = async () => {
    try {
      const statusPromises = users.map(user => 
        axios.get(`/api/monitor/status?username=${user.username}`, {
          headers: { Authorization: `Bearer ${token}` },
        })
      );
      
      const statusResults = await Promise.all(statusPromises);
      
      const statuses = {};
      statusResults.forEach((result, index) => {
        if (result.data && typeof result.data.is_running !== 'undefined') {
          statuses[users[index].username] = result.data.is_running;
        }
      });
      
      setMonitorStatus(statuses);
    } catch (error) {
      console.error('获取监控状态失败:', error);
    }
  };

  // 刷新监控状态
  const refreshStatus = () => {
    fetchUsersMonitorStatus();
  };

  // 开启或关闭用户监控
  const toggleMonitorStatus = async (user, currentStatus) => {
    try {
      setLoading(true);
      const endpoint = currentStatus ? '/api/monitor/stop' : '/api/monitor/start';
      
      await axios.post(`${endpoint}?username=${user.username}`, {}, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      // 更新状态
      setMonitorStatus(prev => ({
        ...prev,
        [user.username]: !currentStatus
      }));
    } catch (error) {
      alert(`${currentStatus ? '停止' : '启动'}监控失败`);
    } finally {
      setLoading(false);
    }
  };

  // 停止所有用户的监控
  const stopAllMonitors = async () => {
    if (!window.confirm('确定要停止所有用户的监控吗？')) {
      return;
    }

    try {
      setLoading(true);
      const response = await axios.post(`/api/admin/stop-all-monitors?username=${encodeURIComponent(username)}`, {}, {
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
      });
      
      if (response.data) {
        // 更新所有用户状态为已停止
        const updatedStatus = {};
        users.forEach(user => {
          updatedStatus[user.username] = false;
        });
        setMonitorStatus(updatedStatus);
        
        // 刷新用户列表以更新状态
        fetchUsers();
      }
    } catch (error) {
      console.error('停止所有监控失败:', error);
      alert('停止所有监控失败');
    } finally {
      setLoading(false);
    }
  };

  // 发送通知邮件
  const sendNotification = async () => {
    if (!notificationSubject.trim() || !notificationContent.trim()) {
      alert('请填写完整的邮件主题和内容');
      return;
    }

    try {
      setLoading(true);
      const response = await axios.post(
        `/api/admin/send-notification?username=${encodeURIComponent(username)}`,
        {
          subject: notificationSubject,
          content: notificationContent
        },
        {
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );
      
      if (response.data) {
        setNotificationStatus(response.data.message);
        setNotificationSubject('');
        setNotificationContent('');
        setTimeout(() => {
          setNotificationStatus('');
          setShowNotificationModal(false);
        }, 3000);
      }
    } catch (error) {
      console.error('发送通知失败:', error);
      alert('发送通知失败');
    } finally {
      setLoading(false);
    }
  };

  // 处理页码变化
  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
    }
  };

  if (loading) return (
    <div className="page-container">
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>数据加载中...</p>
      </div>
    </div>
  );

  return (
    <div className="page-container">
      <div className="container admin-container">
        <div className="section-header">
          <h2>用户管理</h2>
          <div className="section-tools">
            <button onClick={fetchUsers} className="refresh-button">
              <RefreshIcon />
              刷新用户列表
            </button>
          </div>
        </div>
        
        {users.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">👥</div>
            <p>没有找到用户数据</p>
            <button onClick={fetchUsers} className="refresh-button">
              <RefreshIcon />
              刷新
            </button>
          </div>
        ) : (
          <div className="users-list">
            <div className="admin-controls">
              <button onClick={refreshStatus} className="refresh-button">
                <RefreshIcon />
                刷新监控状态
              </button>
              <button onClick={stopAllMonitors} className="stop-all-button">
                <StatusIcon />
                停止所有监控
              </button>
              <button onClick={() => setShowNotificationModal(true)} className="send-notification-button">
                <ChatIcon />
                发送通知
              </button>
            </div>
            
            {/* 通知邮件模态框 */}
            {showNotificationModal && (
              <div className="modal-overlay">
                <div className="modal-content">
                  <h3>发送通知邮件</h3>
                  <div className="form-group">
                    <label>邮件主题：</label>
                    <input
                      type="text"
                      value={notificationSubject}
                      onChange={(e) => setNotificationSubject(e.target.value)}
                      placeholder="请输入邮件主题"
                    />
                  </div>
                  <div className="form-group">
                    <label>邮件内容：</label>
                    <textarea
                      value={notificationContent}
                      onChange={(e) => setNotificationContent(e.target.value)}
                      placeholder="请输入邮件内容"
                      rows="5"
                    />
                  </div>
                  <div className="modal-buttons">
                    <button onClick={sendNotification} className="send-button">
                      发送
                    </button>
                    <button onClick={() => setShowNotificationModal(false)} className="cancel-button">
                      取消
                    </button>
                  </div>
                  {notificationStatus && (
                    <p className="notification-status">{notificationStatus}</p>
                  )}
                </div>
              </div>
            )}
            
            <div className="table-container">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>用户名</th>
                    <th>邮箱</th>
                    <th>关键词</th>
                    <th>监控状态</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr key={user.username}>
                      <td data-label="用户名">{user.username}</td>
                      <td data-label="邮箱">{user.email}</td>
                      <td data-label="关键词">{user.keywords || '未设置'}</td>
                      <td data-label="监控状态">
                        <span className={monitorStatus[user.username] ? 'status-running' : 'status-stopped'}>
                          {monitorStatus[user.username] ? '运行中' : '已停止'}
                        </span>
                      </td>
                      <td data-label="操作">
                        <button
                          onClick={() => toggleMonitorStatus(user, monitorStatus[user.username])}
                          className={monitorStatus[user.username] ? 'stop-button' : 'start-button'}
                          disabled={!user.keywords}
                        >
                          {monitorStatus[user.username] ? '停止监控' : '启动监控'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            {/* 分页控件 */}
            <div className="pagination">
              <button 
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className="page-button"
              >
                上一页
              </button>
              <span className="page-info">
                第 {currentPage} 页 / 共 {totalPages} 页
              </span>
              <button 
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="page-button"
              >
                下一页
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default AdminPanel; 