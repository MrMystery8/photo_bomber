# GemBooth

GemBooth is a small Flask web application that acts like an AI photobooth.  It lets you capture a picture from your webcam or upload an existing image and then applies fun image transformations by talking to the [OpenRouter](https://openrouter.ai) API.  Each transformation now includes a surprise "photobomber" character that is merged into the final image.

## Features

- Capture photos from your webcam or upload files from disk.
- Choose from a number of preset styles (Renaissance, Cartoon, Anime, etc.) or supply a custom prompt for the model.
- Generated images are saved alongside the original and displayed in the gallery.
- Combine original/generated pairs into an animated GIF.
- Every request adds a randomly selected photobomber into the scene.

## Requirements

The application is written in Python and depends on a few libraries:

```
$ pip install -r requirements.txt
```

The key dependencies are:

- [Flask](https://flask.palletsprojects.com) – web framework
- [openai](https://github.com/openai/openai-python) – client used to call the OpenRouter endpoint
- [python-dotenv](https://github.com/theskumar/python-dotenv) – loads environment variables from a `.env` file
- [Pillow](https://python-pillow.org) – image processing

## Configuration

The app expects a few environment variables.  They can be placed in a `.env` file for convenience.

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | ✅ | API key for OpenRouter.  The server refuses to start without it. |
| `SITE_URL` | optional | Used as the HTTP referer header when calling the model. |
| `SITE_TITLE` | optional | Title sent to OpenRouter for attribution (defaults to `Gembooth`). |
| `IMAGE_MODEL` | optional | Model name to request from OpenRouter (defaults to `google/gemini-2.5-flash-image-preview:free`). |

## Running the Application

1. Install dependencies and create a `.env` file with the values listed above.
2. Start the web server:

   ```bash
   python app.py
   ```

3. Open <http://localhost:5000> in a browser.  Allow camera access if you want to capture directly.
4. Pick a style or enter a custom prompt and take/upload a picture.  The generated image will appear in the gallery.  Select multiple results and click **Make GIF** to produce a simple animation.

Generated and source images are stored under `static/generated_images/` while the server is running.

## Photobombers

To make things more fun, each generation includes an extra "photobomber" image.  When a photo is submitted the server:

1. Randomly chooses an image from `static/photobomber/`.
2. Builds a prompt by taking the selected style prompt (or your custom text) and appending instructions to insert the photobomber.  The request sent to OpenRouter includes both the original photo and the photobomber image so the model can blend them together.

### Adding Your Own Photobombers

Place PNG or JPEG files in `static/photobomber/`.  The filename (without extension) is used to describe the character.  Optionally add a `.txt` file with the same name to supply a more detailed description that will be appended to the prompt.  Restart the server and the new photobomber will be picked at random for future requests.

## Testing

A minimal script `test.py` is included. It uses the `OPENROUTER_API_KEY` to attempt a simple request against the OpenRouter API. Run it with:

```bash
python test.py
```

If the key is missing or invalid, the script prints the error. The repository currently does not contain formal unit tests.

## Metadata

`metadata.json` describes the application for environments that support web app metadata.  It requests camera permissions to enable the webcam capture feature.

## License

This project is provided as-is for demonstration purposes.

