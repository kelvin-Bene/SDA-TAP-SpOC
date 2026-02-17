# User Guides

This section contains practical guides for using the UCT Benchmark system.

## Available Guides

### Getting Started
- **[Installation & Setup](../getting-started.md)** - Complete setup instructions for all platforms

### Setup Guides
- **[Orekit Setup (Windows)](OREKIT_SETUP.md)** - Configure Java and Orekit for orbit propagation

### Usage Guides
- **[Dataset Generation](DATASET_GENERATION.md)** - How to generate benchmark datasets
- **[Running Evaluations](EVALUATION_GUIDE.md)** - Evaluate UCTP algorithm submissions
- **[Web UI Guide](UI_GUIDE.md)** - Using the web interface

## Quick Reference

### Starting the Application

```bash
# Backend API
cd UCT-Benchmark-DMR/combined
uvicorn backend_api.main:app --reload --port 8000

# Frontend
cd UCT-Benchmark-DMR/combined/frontend
npm run dev
```

### Common Tasks

| Task | Command/Action |
|------|----------------|
| Generate dataset | Web UI > Datasets > Generate |
| Download dataset | Web UI > Datasets > Download |
| Submit results | Web UI > Submit > Upload |
| View leaderboard | Web UI > Leaderboard |

### API Tokens

The system requires API tokens for data access:

| Service | Environment Variable | How to Get |
|---------|---------------------|------------|
| UDL | `UDL_TOKEN` | Contact data provider |
| Space-Track | `SPACETRACK_USER` / `SPACETRACK_PASS` | Register at space-track.org |
| ESA DiscoWeb | `ESA_TOKEN` | Register at ESA portal |

## Support

- Check the [Technical Reference](../technical/README.md) for detailed documentation
- Review [Issues Backlog](../reports/ISSUES_BACKLOG.md) for known issues
- See [Configuration](../technical/CONFIGURATION.md) for system settings

---

## Related Documentation

- [Technical Reference](../technical/README.md)
- [Project Status](../planning/PROJECT_STATUS.md)
