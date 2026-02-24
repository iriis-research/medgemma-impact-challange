# NidanMitra AI - Patient Understanding & Adherence Companion

![NidanMitra AI](https://img.shields.io/badge/NidanMitra-AI%20Health%20Companion-10b99b)
![License](https://img.shields.io/badge/license-MIT-blue)

NidanMitra AI is a web-based patient assistant that empowers patients to understand, trust, and follow their medical care using an AI-powered, medically grounded conversational interface.

## 🌟 Features

### AI Chat Interface
- WhatsApp-like conversational UI
- Ask questions about health, medications, and reports
- Emergency detection with appropriate guidance
- Multilingual support (English, Spanish, Hindi)

### Medical Report Viewer
- Upload PDFs and images
- AI-powered plain-language summaries
- Risk level indicators
- Highlighted important terms

### Medication Tracker
- Daily medication checklist
- Reminder scheduling
- Side-effect reporting
- AI explanations for each medication

### Symptom Journal
- Log symptoms with severity ratings
- Timeline visualization
- Auto-generated summaries for doctor visits
- Pattern detection

### Accessibility Features
- Large font mode
- Multiple languages (i18n)
- Minimal medical jargon
- Mobile-first responsive design

## 🏗️ Architecture

```
health_app/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── api/               # API Routes
│   │   │   ├── auth.py        # Authentication
│   │   │   ├── chat.py        # AI Chat
│   │   │   ├── reports.py     # Medical Reports
│   │   │   ├── medications.py # Medication Tracking
│   │   │   └── symptoms.py    # Symptom Journal
│   │   ├── db/                # Database Models
│   │   ├── llm/               # MedGemma Integration
│   │   │   ├── medgemma_client.py
│   │   │   └── prompts.py     # Safety-first prompts
│   │   ├── security/          # Authentication
│   │   └── config.py          # Configuration
│   └── requirements.txt
│
└── frontend/                   # Next.js Frontend
    ├── src/
    │   ├── app/               # Next.js App Router
    │   │   ├── dashboard/
    │   │   ├── chat/
    │   │   ├── reports/
    │   │   ├── medications/
    │   │   ├── symptoms/
    │   │   └── settings/
    │   ├── components/        # React Components
    │   │   ├── Chat/
    │   │   ├── Reports/
    │   │   ├── Medications/
    │   │   ├── Symptoms/
    │   │   └── Layout/
    │   └── lib/               # Utilities
    │       ├── api.ts         # API Client
    │       ├── store.ts       # Zustand Store
    │       └── i18n.ts        # Internationalization
    ├── package.json
    └── tailwind.config.js
```

## 🚀 Getting Started

### Prerequisites

- **Docker & Docker Compose** (for backend services) - **Highly Recommended**
  - Docker uses Python 3.11 with full compatibility
  - No Python version issues
- **Python 3.11 or 3.12** (for native backend only)
  - ⚠️ **Python 3.14 is NOT supported** - many packages don't have compatible builds yet
- **Node.js 18+** (for frontend)
- **HuggingFace Account** (for MedGemma model access)

### Quick Start with Docker (Recommended)

#### 1. Backend Setup (Docker)

The backend runs completely in Docker with all services (PostgreSQL, Redis, Qdrant, and the API):

```bash
cd backend

# Create .env file (optional - defaults are provided)
cat > .env << EOF
# HuggingFace Token (required for MedGemma)
HF_TOKEN=your-huggingface-token-here

# Optional: Override defaults
SECRET_KEY=your-super-secret-key-change-in-production
DEBUG=false
EOF

# Start all backend services
docker compose up -d

# View logs
docker compose logs -f backend

# Stop services
docker compose down
```

The backend will be available at `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

#### 2. Frontend Setup (Native)

The frontend runs separately (not in Docker):

```bash
cd frontend

# Install dependencies
npm install

# Create .env.local file (optional - defaults to http://localhost:8000/api)
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api" > .env.local

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:3000`

### Alternative: Native Backend Setup

If you prefer to run the backend natively (useful for MPS acceleration on Mac):

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/NidanMitra
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-super-secret-key
HF_TOKEN=your-huggingface-token
QDRANT_HOST=localhost
QDRANT_PORT=6333
EOF

# Start only services (PostgreSQL, Redis, Qdrant) in Docker
docker compose -f docker-compose.services.yml up -d

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --port 8000
```

### Environment Variables

#### Backend (.env)

```env
# Database (auto-configured in Docker)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/NidanMitra

# Redis (auto-configured in Docker)
REDIS_URL=redis://redis:6379/0

# JWT Authentication
SECRET_KEY=your-super-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# HuggingFace Token (required)
HF_TOKEN=your-huggingface-token-here

# MedGemma Model
MEDGEMMA_MODEL_ID=google/medgemma-1.5-4b-it
USE_LOCAL_MODEL=true
DEVICE=cpu
USE_4BIT_QUANTIZATION=true

# Vector Database (auto-configured in Docker)
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# Application
DEBUG=false
```

#### Frontend (.env.local)

```env
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

## 🎨 Design System

NidanMitra uses a warm, trustworthy healthcare palette:

- **Primary**: Teal (`#10b99b`) - Trust and healing
- **Accent**: Orange (`#f97316`) - Warmth and energy
- **Surface**: Stone grays for backgrounds
- **Emergency**: Red for urgent alerts

### Typography
- Display: Outfit (headings)
- Body: DM Sans (content)
- Mono: JetBrains Mono (data)

## 🔒 Safety Features

The AI system includes multiple safety layers:

1. **Emergency Detection**: Automatically detects potential emergencies (chest pain, difficulty breathing, etc.) and advises seeking immediate care.

2. **No Diagnosis Policy**: The AI never provides diagnoses - it only offers educational information.

3. **Disclaimer System**: All responses include appropriate medical disclaimers.

4. **Empathy-First Prompts**: Prompts are designed to be supportive and acknowledge patient concerns.

## 🌐 Internationalization

Supported languages:
- English (en)
- Spanish (es)
- Hindi (hi)

Add new languages in `frontend/src/lib/i18n.ts`.

## 📱 Mobile-First Design

The application is designed mobile-first with:
- Responsive layouts
- Touch-friendly interactions
- Bottom-sheet modals
- Large tap targets

## 🧪 Demo Mode

The application works in demo mode without backend connection:
- Simulated AI responses
- Local data storage
- Full UI functionality

## 📚 API Documentation

When running the backend, API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🛡️ Privacy & Security

- All health data is encrypted at rest
- JWT-based authentication
- No data sharing with third parties
- HIPAA-compliant design patterns

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## ⚠️ Medical Disclaimer

NidanMitra AI provides educational health information only. It is not a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of your physician or other qualified health provider with any questions you may have regarding a medical condition.

---

Built with ❤️ for patients everywhere

