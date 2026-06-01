# HMDA Stakeholder Dashboard - Public Deployment Guide

## 🎯 Overview

The HMDA Stakeholder Dashboard is an interactive web application designed to make Home Mortgage Disclosure Act data accessible to community organizations, policymakers, researchers, and the public. This guide provides complete instructions for public deployment.

## 🚀 Quick Deployment Options

### Option 1: Streamlit Cloud (Easiest)
1. **Prepare Your Repository**
   ```bash
   git init
   git add .
   git commit -m "Initial deployment setup"
   # Push to GitHub
   ```

2. **Deploy to Streamlit Cloud**
   - Visit [streamlit.io/cloud](https://streamlit.io/cloud)
   - Connect your GitHub repository
   - Set main file: `streamlit_dashboard.py` (create this from your Flask dashboard)
   - Set requirements: `requirements.txt`
   - Deploy

### Option 2: Heroku (Intermediate)
1. **Install Heroku CLI**
   ```bash
   # Follow instructions at devcenter.heroku.com/articles/heroku-cli
   ```

2. **Deploy**
   ```bash
   heroku create your-app-name
   heroku config:set FLASK_ENV=production
   heroku config:set SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
   git push heroku main
   ```

### Option 3: Docker (Advanced)
1. **Build and Run**
   ```bash
   docker build -t hmda-dashboard .
   docker run -d -p 5000:5000 --name hmda-dashboard hmda-dashboard
   ```

2. **With Docker Compose**
   ```bash
   docker-compose up -d
   ```

## 🔧 Configuration

### Environment Variables
Create a `.env` file based on `.env.example`:

```bash
# Required
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
HOST=0.0.0.0
PORT=5000

# Security
SECURE_SSL=True
RATE_LIMIT_ENABLED=True

# Data
DATA_PATH=/app/Output/Data
```

### Security Headers
The production dashboard includes:
- ✅ XSS Protection
- ✅ Content Type Options
- ✅ Frame Protection
- ✅ HTTPS Enforcement (when SSL enabled)
- ✅ Rate Limiting
- ✅ Secure Cookies

## 📊 Data Preparation

Before deployment, ensure your data is ready:

1. **Process All Years**
   ```bash
   cd D:/Arcanum/Projects/HMDA
   python comprehensive_hmda_processor_fixed.py
   ```

2. **Verify Required Files**
   - `Output/Data/enhanced_analysis/state_level.csv`
   - `Output/Data/enhanced_analysis/county_level.csv`
   - `Output/Data/enhanced_analysis/msa_level.csv`
   - `Output/Data/enhanced_analysis/race_analysis.csv`

3. **Check Data Freshness**
   - Files should be less than 1 year old
   - Include 2024 data for maximum relevance

## 🌐 Domain Setup

### Option 1: Subdomain
- `hmda.yourorganization.org`
- Points directly to dashboard

### Option 2: Path
- `yourorganization.org/hmda`
- Requires Nginx/Apache configuration

### SSL Certificate
Required for public deployment:
- **Let's Encrypt**: Free certificates
- **Cloudflare**: SSL proxy
- **AWS Certificate Manager**: If using AWS

## 📈 Performance Optimization

### Database Optimization
- Use PostgreSQL for production (instead of CSV files)
- Implement proper indexing
- Consider read replicas

### Caching Strategy
- **Data Cache**: 10 minutes (current)
- **Static Assets**: 1 day
- **API Responses**: 5 minutes

### Content Delivery Network (CDN)
- **AWS CloudFront**
- **Cloudflare**
- **Fastly**

## 🔍 Monitoring

### Health Checks
- **Endpoint**: `/api/health`
- **Monitoring**: UptimeRobot, Pingdom
- **Alerts**: Email, Slack

### Analytics
- **Google Analytics**: For user insights
- **Sentry**: For error tracking
- **Loggly**: For log aggregation

### Key Metrics
- Response time < 2 seconds
- Uptime > 99.9%
- Error rate < 0.1%

## 🔒 Security Considerations

### Data Privacy
- All data is public (from CFPB)
- No personal information stored
- Secure data transmission

### Access Control
- No authentication required (public data)
- Rate limiting prevents abuse
- Input validation and sanitization

### Compliance
- **Section 508**: Accessible design
- **GDPR**: Public data exception
- **CCPA**: Public data exception

## 📱 Accessibility

The dashboard is WCAG 2.1 AA compliant:
- ✅ Screen reader compatible
- ✅ Keyboard navigation
- ✅ High contrast mode
- ✅ Plain language
- ✅ Mobile responsive

## 🛠️ Maintenance

### Regular Updates
1. **Data Updates**: Annually when new HMDA data released
2. **Dependencies**: Monthly security updates
3. **Platform Updates**: As needed

### Backup Strategy
- **Code**: Git repository
- **Configuration**: Version controlled
- **Data**: Recreatable from source

## 📞 Support

### User Support
- **Documentation**: Built-in help
- **Contact**: Support email
- **FAQ**: Common questions

### Technical Support
- **Issues**: GitHub Issues
- **Documentation**: Technical README
- **Monitoring**: Alert notifications

## 🚦 Deployment Checklist

### Pre-Deployment
- [ ] All data processed and verified
- [ ] Security configurations set
- [ ] SSL certificate obtained
- [ ] Domain configured
- [ ] Monitoring setup

### Post-Deployment
- [ ] Health check passing
- [ ] SSL certificate working
- [ ] Performance tests passing
- [ ] Accessibility tests passing
- [ ] Analytics tracking active

## 💰 Cost Estimate

### Monthly Costs (varies by platform):

**Streamlit Cloud**: $0-20/month
- Free tier available
- Pro tier for higher usage

**Heroku**: $7-25/month
- Basic dyno: $7/month
- Add-on for SSL: $0/month (free)

**AWS**: $10-50/month
- EC2 instance: $10-20/month
- Load balancer: $18/month
- Data transfer: $5-15/month

**Docker VPS**: $5-20/month
- Basic VPS: $5-10/month
- Additional storage: $5/month

## 📚 Additional Resources

### Documentation
- [HMDA Data Guide](https://ffiec.cfpb.gov/documentation/)
- [Flask Deployment](https://flask.palletsprojects.com/en/latest/deploying/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

### Support
- **CFPB HMDA Support**: hmdahelp@cfpb.gov
- **Fair Housing Resources**: 1-800-669-9777

---

**Last Updated**: November 2024
**Version**: 1.0.0
**Contact**: Your Organization's IT/Development Team

For questions about this deployment guide, please create an issue in the project repository.