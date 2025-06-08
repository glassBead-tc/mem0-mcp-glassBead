module.exports = {
  apps: [
    {
      name: 'mem0-mcp',
      script: 'main.py',
      interpreter: 'python',
      instances: 'max', // Or set a specific number like 4
      exec_mode: 'fork', // Use 'cluster' for Node.js apps
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
        HOST: '0.0.0.0',
        PORT: 8080
      },
      env_development: {
        NODE_ENV: 'development',
        HOST: '127.0.0.1',
        PORT: 8080
      },
      // Health checks
      health_check_grace_period: 3000,
      health_check_http: {
        enabled: true,
        path: '/health', // You'll need to add this endpoint
        interval: 30000
      },
      // Restart policy
      restart_delay: 4000,
      max_restarts: 10,
      min_uptime: '10s',
      // Logging
      log_file: './logs/combined.log',
      out_file: './logs/out.log',
      error_file: './logs/error.log',
      log_date_format: 'YYYY-MM-DD HH:mm Z',
      // Load balancing setup for multiple ports
      increment_var: 'PORT'
    }
  ],
  deploy: {
    production: {
      user: 'deploy',
      host: ['your-server.com'],
      ref: 'origin/main',
      repo: 'your-repo.git',
      path: '/var/www/mem0-mcp',
      'post-deploy': 'pip install -r requirements.txt && pm2 reload ecosystem.config.js --env production'
    }
  }
}; 