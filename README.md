# HireCharm Onboarding Form

Client onboarding form for collecting campaign requirements and context.

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    Docker Container                         │
│                                                             │
│   ┌─────────────┐         ┌─────────────────────┐          │
│   │   nginx     │────────▶│   FastAPI Backend   │          │
│   │  (port 80)  │         │    (port 8000)      │          │
│   └─────────────┘         └─────────────────────┘          │
│         │                           │                       │
│         │ /                         │ /onboarding/*         │
│         ▼                           ▼                       │
│   ┌─────────────┐         ┌─────────────────────┐          │
│   │ index.html  │         │  Supabase/Postgres  │          │
│   │   (form)    │         │     Database        │          │
│   └─────────────┘         └─────────────────────┘          │
└────────────────────────────────────────────────────────────┘
```

## Database Tables

| Table | Purpose |
|-------|---------|
| `clients` | Client records |
| `client_onboarding_submissions` | Form submissions (main data) |
| `client_segments` | Customer segments (1:N) |
| `client_personas` | Buyer personas (1:N) |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_HOST` | Database host | localhost |
| `POSTGRES_PORT` | Database port | 5432 |
| `POSTGRES_DB` | Database name | postgres |
| `POSTGRES_USER` | Database user | postgres |
| `POSTGRES_PASSWORD` | Database password | (required) |
| `DATABASE_URL` | Full connection string (alternative) | - |

## Deployment (Coolify)

1. Push to GitHub
2. Coolify will auto-build and deploy
3. Set environment variables in Coolify UI

## Local Development

```bash
# Run database migration first
psql -h $POSTGRES_HOST -d $POSTGRES_DB -f ../OwnRBL/database_migrations/020_client_onboarding_forms.sql

# Build and run
docker build -t hirecharm-onboarding .
docker run -p 80:80 \
  -e POSTGRES_HOST=host.docker.internal \
  -e POSTGRES_DB=your_db \
  -e POSTGRES_USER=your_user \
  -e POSTGRES_PASSWORD=your_password \
  hirecharm-onboarding
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serve onboarding form |
| `/health` | GET | Health check |
| `/onboarding/submit` | POST | Submit form |
| `/onboarding/{id}` | GET | Retrieve submission |

## Campaign Idea Generator Integration

The onboarding data feeds into the campaign idea generator workflow:

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Onboarding Form │────▶│    Database      │────▶│ Campaign Generator│
│    Submission    │     │   (Supabase)     │     │    (AI/LLM)       │
└──────────────────┘     └──────────────────┘     └──────────────────┘
                                │
                                ▼
                    vw_campaign_generation_context
                    (aggregated view for LLM prompts)
```

### Data Flow

1. Client submits onboarding form
2. Data stored in `client_onboarding_submissions`, `client_segments`, `client_personas`
3. Campaign generator queries `vw_campaign_generation_context` view
4. View returns all context needed for LLM prompt:
   - Company info
   - ICP/segments
   - Personas
   - Pain points
   - Messaging tone
   - Success criteria

### Using the Campaign Context View

```sql
-- Get campaign generation context for a client
SELECT * FROM vw_campaign_generation_context
WHERE client_id = 'your-client-uuid';

-- Returns: company_name, core_product, target_customer, acv,
--          sales_cycle_length, primary_gtm_objective, signals[],
--          job_titles[], customer_voice, roi_results, case_studies,
--          tone_style, success_definition, segments (JSONB), personas (JSONB)
```
