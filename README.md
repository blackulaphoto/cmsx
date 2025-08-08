# Case Manager Suite (CMSX)

A comprehensive case management platform designed for social workers, legal professionals, and case managers to efficiently manage client cases, benefits, housing, legal services, and more.

## 🚀 Features

### Core Modules
- **Case Management**: Complete client case tracking and management
- **Benefits Assessment**: Disability and benefits eligibility evaluation
- **Housing Services**: Housing assistance and resource management
- **Legal Services**: Expungement and legal case management
- **Resume Builder**: AI-powered resume creation and optimization
- **Job Search**: Employment assistance and job matching
- **AI Assistant**: Intelligent case management assistance
- **Reminders**: Automated task and appointment reminders

### Advanced Features
- **AI-Enhanced Services**: Machine learning for case optimization
- **Multi-Database Architecture**: Scalable data management
- **Real-time Scrapers**: Automated data collection from various sources
- **Comprehensive Reporting**: Analytics and insights
- **Mobile-Responsive UI**: Modern web interface

## 🛠️ Technology Stack

- **Backend**: Python (Flask)
- **Frontend**: React.js
- **Database**: SQLite (multiple databases for modularity)
- **AI/ML**: Custom AI services and integrations
- **PDF Generation**: Resume and document creation
- **Web Scraping**: Automated data collection

## 📋 Prerequisites

- Python 3.8+
- Node.js 14+
- Git

## 🚀 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/blackulaphoto/cmsx.git
   cd cmsx
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. **Initialize the database**
   ```bash
   python init_database.py
   ```

## 🏃‍♂️ Running the Application

### Option 1: Using the launch script (Recommended)
```bash
python launch_platform.py
```

### Option 2: Manual startup
```bash
# Start the backend
python main.py

# In another terminal, start the frontend
cd frontend
npm start
```

The application will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5000

## 📁 Project Structure

```
CASE_MANAGER_SUITE2/
├── backend/                 # Backend Flask application
│   ├── api/                # API endpoints
│   ├── modules/            # Feature modules
│   │   ├── ai/            # AI services
│   │   ├── benefits/      # Benefits assessment
│   │   ├── case_management/ # Case management
│   │   ├── housing/       # Housing services
│   │   ├── legal/         # Legal services
│   │   ├── resume/        # Resume builder
│   │   └── reminders/     # Reminder system
│   └── shared/            # Shared utilities
├── frontend/              # React frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   └── api/          # API integration
├── databases/             # SQLite databases
├── config/               # Configuration files
├── docs/                 # Documentation
├── tests/                # Test files
└── static/               # Static assets
```

## 🔧 Configuration

The application uses multiple configuration files:
- `config/main_config.py` - Main application configuration
- `config/config.py` - Environment-specific settings

## 🧪 Testing

Run the comprehensive test suite:
```bash
python -m pytest tests/
```

For end-to-end testing:
```bash
npm test
```

## 📊 Database Architecture

The platform uses a modular database approach with separate databases for:
- Case Management
- Benefits
- Housing
- Legal Services
- AI Assistant
- Reminders
- User Authentication

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the documentation in the `docs/` folder
- Review the comprehensive testing reports

## 🔄 Updates

The platform is actively maintained with regular updates for:
- Security patches
- Feature enhancements
- Performance improvements
- Bug fixes

---

**Built with ❤️ for case managers and social workers** 