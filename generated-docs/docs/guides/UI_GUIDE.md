# Web UI Guide

This guide explains how to use the UCT Benchmark web interface for dataset management, algorithm submission, and results viewing.

## Accessing the Application

### Start the Services

```bash
# Terminal 1: Start backend
cd UCT-Benchmark-DMR/combined
uvicorn backend_api.main:app --reload --port 8000

# Terminal 2: Start frontend
cd UCT-Benchmark-DMR/combined/frontend
npm run dev
```

### Access the Interface

Open your browser to: http://localhost:5173

## Navigation Overview

```
┌─────────────────────────────────────────────────────────┐
│ UCT Benchmark                    [User] [Theme] [Logout]│
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────┐  ┌──────────┐  ┌────────┐  ┌───────────┐ │
│  │Dashboard│  │ Datasets │  │ Submit │  │Leaderboard│ │
│  └─────────┘  └──────────┘  └────────┘  └───────────┘ │
│                                                         │
│  Main Content Area                                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Dashboard

The dashboard provides an overview of your activity:

### Statistics Cards
- **Your Rank**: Current leaderboard position
- **Submissions**: Total submissions made
- **Datasets**: Number of datasets generated
- **Best F1 Score**: Highest F1 score achieved

### Recent Submissions
Shows your latest algorithm submissions with:
- Status (Queued, Processing, Completed, Failed)
- Dataset used
- Submission time
- Quick link to results

### Leaderboard Snapshot
Top 5 entries on the global leaderboard with medal indicators.

## Datasets Section

### Browse Datasets

Filter available datasets by:

| Filter | Options |
|--------|---------|
| Orbital Regime | LEO, MEO, GEO, HEO, All |
| Tier | T1, T2, T3, T4, All |
| Sensor Type | Optical, Radar, RF, All |
| Object Count | Range slider |

### Dataset Cards

Each dataset card shows:
- Name and code
- Orbital regime badge
- Tier badge
- Object count
- Observation count
- File size
- **Preview** and **Download** buttons

### Preview Dialog

Click **Preview** to see:
- Full dataset metadata
- Sample observations (first 10)
- Reference objects list
- Generation parameters

### Generate New Dataset

1. Click **Generate New Dataset**
2. Configure parameters:
   - **Orbital Regime**: LEO, MEO, GEO, or HEO
   - **Coverage Level**: High, Standard, or Low
   - **Object Count**: 10-100 satellites
   - **Time Window**: Start and end dates (max 90 days)
   - **Tier**: T1, T2, T3, or T4
3. Click **Generate**
4. Wait for processing (shown in job queue)
5. Download when complete

### My Datasets

View datasets you've generated:
- Generation status
- Download links
- Delete option

## Submit Section

### Upload Submission

1. Navigate to **Submit**
2. Fill in the form:
   - **Algorithm Name**: Your algorithm identifier
   - **Version**: Version string (e.g., "1.0.0")
   - **Dataset**: Select from available datasets
   - **Result File**: Upload JSON output
   - **Description**: Optional notes
3. Click **Submit for Evaluation**

### Submission Format

Your JSON file must follow the required format:

```json
[
  {
    "idStateVector": 0,
    "sourcedData": ["obs-1", "obs-2"],
    "epoch": "2026-01-15T12:00:00.000000",
    "xpos": -7365.971,
    "ypos": -1331.400,
    "zpos": 1514.249,
    "xvel": 1.977,
    "yvel": -5.225,
    "zvel": 4.473,
    "referenceFrame": "J2000"
  }
]
```

### My Submissions

View all your submissions:

| Status | Description |
|--------|-------------|
| Queued | Waiting in evaluation queue |
| Validating | Format validation in progress |
| Processing | Evaluation running |
| Completed | Results available |
| Failed | Error during evaluation |

Click a submission to view detailed results.

## Results Page

### Overview Tab

- **Binary Metrics**: Precision, Recall, F1 Score
- **State Metrics**: Position and velocity errors
- **Comparison**: Your result vs. best submission

### Satellite Breakdown

Table showing per-satellite results:
- Satellite ID
- Status (TP, FP, FN)
- Observations used
- Position error
- Confidence score

### Visualizations

- **Confusion Matrix**: TP/FP/FN breakdown
- **Error Distribution**: Position error histogram
- **Timeline**: Observations over time

### Export Options

Download results in:
- **PDF**: Formatted report
- **JSON**: Raw metrics data
- **CSV**: Tabular data

## Leaderboard

### Filters

- **Orbital Regime**: LEO, MEO, GEO, HEO, All
- **Tier**: T1, T2, T3, T4, All
- **Time Period**: All time, This month, This week

### Ranking Table

| Column | Description |
|--------|-------------|
| Rank | Position (with medal for top 3) |
| Algorithm | Algorithm name |
| Team | Team/user name |
| Version | Algorithm version |
| F1 Score | Primary ranking metric |
| Precision | Precision score |
| Recall | Recall score |
| Position RMS | State accuracy |
| Submitted | Submission date |

### Your Position

Your entries are highlighted for easy identification.

## Settings

### Profile

- Update display name
- Change email
- Manage API tokens

### Preferences

- **Theme**: Light, Dark, System
- **Notifications**: Email alerts for evaluation completion
- **Default Filters**: Set preferred dataset filters

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` | Search |
| `D` | Go to Dashboard |
| `G` | Go to Datasets |
| `S` | Go to Submit |
| `L` | Go to Leaderboard |
| `?` | Show help |

## Troubleshooting

### Page Not Loading

1. Check backend is running (`uvicorn backend_api.main:app`)
2. Check frontend is running (`npm run dev`)
3. Clear browser cache

### Upload Fails

1. Verify JSON format is correct
2. Check file size (max 50MB)
3. Ensure all required fields are present

### Evaluation Stuck

1. Check job queue status
2. Verify backend logs for errors
3. Re-submit if necessary

---

## Related Documentation

- [Getting Started](../getting-started.md)
- [Dataset Generation](DATASET_GENERATION.md)
- [Evaluation Guide](EVALUATION_GUIDE.md)
- [Backend API](../technical/BACKEND_API.md)
