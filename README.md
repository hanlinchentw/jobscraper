# JobScraper - Enhanced Fork

A Python-based job scraping tool that collects job listings from multiple sources and sends automated email notifications. This is an enhanced fork of [cwwmbm/linkedinscraper](https://github.com/cwwmbm/linkedinscraper) with additional features for Google job search scraping and email notifications.

## ✨ New Features Added

- **Google Career Scraping**: Extract job listings directly from Google's job search results
- **Email Notifications**: Automated email alerts for new job postings
- **GitHub Actions Integration**: Automated daily/hourly job scraping runs

## 🚀 Features

- Scrape job listings from multiple job boards
- Google Jobs integration for comprehensive job search
- Automated email notifications for new opportunities
- Export results to CSV format
- Configurable search parameters (keywords, location, etc.)
- Automated scheduling via GitHub Actions
- Data deduplication and filtering

## 📋 Requirements

- Python 3.11+
- Gmail account with App Password (for email notifications)
- Required Python packages (see `requirements.txt`)

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/jobscraper.git
   cd jobscraper
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file or set the following environment variables:
   ```
   GMAIL_PASSWORD=your_gmail_app_password
   GMAIL_EMAIL=your_email@gmail.com
   RECIPIENT_EMAIL=recipient@example.com
   ```

## 🔧 Configuration

### Gmail Setup for Email Notifications

1. Enable 2-Factor Authentication on your Gmail account
2. Generate an App Password:
   - Go to Google Account Settings → Security → 2-Step Verification → App passwords
   - Generate a new app password for "Mail"
   - Use this 16-character password as your `GMAIL_PASSWORD`

### GitHub Actions Setup (Optional)

For automated scraping, add these secrets to your GitHub repository:

- `GMAIL_PASSWORD`: Your Gmail app password
- `GMAIL_EMAIL`: Your Gmail address
- `RECIPIENT_EMAIL`: Email address to receive notifications

Go to Settings → Secrets and variables → Actions → New repository secret

## 📊 Usage

### Basic Usage
```bash
python main.py
```

## 📁 Output

The scraper generates:
- `jobs_YYYY-MM-DD.csv`: Daily job listings in CSV format
- Console output with job count and summary
- Email notifications with job highlights (if configured)

## ⚙️ GitHub Actions Workflow

The included workflow (`.github/workflows/god-give-me-jobs.yml`) automatically:
- Runs every hour to check for new jobs
- Triggers on pushes to main branch
- Sends email notifications for new findings
- Stores results as workflow artifacts

## 📈 Example Output

```
Found 25 new jobs for 'python developer' in 'remote'
Jobs saved to: jobs_2025-06-25.csv
Email notification sent to: recipient@example.com

Top Jobs Found:
- Senior Python Developer at TechCorp (Remote) - $120k-150k
- Python Backend Engineer at StartupXYZ (San Francisco) - $100k-130k
- Full Stack Python Developer at BigTech (New York) - $110k-140k
```

#### Email sent:
![截圖 2025-06-25 下午4 37 01](https://github.com/user-attachments/assets/7167b0f4-6bf0-4612-9bbe-a1881e981851)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project maintains the same license as the original repository.

## 🙏 Acknowledgments

- Original repository by [cwwmbm](https://github.com/cwwmbm/)
- Enhanced with Google scraping and email functionality
- Built with Python, BeautifulSoup, and Selenium

## 🐛 Issues & Support

If you encounter any issues or have questions:
1. Check the existing issues in the original repository
2. Create a new issue with detailed information
3. Include error messages and environment details

---

**Note**: This is a fork of the original linkedincraper with additional features. Please respect the terms of service of job boards when scraping data.
