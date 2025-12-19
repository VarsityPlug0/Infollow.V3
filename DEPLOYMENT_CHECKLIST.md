# Deployment Checklist

## Pre-deployment

- [ ] **Code Review**
  - [ ] All features working locally
  - [ ] No debug code left in production
  - [ ] All environment variables properly configured
  - [ ] Security checks completed

- [ ] **Database Preparation**
  - [ ] Schema up to date
  - [ ] Migration scripts ready if needed
  - [ ] Backup strategy defined

- [ ] **Environment Variables**
  - [ ] `SECRET_KEY` generated and secured
  - [ ] `ADMIN_PASSWORD` set to strong password
  - [ ] `HANDS_API_KEY` generated for authentication
  - [ ] Database connection strings configured
  - [ ] Proxy settings configured if needed

- [ ] **Dependencies**
  - [ ] `requirements.txt` up to date
  - [ ] All dependencies compatible with target environment
  - [ ] No unused dependencies

## Deployment Options

### Render Deployment

- [ ] GitHub repository updated with latest code
- [ ] Render account ready
- [ ] Web service configuration:
  - [ ] Build command: `pip install -r requirements.txt`
  - [ ] Start command: `gunicorn --worker-class gevent --workers 1 --bind 0.0.0.0:$PORT app:app`
  - [ ] Environment variables set
- [ ] PostgreSQL database provisioned (optional but recommended)
- [ ] Custom domain configured (if needed)

### Docker Deployment

- [ ] Dockerfile validated
- [ ] Image builds successfully
- [ ] Container runs locally
- [ ] Environment variables passed correctly
- [ ] Ports mapped correctly
- [ ] Health checks passing

## Post-deployment

- [ ] **Application Verification**
  - [ ] Home page loads
  - [ ] Admin login works
  - [ ] API endpoints responsive
  - [ ] Socket.IO connections working

- [ ] **Database Connection**
  - [ ] Application can read/write to database
  - [ ] Tables created successfully
  - [ ] Sample data accessible

- [ ] **Security Checks**
  - [ ] Admin panel protected
  - [ ] API endpoints require authentication where needed
  - [ ] No sensitive information exposed

- [ ] **Performance Monitoring**
  - [ ] Response times acceptable
  - [ ] Memory usage within limits
  - [ ] Error rates within acceptable range

## Ongoing Maintenance

- [ ] **Monitoring Setup**
  - [ ] Application logs monitored
  - [ ] Error alerts configured
  - [ ] Performance metrics tracked

- [ ] **Backup Strategy**
  - [ ] Database backups scheduled
  - [ ] Session files backed up regularly
  - [ ] Recovery procedures documented

- [ ] **Updates and Upgrades**
  - [ ] Dependency updates monitored
  - [ ] Security patches applied
  - [ ] Compatibility testing performed