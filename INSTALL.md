# Quick Installation Guide

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Or if you prefer to use a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Setup Configuration

```bash
python3 setup.py
```

This will create a `.env` file. Edit it and add your OpenAI API key:

```env
OPENAI_API_KEY=sk-your-actual-openai-api-key-here
```

## 3. Run the Application

```bash
python3 app.py
```

Open your browser to: http://localhost:5000

## 4. Start Your First Search

1. Click "New Search"
2. Enter what you're looking for (e.g., "overdose response teams")
3. Select a state (North Carolina has the most sample counties)
4. Click "Start Search"
5. Watch the progress in real-time!

## Sample Search Queries

- "overdose response teams or opioid crisis response teams"
- "mental health crisis intervention teams" 
- "substance abuse treatment centers"
- "emergency management agencies"

## Getting OpenAI API Key

1. Go to https://platform.openai.com/
2. Create an account or sign in
3. Go to API Keys section
4. Create a new API key
5. Copy and paste it into your `.env` file

## Troubleshooting

- **"No module named 'flask'"**: Run `pip install -r requirements.txt`
- **"API key not found"**: Check your `.env` file has the correct OpenAI API key
- **Database errors**: Delete `prospector.db` file and restart the app
