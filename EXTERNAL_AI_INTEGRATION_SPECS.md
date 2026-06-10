# External AI Chat System Integration Specifications

## Overview

This document provides complete specifications for integrating an external AI chat system with the Case Manager Suite 2.0. The system supports GPT-4-powered AI assistance for case management, resource discovery, and client support.

**Last Updated**: 2026-05-26
**Version**: 2.0.0
**Base URL**: `http://localhost:8000` (development) or your production domain

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
4. [Data Models](#data-models)
5. [AI Capabilities](#ai-capabilities)
6. [Tool Functions](#tool-functions)
7. [Database Schema](#database-schema)
8. [Integration Examples](#integration-examples)
9. [Error Handling](#error-handling)
10. [Rate Limiting & Performance](#rate-limiting--performance)

---

## Architecture Overview

### System Components

```
External AI Client
       ↓
   [HTTP/JSON]
       ↓
FastAPI Backend (/api/ai/*)
       ↓
UnifiedAIService (unified_service.py)
       ↓
    ┌──────────────┬───────────────┬──────────────┐
    ↓              ↓               ↓              ↓
OpenAI GPT-4   SQLite Memory   Virgil DB    Knowledge Files
(gpt-4o-mini)  (ai_assistant.db) (resources)  (enrichment)
```

### Key Features

- **Persistent Conversation Memory**: SQLite-based conversation storage per case manager
- **Resource Discovery**: Enhanced Virgil DB with 4,000+ providers + knowledge enrichment
- **Multi-Database Access**: 9 specialized databases (clients, benefits, housing, jobs, etc.)
- **Tool Functions**: 12+ specialized tools for data operations
- **Knowledge Enrichment**: Detailed provider info from curated knowledge files
- **Crisis Detection**: Automatic detection and prioritization of urgent needs

---

## Authentication

### Headers Required

```http
Content-Type: application/json
```

**Note**: The current system does not require authentication tokens for AI endpoints, but you can add middleware-based auth if needed.

### Optional User Context

```json
{
  "case_manager_id": "cm_12345"  // Identifies the case manager/user
}
```

---

## API Endpoints

### 1. Primary Chat Endpoint

**POST** `/api/ai/chat`

Full-featured AI assistant with read/write access to all databases and tool execution.

#### Request Body

```json
{
  "message": "I need a 7 day detox for a client in Los Angeles",
  "case_manager_id": "cm_12345"  // Optional, defaults to "default_cm"
}
```

#### Response

```json
{
  "response": "I found several detox centers in Los Angeles that can provide 7-day programs:\n\n1. **Muse Treatment Center** (Sherman Oaks)\n   - Services: Medical detox, residential treatment\n   - Insurance: Medi-Cal, private insurance\n   - Phone: (310) 555-1234\n   - Website: https://musetreatment.com\n\n2. **Milton Recovery Centers** (Los Angeles)\n   - Services: Short-term detox, residential transition\n   - Insurance: Medi-Cal, Medicare, private\n   - Phone: (213) 555-5678\n\nWould you like me to add any of these to your client's case notes?",
  "conversationId": "conv_cm_12345_1748342567",
  "toolCalls": [
    {
      "name": "search_internal_resources",
      "arguments": {
        "query": "detox center 7 day program",
        "location": "Los Angeles, CA",
        "limit": 5
      },
      "result": {
        "services": [
          {
            "provider_name": "Muse Treatment Center",
            "service_type": "treatment",
            "service_subtypes": ["detox", "residential"],
            "city": "Sherman Oaks",
            "phone": "(310) 555-1234",
            "insurance_accepted": ["medi_cal", "private"],
            "enriched": true,
            "enrichment_source": "suboxone_clinics.txt"
          }
        ]
      }
    }
  ],
  "metadata": {
    "model": "gpt-4o-mini",
    "tokensUsed": 1234,
    "responseTime": 2.3,
    "caseManagerId": "cm_12345"
  }
}
```

---

### 2. Assistant Chat Endpoint (Read-Only)

**POST** `/api/ai/assistant`

Read-only assistant for popup UI with search capabilities but no database writes.

#### Request Body

```json
{
  "message": "Find food banks near Hollywood",
  "case_manager_id": "cm_12345"
}
```

#### Response

Same structure as `/api/ai/chat` but tool calls are limited to read-only operations.

---

### 3. Get Conversation History

**GET** `/api/ai/conversation/{case_manager_id}`

Retrieve conversation history for a specific case manager.

#### Example

```http
GET /api/ai/conversation/cm_12345
```

#### Response

```json
{
  "case_manager_id": "cm_12345",
  "messages": [
    {
      "id": 1,
      "role": "user",
      "content": "Find detox centers in LA",
      "timestamp": "2026-05-26T10:30:00Z"
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "I found 5 detox centers in Los Angeles...",
      "timestamp": "2026-05-26T10:30:03Z",
      "toolCalls": [...]
    }
  ],
  "totalMessages": 24,
  "lastActivity": "2026-05-26T14:22:00Z"
}
```

---

## Data Models

### ChatRequest

```typescript
interface ChatRequest {
  message: string;              // Required: User's message
  case_manager_id?: string;     // Optional: Defaults to "default_cm"
}
```

### ChatResponse

```typescript
interface ChatResponse {
  response: string;                    // AI-generated response
  conversationId: string;              // Unique conversation identifier
  toolCalls?: ToolCall[];              // Functions executed during this turn
  metadata: {
    model: string;                     // AI model used (e.g., "gpt-4o-mini")
    tokensUsed: number;                // Total tokens consumed
    responseTime: number;              // Response time in seconds
    caseManagerId: string;             // Case manager ID
    mode?: "central" | "assistant";    // Endpoint mode
  };
}
```

### ToolCall

```typescript
interface ToolCall {
  name: string;                  // Tool function name
  arguments: Record<string, any>; // Arguments passed to tool
  result: any;                   // Tool execution result
  executionTime?: number;        // Time taken to execute (ms)
}
```

---

## AI Capabilities

### 1. Resource Discovery

The AI can search and recommend:

- **Treatment Centers**: Detox, residential, outpatient, MAT, sober living
- **Medical Providers**: Primary care, urgent care, mental health, dental
- **Housing**: Emergency shelter, transitional, permanent supportive housing
- **Food Resources**: Food banks, meal programs, pantries
- **Legal Services**: Expungement, court support, legal aid
- **Benefits**: CalFresh, Medi-Cal, General Relief, SSI/SSDI
- **Employment**: Background-friendly jobs, resume assistance

**Example Query**: "Find MAT providers accepting Medi-Cal in North Hollywood"

**AI Response**: Returns enriched providers with payment details, services, insurance accepted, and contact info.

---

### 2. Client Management

The AI can:

- Retrieve client profiles and case history
- Update client notes and status
- Track tasks and reminders
- Assess urgency and risk factors
- Generate case summaries

**Example Query**: "Show me John Doe's recent housing applications"

---

### 3. Benefits Screening

The AI can:

- Assess benefit eligibility (CalFresh, Medi-Cal, etc.)
- Calculate household income thresholds
- Recommend programs based on client profile
- Track benefit application status

**Example Query**: "Is my client eligible for CalFresh with $1,800/month income?"

---

### 4. Job Matching

The AI can:

- Find background-friendly jobs
- Generate tailored resumes
- Match skills to opportunities
- Track application status

**Example Query**: "Find warehouse jobs for client with felony conviction"

---

## Tool Functions

The AI has access to these tools (automatically called as needed):

### 1. `search_internal_resources`

**Description**: PRIMARY TOOL for searching local verified providers (treatment, medical, housing, food, etc.)

**Parameters**:
```json
{
  "query": "detox center with Medi-Cal",
  "location": "Los Angeles, CA",
  "limit": 8
}
```

**Returns**:
```json
{
  "services": [
    {
      "provider_name": "Muse Treatment",
      "service_type": "treatment",
      "service_subtypes": ["detox", "residential"],
      "phone": "(310) 555-1234",
      "address": "123 Main St, Sherman Oaks, CA 91403",
      "city": "Sherman Oaks",
      "insurance_accepted": ["medi_cal", "private"],
      "website": "https://musetreatment.com",
      "location_score": 0.95,
      "enriched": true,
      "payment_details": "Accepts Medi-Cal, Medicare, most private insurance",
      "services_details": "Medical detox (3-7 days), residential (30-90 days), dual diagnosis",
      "provider_notes": "Specialized in co-occurring disorders, evidence-based treatment"
    }
  ],
  "totalResults": 12,
  "searchLocation": "Los Angeles, CA"
}
```

---

### 2. `search_web_resources`

**Description**: Fallback for web searches when internal database has no results

**Parameters**:
```json
{
  "query": "free dental clinic Pasadena",
  "location": "Pasadena, CA"
}
```

---

### 3. `get_client_profile`

**Description**: Retrieve full client profile with case history

**Parameters**:
```json
{
  "client_id": "12345"
}
```

**Returns**:
```json
{
  "client": {
    "id": "12345",
    "name": "John Doe",
    "dob": "1985-03-15",
    "phone": "(213) 555-1234",
    "email": "john.doe@example.com",
    "status": "active",
    "risk_level": "medium",
    "assigned_case_manager": "cm_12345",
    "barriers": ["housing", "substance_use", "employment"],
    "insurance": ["medi_cal"],
    "notes": "Recent intake, needs detox and housing placement",
    "created_at": "2026-05-01",
    "last_contact": "2026-05-25"
  }
}
```

---

### 4. `update_client_notes`

**Description**: Add notes to client record

**Parameters**:
```json
{
  "client_id": "12345",
  "note": "Called Muse Treatment, intake scheduled for 5/27 at 9am",
  "category": "service_referral"
}
```

---

### 5. `search_jobs`

**Description**: Search background-friendly job opportunities

**Parameters**:
```json
{
  "query": "warehouse",
  "location": "Los Angeles, CA",
  "background_friendly": true,
  "limit": 10
}
```

---

### 6. `assess_benefits_eligibility`

**Description**: Determine benefit program eligibility

**Parameters**:
```json
{
  "client_id": "12345",
  "programs": ["calfresh", "medi_cal", "general_relief"]
}
```

**Returns**:
```json
{
  "eligibility": {
    "calfresh": {
      "eligible": true,
      "estimated_benefit": "$281/month",
      "household_size": 1,
      "income_threshold": "$2,266/month",
      "reasoning": "Client income ($1,200/mo) is below threshold"
    },
    "medi_cal": {
      "eligible": true,
      "coverage_type": "full_scope",
      "reasoning": "Income below 138% FPL"
    }
  }
}
```

---

### 7. `create_smart_task`

**Description**: Create intelligent task with auto-prioritization

**Parameters**:
```json
{
  "client_id": "12345",
  "task": "Follow up on Muse Treatment intake",
  "due_date": "2026-05-27",
  "priority": "high"
}
```

---

### 8. `get_dashboard_stats`

**Description**: Retrieve case management dashboard statistics

**Returns**:
```json
{
  "total_clients": 147,
  "active_clients": 89,
  "pending_tasks": 34,
  "urgent_tasks": 7,
  "recent_placements": 12,
  "housing_search_active": 23
}
```

---

### 9. `search_housing_listings`

**Description**: Search available housing (emergency, transitional, permanent)

**Parameters**:
```json
{
  "city": "Los Angeles",
  "housing_type": "emergency",
  "accepts_pets": false,
  "wheelchair_accessible": false
}
```

---

### 10. `generate_resume`

**Description**: Create tailored resume for client

**Parameters**:
```json
{
  "client_id": "12345",
  "job_description": "Warehouse Associate - forklift certified, lifting 50lbs"
}
```

---

### 11. `check_expungement_eligibility`

**Description**: Assess criminal record expungement eligibility

**Parameters**:
```json
{
  "client_id": "12345"
}
```

---

### 12. `get_documentation_templates`

**Description**: Retrieve case documentation templates

**Parameters**:
```json
{
  "template_type": "intake_assessment"
}
```

---

## Database Schema

### Conversation Memory (ai_assistant.db)

```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_manager_id TEXT NOT NULL,
    role TEXT NOT NULL,  -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    function_calls TEXT,  -- JSON array of tool calls
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT  -- JSON metadata
);

CREATE INDEX idx_cm_timestamp ON conversations(case_manager_id, timestamp DESC);
```

### Client Database (core_clients.db)

```sql
CREATE TABLE clients (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    dob DATE,
    phone TEXT,
    email TEXT,
    status TEXT DEFAULT 'active',
    risk_level TEXT,
    assigned_case_manager TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE client_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT NOT NULL,
    note TEXT NOT NULL,
    category TEXT,
    created_by TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(id)
);
```

### Virgil DB (virgil_st_dev.db)

Four main tables:

1. **resources** - Food banks, shelters, services (1,200+ entries)
2. **treatment_centers** - Detox, rehab, sober living (300+ entries)
3. **medi_cal_providers** - Medical providers (2,500+ entries)
4. **meetings** - AA/NA meetings (500+ entries)

---

## Integration Examples

### Example 1: Simple Chat Integration (JavaScript)

```javascript
const chatWithAI = async (message, caseManagerId = 'cm_12345') => {
  const response = await fetch('http://localhost:8000/api/ai/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message: message,
      case_manager_id: caseManagerId
    })
  });

  const data = await response.json();

  console.log('AI Response:', data.response);
  console.log('Tools Used:', data.toolCalls?.length || 0);

  return data;
};

// Usage
await chatWithAI('Find detox centers in North Hollywood with Medi-Cal');
```

---

### Example 2: Python Integration

```python
import requests
import json

class CMSAIClient:
    def __init__(self, base_url='http://localhost:8000'):
        self.base_url = base_url
        self.case_manager_id = 'cm_12345'

    def chat(self, message):
        """Send message to AI chat endpoint"""
        response = requests.post(
            f'{self.base_url}/api/ai/chat',
            json={
                'message': message,
                'case_manager_id': self.case_manager_id
            }
        )
        response.raise_for_status()
        return response.json()

    def get_conversation_history(self):
        """Retrieve conversation history"""
        response = requests.get(
            f'{self.base_url}/api/ai/conversation/{self.case_manager_id}'
        )
        response.raise_for_status()
        return response.json()

# Usage
client = CMSAIClient()

# Send message
result = client.chat('Find MAT providers in Los Angeles')
print(f"AI: {result['response']}")

# View tool calls
if result.get('toolCalls'):
    for tool in result['toolCalls']:
        print(f"Tool: {tool['name']}")
        print(f"Args: {tool['arguments']}")
```

---

### Example 3: React Integration

```typescript
import { useState } from 'react';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export const useAIChat = (caseManagerId: string) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);

  const sendMessage = async (message: string) => {
    setLoading(true);

    // Add user message
    setMessages(prev => [...prev, {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    }]);

    try {
      const response = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          case_manager_id: caseManagerId
        })
      });

      const data = await response.json();

      // Add AI response
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString()
      }]);

      return data;
    } catch (error) {
      console.error('Chat error:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  return { messages, sendMessage, loading };
};
```

---

## Error Handling

### Standard Error Response

```json
{
  "error": {
    "code": "AI_SERVICE_ERROR",
    "message": "Failed to generate AI response",
    "details": "OpenAI API timeout after 30 seconds",
    "timestamp": "2026-05-26T14:22:00Z",
    "requestId": "req_abc123"
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Missing required fields or invalid format |
| `CASE_MANAGER_NOT_FOUND` | 404 | Case manager ID not found |
| `AI_SERVICE_ERROR` | 500 | OpenAI API error or timeout |
| `DATABASE_ERROR` | 500 | Database connection or query error |
| `TOOL_EXECUTION_ERROR` | 500 | Tool function execution failed |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |

### Retry Strategy

```javascript
const chatWithRetry = async (message, maxRetries = 3) => {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await chatWithAI(message);
    } catch (error) {
      if (i === maxRetries - 1) throw error;

      // Exponential backoff
      const delay = Math.pow(2, i) * 1000;
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
};
```

---

## Rate Limiting & Performance

### Current Limits

- **No rate limiting** currently enforced (add as needed)
- **Request timeout**: 60 seconds
- **OpenAI timeout**: 30 seconds per API call
- **Max conversation history**: Last 50 messages per case manager

### Performance Benchmarks

| Operation | Avg Response Time |
|-----------|-------------------|
| Simple chat (no tools) | 1.2s |
| Resource search | 2.5s |
| Client profile retrieval | 0.8s |
| Benefits eligibility | 1.5s |
| Resume generation | 3.2s |

### Optimization Tips

1. **Use assistant endpoint** for read-only queries (faster)
2. **Batch operations** when possible
3. **Cache conversation history** on client side
4. **Limit conversation context** to last 20 messages for performance

---

## Advanced Features

### 1. Knowledge Enrichment

Providers are automatically enriched with curated knowledge files:

```json
{
  "provider_name": "JWCH Institute",
  "enriched": true,
  "enrichment_source": "suboxone_clinics.txt",
  "payment_details": "Medi-Cal, Medicare, sliding scale for uninsured",
  "services_details": "MAT (Suboxone, Vivitrol), primary care, behavioral health",
  "provider_notes": "Serving Skid Row and Downtown LA, walk-ins welcome"
}
```

### 2. Crisis Detection

AI automatically detects crisis terms and prioritizes urgent needs:

```javascript
const crisisTerms = [
  'homeless', 'street', 'kicked out', 'sleeping outside',
  'detox', 'overdose', 'withdrawal', 'emergency'
];
```

When detected, AI:
- Prioritizes emergency resources
- Flags conversation for case manager review
- Suggests immediate actions

### 3. Location Intelligence

Smart location scoring based on:
- City/neighborhood matching
- ZIP code proximity
- Transit accessibility
- Provider capacity

---

## Testing

### Sample Test Queries

```javascript
const testQueries = [
  // Resource discovery
  "Find detox centers in Los Angeles accepting Medi-Cal",
  "I need emergency shelter tonight in North Hollywood",
  "MAT providers near Van Nuys with Suboxone",

  // Client management
  "Show me John Doe's case notes",
  "Add note: Client completed intake assessment",

  // Benefits
  "Is my client eligible for CalFresh with $1500 monthly income?",
  "What benefits can a family of 3 get?",

  // Jobs
  "Find warehouse jobs for client with felony record",
  "Generate resume for construction worker position"
];
```

### Health Check

```http
GET /api/health

Response:
{
  "status": "healthy",
  "timestamp": "2026-05-26T14:22:00Z",
  "modules": {
    "ai_unified": "loaded",
    "virgil_db": "connected",
    "openai": "available"
  },
  "database_stats": {
    "resources": 1247,
    "treatment_centers": 312,
    "medi_cal_providers": 2583,
    "meetings": 547
  }
}
```

---

## Support & Documentation

### Additional Resources

- **API Documentation**: `/docs` (FastAPI auto-generated)
- **Interactive API**: `/redoc` (ReDoc UI)
- **Knowledge Files**: `knowledge files/` directory
- **Database Schemas**: `databases/` directory

### Contact

For integration support or questions, contact the development team.

---

## Version History

- **2.0.0** (2026-05-26): Complete system with Phase 1-3 enhancements
  - Enhanced Virgil DB multi-table search
  - Knowledge enrichment layer (64+ providers)
  - Unified AI with GPT-4o-mini
  - 12+ tool functions
  - 9-database architecture

---

**End of Specifications**
