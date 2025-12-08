# Testing the Anomaly Detection UI

## Worktree Location

```
C:\Users\benja\Documents\code_projects\baselinr\baselinr-plan10-anomaly
```

Branch: `plan10-anomaly-detection-ui`

## Quick Start (Direct Method - Recommended)

Since the `baselinr ui` command may conflict with installed packages, test the UI directly:

### Option 1: Frontend Only (UI Testing)

**Terminal 1:**
```powershell
cd C:\Users\benja\Documents\code_projects\baselinr\baselinr-plan10-anomaly\dashboard\frontend
npm install  # First time only
npm run dev
```

Access at: **http://localhost:3000/config/anomaly**

*Note: Without backend, you can still test the UI but saving will show errors.*

### Option 2: Frontend + Backend (Full Functionality)

**Terminal 1 - Backend:**
```powershell
cd C:\Users\benja\Documents\code_projects\baselinr\baselinr-plan10-anomaly\dashboard\backend

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# If venv doesn't exist, create it:
# python -m venv venv
# .\venv\Scripts\Activate.ps1
# pip install -r requirements.txt

# Start backend
python main.py
```

Backend runs at: **http://localhost:8000**

**Terminal 2 - Frontend:**
```powershell
cd C:\Users\benja\Documents\code_projects\baselinr\baselinr-plan10-anomaly\dashboard\frontend
npm run dev
```

Frontend runs at: **http://localhost:3000**

## Environment Setup

The frontend `.env.local` file should contain:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

This should already be set, but if not, create it in `dashboard/frontend/.env.local`

## What to Test

1. **Navigate to Anomaly Detection**:
   - Click "Anomaly Detection" in sidebar
   - Or go to: http://localhost:3000/config/anomaly

2. **Expectation Learning Section**:
   - Toggle enable/disable
   - Adjust learning window slider (7-365 days)
   - Set min samples
   - Configure EWMA lambda parameter

3. **Anomaly Detection Section**:
   - Toggle enable/disable
   - Select/deselect detection methods
   - Click "Show settings" for each method
   - Adjust thresholds (IQR, MAD, EWMA)
   - Configure seasonality and regime shift settings

4. **Save Functionality**:
   - Click "Save Configuration"
   - Should show success message (if backend running)
   - Or error message if backend not available

## Troubleshooting

**Port conflicts:**
- Frontend default: 3000
- Backend default: 8000
- If ports are in use, Next.js will prompt for a different port

**Dependencies:**
- Each worktree has its own `node_modules` - install in this worktree if needed
- Backend uses its own virtual environment
