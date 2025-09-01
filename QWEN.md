# GemBooth Project Context

## Project Overview

GemBooth is a Flask-based web application that functions as an AI-powered photobooth. Users can capture photos from their webcam or upload existing images, which are then transformed using various artistic styles through the OpenRouter API.

### Key Features
- Webcam photo capture or file upload
- Multiple preset artistic styles (Renaissance, Cartoon, Anime, etc.)
- Custom prompt support for personalized transformations
- Generated images saved and displayed in a gallery
- Ability to create animated GIFs from original/generated image pairs

### Technologies Used
- **Backend**: Python Flask
- **Frontend**: HTML, CSS, JavaScript
- **API Integration**: OpenRouter API (using OpenAI Python client)
- **Image Processing**: Pillow library
- **Environment Management**: python-dotenv

## Project Structure

```
fun_image_gen/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── test.py             # API connectivity test script
├── metadata.json       # Web app metadata with camera permissions
├── README.md           # Project documentation
├── .gitignore          # Git ignore rules
├── static/             # Static assets
│   ├── style.css       # Main styles
│   ├── theme.css       # Theme and design tokens
│   └── generated_images/  # Storage for processed images (git-ignored)
├── templates/          # HTML templates
│   └── index.html      # Main application page
└── venv/               # Python virtual environment (git-ignored)
```

## Setup and Configuration

### Dependencies
Install required packages:
```bash
pip install -r requirements.txt
```

Key dependencies:
- Flask (web framework)
- openai (OpenRouter API client)
- python-dotenv (environment variable management)
- Pillow (image processing)

### Environment Variables
Create a `.env` file with the following required variable:
```
OPENROUTER_API_KEY=your_api_key_here
```

Optional variables:
- `SITE_URL`: HTTP referer header for API calls
- `SITE_TITLE`: Attribution title (defaults to "Gembooth")
- `IMAGE_MODEL`: Model name (defaults to "google/gemini-2.5-flash-image-preview:free")

## Running the Application

1. Install dependencies and set up `.env` file
2. Start the Flask server:
   ```bash
   python app.py
   ```
3. Access the application at http://localhost:5000

## Testing

Run the API connectivity test:
```bash
python test.py
```

## Development Notes

### Code Structure
- **app.py**: Contains all Flask routes and image processing logic
- **Frontend**: Single-page application with camera controls, style selection, and gallery
- **Styling**: CSS custom properties (design tokens) for consistent theming
- **Image Storage**: Images saved to `static/generated_images/` during runtime

### Predefined Styles
The application includes 11 predefined artistic styles with custom prompts:
1. Renaissance
2. Cartoon
3. Statue
4. 80s
5. 19th Century
6. Anime
7. Psychedelic
8. 8-bit
9. Big Beard
10. Comic Book
11. Old

### Image Processing Flow
1. Capture/upload image
2. Save original image locally
3. Send image + prompt to OpenRouter API
4. Receive transformed image
5. Save generated image locally
6. Display in gallery with original

## Important Directories and Files

- `static/generated_images/`: Runtime storage for all processed images (git-ignored)
- `templates/index.html`: Main UI with all frontend logic
- `static/style.css` and `static/theme.css`: Complete styling with design tokens
- `app.py`: Core application logic including Flask routes and OpenRouter integration