# 🤖 Multimodal  Agent AI

A production-ready AI-powered multimodal document analysis system that processes PDFs, DOCX files, and images with speech capabilities.

## ✨ Features

- 📄 **Document Processing**: PDF, DOCX, and image file analysis
- 🖼️ **Image Understanding**: OCR (Tesseract & EasyOCR) + Image Captioning
- 🎤 **Speech Recognition**: Audio transcription using Faster-Whisper
- 🔊 **Text-to-Speech**: Natural voice synthesis with Piper TTS
- 🧠 **Intelligent Retrieval**: Vector-based semantic search with ChromaDB
- 🔄 **LangGraph Workflow**: Advanced agent orchestration
- 📊 **Modern UI**: Responsive Streamlit interface

## 🏗️ Architecture

```
┌─────────────────┐
│  Streamlit UI   │
└────────┬────────┘
         │
    ┌────▼─────┐
    │  Agent   │ (LangGraph)
    └────┬─────┘
         │
    ┌────▼──────────────────────────┐
    │  Document Processor           │
    │  - PDF Reader                 │
    │  - DOCX Parser                │
    │  - Image OCR & Captioning     │
    └───────────────────────────────┘
         │
    ┌────▼──────────────────────────┐
    │  Vector Store (ChromaDB)      │
    │  - Embeddings                 │
    │  - Similarity Search          │
    └───────────────────────────────┘
         │
    ┌────▼──────────────────────────┐
    │  LLM (LM Studio)              │
    │  - Local/Cloud Models         │
    │  - Context-aware Generation   │
    └───────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker (for containerized deployment)
- LM Studio (for local LLM)
- Tesseract OCR

### Local Development

1. **Clone the repository**
```bash
git clone https://github.com/ruhul-cse-duet/Multimodal-AI-Agent-Qwen2-pdf-image-STT-TTS.git
cd Multimodal-AI-Agent-Qwen2-pdf-image-STT-TTS
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Start LM Studio** (for local LLM)
- Download and launch LM Studio
- Load your preferred model
- Ensure server is running on port 1234

6. **Run the FastAPI backend**
```bash
uvicorn api:app --reload --port 8000
```

7. **Run the Streamlit UI**
```bash
streamlit run app.py
```

8. **Access the UI**
Navigate to `http://localhost:8501`

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Build and start
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Manual Docker Build

```bash
# Build image
docker build -t multimodal-vox-agent .

# Run container
docker run -p 8501:8501 \
  -v $(pwd)/chroma_db:/app/chroma_db \
  -v $(pwd)/uploads:/app/uploads \
  --env-file .env \
  multimodal-vox-agent
```

## ☁️ AWS Deployment

### Option 1: AWS ECS (Elastic Container Service)

1. **Build and push to ECR**
```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and tag
docker build -t multimodal-vox-agent .
docker tag multimodal-vox-agent:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/multimodal-vox-agent:latest

# Push to ECR
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/multimodal-vox-agent:latest
```

2. **Deploy using the provided CloudFormation template** (see `aws/ecs-deployment.yml`)

### Option 2: AWS EC2

1. **Launch EC2 instance** (t3.medium or larger)
2. **SSH into instance**
3. **Install Docker**
```bash
sudo yum update -y
sudo yum install -y docker
sudo service docker start
sudo usermod -a -G docker ec2-user
```

4. **Deploy application**
```bash
git clone <your-repo>
cd multimodal-vox-agent
docker-compose up -d
```

### Option 3: AWS App Runner

```bash
# Create App Runner service using the Dockerfile
aws apprunner create-service \
  --service-name multimodal-vox-agent \
  --source-configuration file://aws/apprunner-config.json
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_STUDIO_BASE_URL` | LM Studio API endpoint | `http://localhost:1234/v1` |
| `LLM_STUDIO_API_KEY` | API key for LLM | `lmstudio` |
| `LOCAL_LLM_MODEL` | Model name | `LiquidAI/LFM2.5-VL-1.6B-GGUF` |
| `EMBEDDING_MODEL` | Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| `VISION_MODEL` | Image captioning model | `Salesforce/blip-image-captioning-base` |
| `STT_MODEL` | Whisper model size | `base` |
| `TTS_MODEL` | Piper TTS voice | `en_US-lessac-medium` |
| `CHROMA_PERSIST_DIR` | Vector DB path | `./chroma_db` |
| `UPLOAD_DIR` | Upload directory | `./uploads` |
| `TEMP_DIR` | Temporary files | `./temp` |
| `API_BASE_URL` | FastAPI backend base URL | `http://localhost:8000` |
| `MAX_ITERATIONS` | Agent max iterations | `10` |

