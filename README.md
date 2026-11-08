# ComicVerse - Manga/Comic Reading Platform

A modern, feature-rich manga and comic reading platform built with Flask.

## Features

✨ **Reading Experience**
- Beautiful, responsive comic reader
- Progress tracking & reading history
- Bookmarks & favorites
- Chapter navigation

👤 **User System**
- User authentication & profiles
- Follow system
- XP & leveling system
- Custom avatars & themes

📚 **Content Management**
- Multi-language support (EN/ID)
- Genre tagging
- Comic status tracking (ongoing/completed/hiatus)
- Author/artist credits

🎨 **Customization**
- Dark/light themes
- Custom backgrounds
- Profile customization

👨‍💼 **Admin Panel**
- Comic management
- User management
- Genre management
- Site settings
- Announcements
- Changelog

## Quick Start

### Requirements
- Python 3.8+
- Virtual environment (recommended)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Arthemist07/ComicVerse.git
cd ComicVerse
```

2. Create virtual environment:
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file:
```bash
cp .env.example .env
```

Edit `.env` and set your configuration (SECRET_KEY, DATABASE_URL, etc.)

5. Run the application:
```bash
python app.py
```

The site will be available at `http://127.0.0.1:5000`

### Default Admin Account

**Important:** Change this password after first login!

- **Email:** `admin@comic.com`
- **Password:** `admin123`

## Configuration

### Database
By default, uses SQLite (`sqlite:///comic.db`). For production, use PostgreSQL:

```env
DATABASE_URL=postgresql://user:password@localhost/comicverse
```

### Cloudflare R2 Storage (Optional)
For image hosting, configure R2 in `.env`:

```env
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY=your-access-key
R2_SECRET_KEY=your-secret-key
R2_BUCKET_NAME=comic-site
R2_PUBLIC_URL=https://pub-xxxxx.r2.dev
```

If not configured, images will be stored locally in `static/uploads/`

## Project Structure

```
ComicVerse/
├── app.py              # Main application
├── config.py           # Configuration
├── models.py           # Database models
├── routes/             # Route blueprints
│   ├── auth.py        # Authentication
│   ├── main.py        # Home, profile, etc.
│   ├── comic.py       # Comic pages & reader
│   ├── admin.py       # Admin panel
│   ├── api.py         # API endpoints
│   └── author.py      # Author panel
├── templates/          # HTML templates
├── static/
│   ├── css/           # Stylesheets
│   ├── js/            # JavaScript
│   └── uploads/       # User uploads (covers, avatars, etc.)
└── translations/       # i18n (en.json, id.json)
```

## Tech Stack

- **Backend:** Flask, SQLAlchemy, Flask-Login
- **Database:** SQLite (dev) / PostgreSQL (prod)
- **Storage:** Local filesystem or Cloudflare R2
- **Frontend:** Vanilla JS, Custom CSS
- **Image Processing:** Pillow

## Deployment

### Heroku
The project includes `Procfile` and `runtime.txt` for Heroku deployment:

```bash
heroku create your-app-name
heroku addons:create heroku-postgresql:mini
git push heroku main
```

### Docker (Coming Soon)
Docker support is planned for easier deployment.

## License

MIT License - feel free to use this project for your own manga/comic site!

## Contributing

Pull requests welcome! Please follow existing code style.

## Roadmap

- [ ] Docker support
- [ ] Mobile apps (React Native)
- [ ] Advanced search & filters
- [ ] Social features (comments, ratings)
- [ ] Download chapters (PDF/CBZ)
- [ ] Bulk import from external sources

---

Built with ❤️ by [Arthemist07](https://github.com/Arthemist07)
