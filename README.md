# bigstat42

Get comprehensive statistics and visualizations from 42 school cluster usage data.

## Features

- 📊 **Fetch data from 42 API** - Retrieve location logs and user activity
- 🔥 **Heatmaps** - Visual representation of cluster usage patterns
  - Day of week vs Hour of day heatmap
  - Top computers vs Hour of day heatmap
- 📈 **Statistics** - Comprehensive usage analytics
  - Hourly usage patterns
  - Daily usage patterns (by day of week)
  - Weekly and monthly trends
  - Average session duration per computer
  - Total usage time and sessions
- 🎯 **Flexible Analysis** - Analyze data for any time period (days, weeks, months)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/kikookraft/bigstat42.git
cd bigstat42
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your API credentials:
   - Copy `.env.example` to `.env`
   - Get your API credentials from https://profile.intra.42.fr/oauth/applications
   - Edit `.env` and add your credentials:
```bash
API_UID=your_api_uid_here
API_SECRET=your_api_secret_here
CAMPUS_ID=1
```

## Usage

### Basic Usage

Analyze the last 7 days of cluster usage:
```bash
python run.py
```

Or using the module directly:
```bash
python -m bigstat42.main
```

### Command Line Options

```bash
python run.py --campus CAMPUS_ID --days DAYS --output OUTPUT_DIR
```

**Options:**
- `--campus`: Campus ID (default: 1 for Paris)
- `--days`: Number of days to analyze (default: 7)
- `--output`: Output directory for visualizations (default: output)
- `--uid`: API UID (optional, overrides .env)
- `--secret`: API Secret (optional, overrides .env)

### Examples

Analyze the last 30 days:
```bash
python run.py --days 30
```

Analyze a specific campus for the last 14 days:
```bash
python run.py --campus 9 --days 14
```

Save results to a custom directory:
```bash
python run.py --days 7 --output my_statistics
```

Use custom API credentials:
```bash
python run.py --uid YOUR_UID --secret YOUR_SECRET --days 7
```

## Output

The application generates the following files in the output directory:

### Visualizations
- `usage_heatmap_day_hour.png` - Heatmap showing usage patterns by day of week and hour
- `usage_heatmap_hosts_hour.png` - Heatmap showing top 20 most used computers by hour
- `hourly_usage.png` - Bar chart of usage by hour of day
- `daily_usage.png` - Bar chart of usage by day of week
- `top_hosts.png` - Top 20 most used computers

### Reports
- `summary.txt` - Text summary with key statistics

## API Information

This application uses the 42 API v2. You need to create an application on your 42 profile to get API credentials:

1. Go to https://profile.intra.42.fr/oauth/applications
2. Create a new application
3. Copy the UID and SECRET
4. Add them to your `.env` file

**API Permissions**: Make sure your API application has the necessary permissions to read location data.

## Requirements

- Python 3.7+
- requests
- pandas
- numpy
- matplotlib
- seaborn
- python-dotenv

All dependencies are listed in `requirements.txt`.

## Project Structure

```
bigstat42/
├── bigstat42/
│   ├── __init__.py       # Package initialization
│   ├── api_client.py     # 42 API client
│   ├── analyzer.py       # Data analysis and statistics
│   ├── visualizer.py     # Visualization generation
│   └── main.py           # Main application
├── run.py                # Entry point script
├── requirements.txt      # Python dependencies
├── .env.example          # Example configuration
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## Statistics Generated

The application provides the following statistics:

- **Total Sessions**: Number of login sessions
- **Unique Users**: Number of different users
- **Unique Hosts**: Number of different computers used
- **Average Session Duration**: Average time spent per session
- **Total Usage Time**: Cumulative usage time
- **Hourly Distribution**: Usage patterns throughout the day
- **Daily Distribution**: Usage patterns throughout the week
- **Weekly Trends**: Usage by week number
- **Monthly Trends**: Usage by month
- **Per-Host Statistics**: Average session duration per computer

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Author

kikookraft
