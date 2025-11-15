# ProfileMesh Dashboard - Quick Start Guide

Get the ProfileMesh Dashboard running in 5 minutes!

## Prerequisites Check

✅ Node.js 18+ installed (`node --version`)  
✅ Python 3.10+ installed (`python --version`)  
✅ PostgreSQL running with ProfileMesh database  
✅ ProfileMesh Phase 1 installed and configured

## Step-by-Step Setup

### 1. Backend Setup (Terminal 1)

```bash
# Navigate to backend
cd dashboard/backend

# Install Python dependencies
pip install -r requirements.txt

# Generate sample data (optional but recommended for testing)
python sample_data_generator.py

# Start the backend server
python main.py
```

✅ Backend running at: **http://localhost:8000**  
✅ API docs at: **http://localhost:8000/docs**

### 2. Frontend Setup (Terminal 2)

```bash
# Navigate to frontend (from project root)
cd dashboard/frontend

# Install Node dependencies
npm install

# Start the development server
npm run dev
```

✅ Dashboard running at: **http://localhost:3000**

## 3. Open the Dashboard

Visit **http://localhost:3000** in your browser.

You should see:
- Dashboard with KPIs
- Recent runs
- Drift alerts (if any)
- Navigation sidebar

## Troubleshooting

### "Connection refused" errors

**Problem**: Frontend can't connect to backend  
**Solution**: 
- Ensure backend is running on port 8000
- Check that `NEXT_PUBLIC_API_URL=http://localhost:8000` 

### No data showing

**Problem**: Dashboard is empty  
**Solution**:
```bash
# Generate sample data
cd dashboard/backend
python sample_data_generator.py
```

### Database connection errors

**Problem**: Backend can't connect to database  
**Solution**:
- Check PostgreSQL is running
- Verify connection string:
  ```bash
  export PROFILEMESH_DB_URL=postgresql://profilemesh:profilemesh@localhost:5433/profilemesh
  ```
- Test connection:
  ```bash
  psql "postgresql://profilemesh:profilemesh@localhost:5433/profilemesh"
  ```

## Configuration

### Backend Environment Variables

Create `dashboard/backend/.env`:
```env
PROFILEMESH_DB_URL=postgresql://profilemesh:profilemesh@localhost:5433/profilemesh
API_HOST=0.0.0.0
API_PORT=8000
```

### Frontend Environment Variables

Create `dashboard/frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Next Steps

1. **Run actual profiling**: Use ProfileMesh CLI to profile your data
   ```bash
   profilemesh profile --config examples/config.yml
   ```

2. **Explore features**:
   - Filter runs by warehouse, schema, table
   - View drift detection alerts
   - Drill down into table-level metrics
   - Export data as JSON

3. **Customize**: 
   - Modify colors in `frontend/tailwind.config.ts`
   - Add custom metrics in backend
   - Create new visualizations

## Production Deployment

### Backend
```bash
cd dashboard/backend
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend
```bash
cd dashboard/frontend
npm run build
npm start
```

## Need Help?

- Check the main [README.md](./README.md) for detailed docs
- Review API documentation at http://localhost:8000/docs
- Ensure ProfileMesh Phase 1 is properly configured

---

🎉 **Happy Profiling!**

