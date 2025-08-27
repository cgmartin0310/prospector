# Prospector - AI-Powered Research Tool

Prospector is an intelligent research tool that uses AI to systematically search through every county in a US state to find specific types of organizations. It's designed to prevent AI hallucination by conducting isolated research sessions for each county.

## Features

- **Systematic County-by-County Research**: Searches every county in a selected state
- **Isolated AI Sessions**: Uses fresh AI conversations for each county to prevent hallucination
- **Real-time Progress Tracking**: Monitor search progress as it happens
- **Organization Database**: Stores all found organizations with contact information
- **Export Capabilities**: Export results to CSV for further analysis
- **Web Interface**: User-friendly dashboard for managing searches

## Use Cases

- Finding overdose response teams across a state
- Locating mental health crisis intervention teams
- Identifying substance abuse treatment centers
- Researching emergency management agencies
- Any systematic organization research across geographic areas

## Setup Instructions

### 1. Prerequisites

- Python 3.8 or higher
- OpenAI API key

### 2. Installation

```bash
# Clone or download the project
cd prospector

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key_here
SECRET_KEY=your_secret_key_here
FLASK_ENV=development
```

### 4. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## How It Works

### 1. Define Your Search
Describe what type of organizations you're looking for:
- "overdose response teams or opioid crisis response teams"
- "mental health crisis intervention teams"
- "substance abuse treatment centers"

### 2. Select State
Choose which state to research. The system will automatically search through all counties in that state.

### 3. AI Research Process
For each county, the system:
- Creates a fresh AI conversation (prevents hallucination)
- Searches for organizations matching your criteria
- Extracts structured information (name, contact, description)
- Saves results to the database
- Pauses between searches to respect API limits

### 4. View Results
- Real-time progress tracking
- Detailed organization information
- Export to CSV for further analysis
- Filter and sort results

## Database Schema

### States and Counties
- Pre-loaded with US states and counties
- Currently includes sample counties for major states
- Can be extended with complete county data

### Prospecting Jobs
- Track search parameters and progress
- Monitor status (pending, running, completed, failed)
- Store timing and error information

### Search Results
- Organization details (name, description, contact)
- Confidence scores from AI
- Raw AI responses for debugging
- Verification status

## API Endpoints

- `GET /` - Dashboard
- `GET /start-search` - New search form
- `POST /start-search` - Start new job
- `GET /job/<id>` - Job status and results
- `GET /results` - All results with filtering
- `GET /api/job/<id>/status` - Job status API
- `GET /api/job/<id>/export` - Export job results
- `GET /api/result/<id>` - Result details API

## Customization

### Adding More Counties
Extend the `DataLoader` class to load complete US county data from Census API or other sources.

### Different AI Models
Modify the `AIService` to use different AI models or providers.

### Custom Search Logic
Extend the `ProspectorService` to add custom search patterns or filtering.

## Cost Considerations

- Each county search uses 1 AI API call
- Costs depend on your search query complexity and AI model used
- Built-in delays help manage API rate limits
- Progress can be paused/resumed to control costs

## Example Search Results

For "overdose response teams in North Carolina":
- Alamance County: Alamance County Opioid Response Team
- Burke County: Burke County Crisis Response Team
- Cumberland County: Cumberland County Overdose Prevention Coalition
- Durham County: Durham County Harm Reduction Coalition

## Troubleshooting

### Common Issues

1. **OpenAI API Key Not Working**
   - Verify your API key in the `.env` file
   - Check your OpenAI account has credits

2. **Database Issues**
   - Delete `prospector.db` and restart to reset database
   - Check file permissions in the project directory

3. **Search Not Starting**
   - Check the browser console for JavaScript errors
   - Verify the Flask server is running

4. **No Results Found**
   - Try broader search terms
   - Check if the county actually has such organizations
   - Review raw AI responses for debugging

## Future Enhancements

- Integration with web scraping for better data collection
- Duplicate detection and organization merging
- User verification and rating system
- Integration with mapping services
- Automated scheduling of periodic searches
- Multi-state search capabilities

## Contributing

This is a prototype application. Areas for improvement:
- Complete US county database
- Better error handling
- Performance optimizations
- Additional export formats
- Mobile-responsive design

## License

This project is provided as-is for educational and research purposes.
