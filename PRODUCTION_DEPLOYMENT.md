# Production Deployment Guide: Knowledge Base Update

## 🚨 **IMPORTANT: This is a MAJOR UPDATE**
This update adds:
- Knowledge Base system with PDF upload
- ChromaDB vector database 
- New API endpoints
- Database schema changes
- New dependencies

## 📋 **Pre-Deployment Checklist**

### 🌍 **Environment Variables Required**
```bash
# Existing variables
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database
SQLALCHEMY_DATABASE_URL=postgresql+asyncpg://user:password@host:port/database

# NEW REQUIRED VARIABLES
OPENAI_API_KEY=your_openai_api_key_here

# Bot tokens (set as needed)
BOT_TOKEN=your_telegram_bot_token_here
```

### 📁 **Persistent Storage Requirements**
```bash
# Create these directories on the server with proper permissions:
mkdir -p /app/db/chroma_db         # ChromaDB vector storage
mkdir -p /app/knowledge_bases      # PDF file uploads
mkdir -p /app/temp_bots           # Generated bot files

# Set proper permissions
chown -R appuser:appuser /app/db
chown -R appuser:appuser /app/knowledge_bases  
chown -R appuser:appuser /app/temp_bots
```

### 🐳 **Docker Volume Mounts**
Update your docker-compose.yml or deployment config:
```yaml
volumes:
  - ./db:/app/db                          # ChromaDB persistence
  - ./knowledge_bases:/app/knowledge_bases # PDF uploads  
  - ./temp_bots:/app/temp_bots             # Bot files
```

## 🗄️ **Database Migration Steps**

### Step 1: Backup Current Database
```bash
pg_dump your_database_name > backup_before_migration.sql
```

### Step 2: Run Alembic Migration
```bash
# Inside the container or server:
cd /app
alembic upgrade head
```

### Step 3: Verify Migration
```bash
# Check that new columns exist:
psql -d your_database -c "SELECT column_name FROM information_schema.columns WHERE table_name='bots';"
# Should show: bot_type, knowledge_base_status
```

## 🚀 **Deployment Process**

### Option A: Docker Compose Deployment
```bash
# 1. Stop current services
docker-compose down

# 2. Pull latest code
git pull origin main

# 3. Build new image  
docker-compose build

# 4. Start services
docker-compose up -d

# 5. Run migration
docker-compose exec api alembic upgrade head

# 6. Check health
curl http://your-server/health/database
```

### Option B: Manual Server Deployment
```bash
# 1. Stop current service
systemctl stop your-api-service

# 2. Pull latest code
cd /path/to/your/app
git pull origin main

# 3. Install new dependencies
pip install -r requirements.txt

# 4. Run migration
alembic upgrade head

# 5. Start service
systemctl start your-api-service

# 6. Check health
curl http://your-server/health/database
```

## 🧪 **Post-Deployment Testing**

### Test Existing Functionality
```bash
# 1. Test existing simple chat bot creation
curl -X POST "http://your-server/bots/" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Simple Bot", "type": "simple_chat", "requirements": "Simple chat bot"}'

# 2. Test bot generation and deployment (use your auth token)
curl -X POST "http://your-server/ai/bots/{bot_id}/generate" \
  -H "Authorization: Bearer your-token"
```

### Test New Knowledge Base Features
```bash
# 1. Create Q&A bot
curl -X POST "http://your-server/bots/" \
  -H "Content-Type: application/json" \
  -d '{"name": "Q&A Bot", "type": "qa_knowledge_base", "requirements": "Bot to answer questions"}'

# 2. Upload PDF (replace with actual file)
curl -X POST "http://your-server/ai/bots/{bot_id}/knowledge/upload" \
  -H "Authorization: Bearer your-token" \
  -F "file=@test.pdf"

# 3. Check processing status
curl "http://your-server/ai/bots/{bot_id}/knowledge/status" \
  -H "Authorization: Bearer your-token"
```

## 🔧 **Troubleshooting**

### Common Issues:

#### 1. ChromaDB Permission Issues
```bash
# Fix permissions:
chown -R your-app-user:your-app-user /app/db/chroma_db
chmod -R 755 /app/db/chroma_db
```

#### 2. OpenAI API Key Missing
```bash
# Verify environment variable:
echo $OPENAI_API_KEY
# Should show your API key
```

#### 3. Migration Fails
```bash
# Check current migration status:
alembic current

# Check migration history:
alembic history

# If needed, mark current state (DANGEROUS - only if you know the schema is correct):
alembic stamp head
```

#### 4. PDF Upload Fails
```bash
# Check directory exists and permissions:
ls -la /app/knowledge_bases/
# Should be writable by your app user
```

### Monitoring Commands:
```bash
# Check ChromaDB collections:
# (Run inside Python shell in container)
import chromadb
client = chromadb.PersistentClient(path="/app/db/chroma_db")
print(client.list_collections())

# Check background tasks (if using systemd):
journalctl -u your-api-service -f

# Check API logs:
docker-compose logs -f api  # or equivalent
```

## 🔙 **Rollback Plan**

If something goes wrong:

### 1. Restore Database
```bash
# Stop API
systemctl stop your-api-service

# Restore database
psql your_database < backup_before_migration.sql

# Revert to previous version
git checkout previous-stable-commit
docker-compose up -d  # or restart service
```

### 2. Remove New Files
```bash
# Clean up new directories if needed:
rm -rf /app/db/chroma_db/*
rm -rf /app/knowledge_bases/*
```

## ✅ **Success Criteria**

Deployment is successful when:
- [ ] Database migration completed without errors
- [ ] Existing simple chat bots still work
- [ ] New Q&A bot creation works
- [ ] PDF upload functionality works
- [ ] Knowledge base processing completes
- [ ] Generated Q&A bots can answer questions
- [ ] All API endpoints return expected responses
- [ ] No "Ошибка обработки" errors in bot responses

## 📞 **Need Help?**

If you encounter issues:
1. Check the troubleshooting section above
2. Review application logs
3. Verify all environment variables are set
4. Test individual components step by step

---
**Last Updated:** $(date)
**Version:** Knowledge Base v1.0 