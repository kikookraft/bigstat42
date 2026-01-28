# Quick Start Guide

## 1. Try the Demo First

No API credentials needed! See what bigstat42 can do:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the demo
python demo.py
```

This generates sample data and creates visualizations in `demo_output/`.

## 2. Get Your 42 API Credentials

1. Go to https://profile.intra.42.fr/oauth/applications
2. Click "New Application"
3. Fill in the form:
   - **Name**: bigstat42 (or any name you prefer)
   - **Redirect URI**: urn:ietf:wg:oauth:2.0:oob (for command-line apps)
   - **Scopes**: public
4. Click "Submit"
5. Copy your **UID** and **SECRET**

## 3. Configure Your Credentials

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your credentials
# API_UID=your_uid_here
# API_SECRET=your_secret_here
# CAMPUS_ID=1
```
Activate a virtual environment and install dependencies:
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```


## 4. Run Your First Analysis

```bash
# Analyze the last 7 days (default)
python run.py

# Or analyze more days
python run.py --days 30

# Or specify a different campus
python run.py --campus 9 --days 14
```

## 5. Check Your Results

Results are saved in the `output/` directory:

- **Heatmaps**: Visual representation of usage patterns
- **Charts**: Hourly and daily usage distributions
- **Summary**: Text file with key statistics

## Common Campus IDs

- 1 = Paris
- 9 = Fremont (Silicon Valley)
- 14 = Madrid
- 21 = São Paulo

To find other campus IDs, check the 42 API documentation: https://api.intra.42.fr/apidoc

## Troubleshooting

### "No location data found"
- Check your API credentials have the correct permissions
- Verify the campus ID is correct
- Make sure there's recent activity for the time period

### "API_UID and API_SECRET must be provided"
- Make sure you created the `.env` file
- Check that the credentials are correctly set in `.env`
- Or provide credentials with `--uid` and `--secret` flags

### Import errors
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Or install the package: `pip install -e .`

## Advanced Usage

### Install as a command
```bash
pip install -e .
bigstat42 --help
```

### Custom output directory
```bash
python run.py --days 30 --output my_analysis
```

### Use command-line credentials
```bash
python run.py --uid YOUR_UID --secret YOUR_SECRET --days 7
```

## What Gets Generated

### Visualizations
1. **usage_heatmap_day_hour.png** - Shows when the cluster is busiest (day × hour)
2. **usage_heatmap_hosts_hour.png** - Shows which computers are most used and when
3. **hourly_usage.png** - Bar chart of sessions by hour
4. **daily_usage.png** - Bar chart of sessions by day of week
5. **top_hosts.png** - Most frequently used computers

### Statistics
- Total number of sessions
- Unique users and computers
- Average session duration
- Total usage time
- Date range analyzed

All data is saved to text in `summary.txt`.

## Need Help?

- 42 API Documentation: https://api.intra.42.fr/apidoc
- Create an issue on GitHub
- Check the README.md for detailed information
