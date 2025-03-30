import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import '../styles.css';
import Icon from './Icons';

// 刷新图标的内联SVG（备用）
const RefreshIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="#ffffff" xmlns="http://www.w3.org/2000/svg" style={{marginRight: '6px'}}>
    <path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 9h7V2l-2.35 4.35z" />
  </svg>
);

function MonitorStatus() {
  const [status, setStatus] = useState({
    is_running: false,
    last_check: '暂无',
    new_products: 0
  });
  const [avgScrapeTime, setAvgScrapeTime] = useState({
    average_time: 0,
    recent_data: [],
    count: 0
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const refreshInterval = useRef(null);
  
  const token = localStorage.getItem('token');
  const username = localStorage.getItem('username');

  useEffect(() => {
    // 组件挂载时获取状态
    fetchStatus();
    fetchAvgScrapeTime();
    
    // 设置10秒自动刷新
    refreshInterval.current = setInterval(() => {
      fetchStatus();
      fetchAvgScrapeTime();
    }, 10000);
    
    // 组件卸载时清除定时器
    return () => {
      if (refreshInterval.current) {
        clearInterval(refreshInterval.current);
      }
    };
  }, []);

  // 获取监控状态
  const fetchStatus = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/monitor/status?username=${username}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.data) {
        setStatus(response.data);
      }
    } catch (error) {
      setError('获取监控状态失败');
    } finally {
      setLoading(false);
    }
  };

  // 获取平均抓取时间
  const fetchAvgScrapeTime = async () => {
    try {
      const response = await axios.get(`/api/monitor/avg_time?username=${username}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.data) {
        setAvgScrapeTime(response.data);
      }
    } catch (error) {
      console.error("获取平均抓取时间失败", error);
    }
  };

  // 开始监控
  const startMonitor = async () => {
    try {
      setLoading(true);
      await axios.post(`/api/monitor/start?username=${username}`, {}, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      // 更新状态
      fetchStatus();
    } catch (error) {
      setError('启动监控失败');
    } finally {
      setLoading(false);
    }
  };

  // 停止监控
  const stopMonitor = async () => {
    try {
      setLoading(true);
      await axios.post(`/api/monitor/stop?username=${username}`, {}, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      // 更新状态
      fetchStatus();
    } catch (error) {
      setError('停止监控失败');
    } finally {
      setLoading(false);
    }
  };

  // 手动刷新
  const handleRefresh = () => {
    fetchStatus();
    fetchAvgScrapeTime();
  };

  return (
    <div className="page-container">
      <div className="container">
        <div className="section-header">
          <h2>监控状态</h2>
          <div className="section-tools">
            <button onClick={handleRefresh} className="refresh-button">
              <RefreshIcon />
              刷新
            </button>
          </div>
        </div>
        
        {loading && (
          <div className="loading-indicator">
            <div className="spinner"></div>
            <p>加载中...</p>
          </div>
        )}
        
        {error && (
          <div className="error-message">
            <p>{error}</p>
          </div>
        )}
        
        <div className="status-card">
          <div className="status-item">
            <span className="status-label">当前状态:</span>
            <span className={status.is_running ? 'status-running' : 'status-stopped'}>
              {status.is_running ? '运行中' : '已停止'}
            </span>
          </div>
          
          <div className="status-item">
            <span className="status-label">最后检查时间:</span>
            <span className="status-value">{status.last_check}</span>
          </div>
          
          <div className="status-item">
            <span className="status-label">新发现商品数:</span>
            <span className="status-value">{status.new_products}</span>
          </div>
          
          <div className="status-actions">
            {status.is_running ? (
              <button 
                onClick={stopMonitor} 
                className="stop-button"
                disabled={loading}
              >
                停止监控
              </button>
            ) : (
              <button 
                onClick={startMonitor} 
                className="start-button"
                disabled={loading}
              >
                开始监控
              </button>
            )}
          </div>
        </div>
        
        <div className="status-card">
          <h3>抓取性能统计</h3>
          
          <div className="status-item">
            <span className="status-label">最近{avgScrapeTime.count}次平均抓取时间:</span>
            <span className="status-value">{avgScrapeTime.average_time} 秒</span>
          </div>
          
          {avgScrapeTime.count > 0 && (
            <div className="scrape-time-chart">
              <h4>最近抓取时间记录</h4>
              <div className="time-bars">
                {avgScrapeTime.recent_data.map((item, index) => (
                  <div key={index} className="time-bar-item">
                    <div 
                      className="time-bar" 
                      style={{ 
                        height: `${Math.min(item.time * 5, 100)}px`,
                        backgroundColor: item.time > avgScrapeTime.average_time * 1.5 ? '#ff6b6b' : '#4caf50'
                      }}
                      title={`${item.timestamp}: ${item.time}秒`}
                    ></div>
                    <div className="time-value">{item.time}s</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        
        <div className="status-notes">
          <div className="note-card">
            <div className="note-icon">💡</div>
            <div className="note-content">
              <h3>监控说明</h3>
              <p>监控系统会定期检查符合您设置关键词的新商品，并通过邮件通知您。</p>
              <p>您可以在用户设置中修改关键词和邮箱。</p>
            </div>
          </div>
          
          <div className="note-card">
            <div className="note-icon">⏱️</div>
            <div className="note-content">
              <h3>自动更新</h3>
              <p>本页面每10秒自动刷新一次监控状态。</p>
              <p>您也可以点击刷新按钮立即获取最新状态。</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default MonitorStatus;