## 📦 Project Structure

```
multimodal-vox-agent/
├── agents/
│   └── multimodal_agent.py    # LangGraph agent
├── config/
│   ├── __init__.py
│   └── settings.py            # Configuration management
├── utils/
│   ├── audio_processor.py     # STT/TTS handling
│   ├── document_processor.py  # Document parsing
│   ├── llm_wrapper.py         # LLM interface
│   └── vector_store.py        # ChromaDB operations
├── aws/
│   ├── ecs-deployment.yml     # ECS CloudFormation
│   └── apprunner-config.json  # App Runner config
├── .github/
│   └── workflows/
│       └── ci-cd.yml          # CI/CD pipeline
├── app.py                     # Main Streamlit app
api.py                     # FastAPI backend
├── app_improved.py            # Enhanced version with better error handling
├── style.css                  # Custom styling
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container definition
├── docker-compose.yml         # Multi-container setup
├── .env.example              # Environment template
├── .gitignore                # Git ignore rules
└── README.md                 # Documentation
```

## 🔧 Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Quality

```bash
# Format code
black .
isort .

# Lint
flake8 .
pylint agents/ utils/ config/
```

## 🐛 Troubleshooting

### Common Issues

**1. LM Studio Connection Error**
- Ensure LM Studio is running
- Check `LLM_STUDIO_BASE_URL` in `.env`
- Verify model is loaded in LM Studio

**2. OCR Not Working**
- Install Tesseract: `sudo apt-get install tesseract-ocr` (Linux)
- On Windows: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
- On Mac: `brew install tesseract`

**3. Audio Processing Errors**
- Check Piper TTS installation
- Verify `PIPER_MODEL_PATH` is set correctly
- Ensure audio files are in supported formats

**4. Memory Issues**
- Reduce `CHUNK_SIZE` in config
- Use smaller embedding models
- Limit concurrent document processing

**5. Docker Container Won't Start**
- Check Docker logs: `docker-compose logs`
- Verify port 8501 isn't in use
- Ensure sufficient disk space

## 📊 Performance Optimization

1. **Use GPU acceleration** (if available)
   - Install CUDA-enabled PyTorch
   - Update Docker to use nvidia runtime

2. **Optimize embedding model**
   - Use quantized models for faster inference
   - Consider smaller models like `all-MiniLM-L6-v2`

3. **Database optimization**
   - Regular cleanup of old embeddings
   - Use appropriate chunk sizes
   - Index optimization for large collections

4. **Caching**
   - Enable Streamlit caching for expensive operations
   - Cache model loading
   - Store frequently accessed data in memory

## 🔒 Security Best Practices

1. **Never commit `.env` files**
2. **Use secrets management** (AWS Secrets Manager, HashiCorp Vault)
3. **Implement authentication** for production deployments
4. **Enable HTTPS** with proper SSL certificates
5. **Regular dependency updates** for security patches
6. **Input validation** and sanitization
7. **Rate limiting** to prevent abuse

## 📈 Monitoring & Logging

- Application logs: `app.log`
- Docker logs: `docker-compose logs -f`
- Health check endpoint: `http://localhost:8501/_stcore/health`

### Production Monitoring

- CloudWatch (AWS)
- Prometheus + Grafana
- Sentry for error tracking

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Authors

- Your Name - Initial work

## 🙏 Acknowledgments

- LangChain & LangGraph for agent framework
- Streamlit for the amazing UI framework
- HuggingFace for models and transformers
- ChromaDB for vector storage
- OpenAI for Whisper
- Piper TTS for voice synthesis

## 📞 Support

- Create an issue: [GitHub Issues](https://github.com/ruhul-cse-duet/Multimodal-AI-Agent-Qwen2-pdf-image-STT-TTS/issues)
- Email: ruhul.cse.duet@gmail.com
- Documentation: [Wiki](https://github.com/ruhul-cse-duet/Multimodal-AI-Agent-Qwen2-pdf-image-STT-TTS/wiki)

---

Made with ❤️ by [Ruhul Amin](https://www.linkedin.com/in/ruhul-duet-cse)
