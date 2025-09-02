import os
import base64
from io import BytesIO
from flask import Flask, render_template, request, jsonify, url_for
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image
import uuid
import random

load_dotenv()

app = Flask(__name__)

# Configure the OpenRouter API key
api_key = os.environ.get("OPENROUTER_API_KEY")
if not api_key:
    raise ValueError("OPENROUTER_API_KEY not found in .env file. Please set it.")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

# In-memory store for images
image_store = {}


def get_random_photobomber_b64(output_mime: str = 'image/jpeg'):
    """Return base64-encoded data of a random photobomber image, encoded
    to match the requested MIME (e.g., 'image/jpeg' or 'image/png')."""
    photobomber_dir = os.path.join('static', 'photobomber')
    os.makedirs(photobomber_dir, exist_ok=True)
    candidates = [
        f
        for f in os.listdir(photobomber_dir)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ]

    if not candidates:
        return None, None

    filename = random.choice(candidates)
    path = os.path.join(photobomber_dir, filename)
    # Choose PIL save format from MIME
    fmt = 'JPEG'
    if isinstance(output_mime, str) and output_mime.lower() == 'image/png':
        fmt = 'PNG'

    with Image.open(path) as img:
        buf = BytesIO()
        if fmt == 'JPEG':
            img.convert('RGB').save(buf, format=fmt)
        else:
            # Preserve alpha for PNG output
            img.convert('RGBA').save(buf, format=fmt)
        b64_random = base64.b64encode(buf.getvalue()).decode('utf-8')
    return b64_random, path

# Predefined modes for the photobooth
modes = {
  "renaissance": {
    "name": "Renaissance",
    "emoji": "🎨",
    "prompt": "Renaissance oil painting on canvas with sfumato and chiaroscuro; muted earth tones (umber, ochre, sienna); soft edges with subtle brush texture; warm varnish color grade; gentle filmic contrast and 50mm perspective. Apply this style uniformly to the entire image and any inserted subject."
  },
  "cartoon": {
    "name": "Cartoon",
    "emoji": "😃",
    "prompt": "Flat-color cartoon style: minimal lines, thick clean outlines (single weight), 2–3 tones per region, saturated playful palette, no gradients or textures, simple cel shading. Apply this style uniformly to the entire image and any inserted subject."
  },
  "statue": {
    "name": "Statue",
    "emoji": "🏛️",
    "prompt": "Classical marble statue look: convert subjects, clothing, and surfaces into carved marble; grayscale stone palette; subtle chisel marks; soft subsurface scattering hints; studio-like top-light; no pigment color. Apply this style uniformly to the entire image and any inserted subject."
  },
  "80s": {
    "name": "80s",
    "emoji": "✨",
    "prompt": "1980s yearbook photo: studio flash with soft fill, pastel gradient backdrop, gentle vignette, mild film grain, period-accurate color grade, hair and clothing may be updated to match the era. Apply this style uniformly to the entire image and any inserted subject."
  },
  "19century": {
    "name": "19th Cent.",
    "emoji": "🎩",
    "prompt": "Daguerreotype: monochrome silver tone, shallow dynamic range, halation glow, period lens falloff and vignetting, plate artifacts and slight motion blur; period-appropriate background and attire allowed. Apply this style uniformly to the entire image and any inserted subject."
  },
  "anime": {
    "name": "Anime",
    "emoji": "🍣",
    "prompt": "Photorealistic anime: crisp line art, controlled cel shading, soft skin gradients, stylized speculars, clean backgrounds, saturated yet balanced palette, minimal grain. Apply this style uniformly to the entire image and any inserted subject."
  },
  "psychedelic": {
    "name": "Psychedelic",
    "emoji": "🌈",
    "prompt": "1960s psychedelic poster: hand-drawn look with bold flat colors and swirling organic shapes, high-contrast complementary palette, screenprint texture, no text. Apply this style uniformly to the entire image and any inserted subject."
  },
  "8bit": {
    "name": "8-bit",
    "emoji": "🎮",
    "prompt": "8-bit pixel art: render on an ~80×80 pixel grid, bright NES-like palette, hard edges, no anti-aliasing, 1–2 px outlines, simple dithering for gradients, minimal shading. Apply this style uniformly to the entire image and any inserted subject."
  },
  "beard": {
    "name": "Big Beard",
    "emoji": "🧔🏻",
    "prompt": "Add an oversized, realistic beard to the main subject while preserving the original photographic style (color grade, lighting, noise, sharpness). Ensure any inserted subject matches the same look. Avoid altering the scene beyond the beard addition."
  },
  "comic": {
    "name": "Comic Book",
    "emoji": "💥",
    "prompt": "Vintage comic panel: bold black inks, halftone dots at 45°, limited CMYK palette, slight off-register charm, paper texture; speech bubbles allowed. Apply this style uniformly to the entire image and any inserted subject."
  },
  "old": {
    "name": "Old",
    "emoji": "👵🏻",
    "prompt": "Dramatically age the primary person: realistic wrinkles, skin sag, hair graying/thinning, age spots, posture changes; maintain the original photographic style (lighting, grade, grain, sharpness). Ensure any inserted subject matches the same style."
  }
}

@app.route('/')
def index():
    return render_template('index.html', modes=modes)

@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({"error": "Missing image in request"}), 400

    try:
        image_data_url = data['image']
        # Detect MIME type from the incoming data URL so we can mirror it
        input_mime = 'image/jpeg'
        if isinstance(image_data_url, str) and image_data_url.startswith('data:image') and ';base64,' in image_data_url:
            try:
                header = image_data_url.split(',')[0]  # e.g., 'data:image/jpeg;base64'
                input_mime = header.split(':', 1)[1].split(';', 1)[0]  # 'image/jpeg'
            except Exception:
                input_mime = 'image/jpeg'
            b64_image = image_data_url.split(',')[1]
        else:
            # If the client sent raw base64, assume JPEG by default
            b64_image = image_data_url
            input_mime = 'image/jpeg'

        prompt = data.get('prompt', '')
        mode = data.get('mode', 'custom')

        image_bytes = base64.b64decode(b64_image)
        image = Image.open(BytesIO(image_bytes)).convert('RGB')
    except Exception as e:
        return jsonify({"error": f"Invalid image data: {e}"}), 400

    # Save original image
    image_id = str(uuid.uuid4())
    input_filename = f"{image_id}_input.jpg"
    input_path = os.path.join('static', 'generated_images', input_filename)
    image.save(input_path, format='JPEG')

    generated_data_url = None
    api_error = None
    photobomber_path = None
    photobomber_message = None
    try:
        referer = os.environ.get('SITE_URL') or request.headers.get('Referer') or ''
        title = os.environ.get('SITE_TITLE') or 'Gembooth'
        api_model = os.environ.get('IMAGE_MODEL', 'google/gemini-2.5-flash-image-preview:free')

        b64_random, photobomber_path = get_random_photobomber_b64(input_mime)

        # Build prompt, auto-instructing the model to perform a photobomb when present
        base_prompt = prompt or modes.get(mode, {}).get('prompt', '')
        if b64_random:
            auto_instr = (
                '''You are an image editor and compositor.

INPUTS
- Image A: the user’s original scene to edit.
- Image B: a photobomber subject to extract and insert into Image A.

OBJECTIVE
Insert the subject from Image B into Image A as a subtle, sneaky photobomb that is fully consistent with the overall visual style of the final image.

GLOBAL STYLE UNIFICATION
- Treat the user/mode prompt text as the authoritative style specification for the whole output.
- If Image A already exhibits a stylization (e.g., anime/cartoon/renaissance/comic/8-bit), analyze and adopt that exact style.
- Apply the same style pipeline to the inserted subject: medium/material (oil paint, pencil, halftone, marble, pixel grid), line weight/edge handling, palette and tonal range, texture/noise pattern, shading model, and global color grade/LUT.
- Ensure the photobomber never reads as a separate layer: identical rendering technique, resolution/sharpness, and post-processing as Image A.

SNEAKY PHOTOBOMBING
- Placement mode: [edge-of-frame | mid-background crowd | behind foreground object | reflection in glass/mirror].
- Sneakiness level: high → subject is off-center, partially occluded, and not drawing immediate focus; avoid direct eye contact with the camera.
- Keep outside the 3x3 grid center; prefer edges, background lanes, or reflective surfaces.
- Scale and pose to match local context (heights, seating/standing level, furniture scale).

COMPOSITION & OCCLUSION
- Do not cover important faces or primary subjects in Image A (use a saliency/face-protection pass).
- Use plausible occluders from Image A (doorframe, shoulder, plant, railing) to sell depth and integration.

PERSPECTIVE & GEOMETRY
- Match camera height, horizon line, vanishing directions, and lens characteristics (distortion/FOV) from Image A.

LIGHTING & COLOR
- Match light direction, intensity, and color temperature.
- Add physically plausible contact shadows and soft ambient occlusion at contact points.
- Reproduce specular highlights/roughness consistent with surrounding materials.
- Conform to Image A’s global grade: white balance, contrast, saturation, and any LUT-like look.

FOCUS, MOTION & NOISE
- Match depth of field: blur the subject appropriately if its plane is out of focus.
- Add motion blur when consistent with local motion in Image A.
- Match sensor noise/grain, sharpening, compression artifacts, and any halftone/pixel structure for the chosen style.

EDGE TREATMENT & MATTE
- Perform hair-aware matting; remove halos and fringing.
- Feather edges and frequency-match to avoid a cutout look.

REFLECTIONS & INTERACTIONS (if applicable)
- If near reflective/glossy surfaces, add a correctly blurred/dimmed reflection with accurate perspective.
- Ensure correct shadow length and softness based on Image A’s key/fill lighting.

PROTECTIONS & AVOID
- Do not resize or crop Image A; preserve all original people and background.
- Avoid center placement and overlapping primary faces.
- Avoid mismatched sharpness, color cast, HDR pop, or inconsistent line/texture that breaks style cohesion.

OUTPUT
Return only the edited version of Image A at its original resolution. No captions, borders, or extra canvas.'''
            )
            full_prompt = (base_prompt + "\n\n" + auto_instr).strip()
        else:
            photobomber_message = "Photobomber directory is empty."
            full_prompt = base_prompt

        # Send the exact user data URL for the first image when possible, to preserve format
        user_image_url = (
            image_data_url if (isinstance(image_data_url, str) and image_data_url.startswith('data:image'))
            else f"data:{input_mime};base64,{b64_image}"
        )

        # Photobomber encoded to the same MIME as the user's image
        content = [
            {"type": "text", "text": full_prompt},
            {"type": "image_url", "image_url": {"url": user_image_url}},
        ]
        if b64_random:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{input_mime};base64,{b64_random}"},
            })

        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": referer,
                "X-Title": title,
            },
            model=api_model,
            messages=[
                {
                    "role": "user",
                    "content": content,
                }
            ],
            modalities=["image", "text"],
        )

        comp_dict = completion.model_dump() if hasattr(completion, 'model_dump') else getattr(completion, '__dict__', {})
        images = None
        try:
            choices = comp_dict.get('choices') or []
            if choices:
                message = choices[0].get('message') or {}
                images = message.get('images') or []
        except Exception:
            images = []

        if images and isinstance(images, list):
            first = images[0]
            if isinstance(first, dict):
                generated_data_url = ((first.get('image_url') or {}).get('url'))
        
        if not generated_data_url:
            text_detail = None
            try:
                if choices and isinstance(message, dict):
                    text_detail = message.get('content')
            except Exception:
                pass
            msg = "Model returned no images in response."
            if text_detail:
                msg += f" Detail: {text_detail}"
            raise RuntimeError(msg)
    except Exception as e:
        api_error = str(e)

    if api_error:
        app.logger.error(f"OpenRouter API error: {api_error}")
        return jsonify({"error": f"OpenRouter API error: {api_error}"}), 502

    if not generated_data_url:
        msg = "API returned no image content."
        app.logger.error(msg)
        return jsonify({"error": msg}), 502

    # Save generated image
    output_filename = f"{image_id}_output.png"
    output_path = os.path.join('static', 'generated_images', output_filename)
    
    # The generated_data_url is a base64 string, so we need to decode it
    if generated_data_url.startswith('data:image') and ',' in generated_data_url:
        generated_b64_image = generated_data_url.split(',')[1]
    else:
        generated_b64_image = generated_data_url

    generated_image_bytes = base64.b64decode(generated_b64_image)
    generated_image = Image.open(BytesIO(generated_image_bytes))
    generated_image.save(output_path, format='PNG')


    image_store[image_id] = {
        'input': input_path,
        'output': output_path,
        'mode': mode,
    }
    if photobomber_path:
        image_store[image_id]['photobomber'] = photobomber_path

    return jsonify({
        'id': image_id,
        'output_url': url_for('static', filename=f'generated_images/{output_filename}'),
        'input_url': url_for('static', filename=f'generated_images/{input_filename}'),
        'mode': mode,
        'emoji': modes.get(mode, {}).get('emoji', '✨'),
        'api_error': api_error,
        'photobomber_message': photobomber_message,
    })

@app.route('/make_gif', methods=['POST'])
def make_gif():
    data = request.get_json()
    photo_ids = data['photo_ids']
    
    images = []
    for photo_id in photo_ids:
        if photo_id in image_store:
            input_path = image_store[photo_id]['input']
            output_path = image_store[photo_id]['output']
            
            input_img = Image.open(input_path).resize((256, 256))
            output_img = Image.open(output_path).resize((256, 256))
            
            images.append(input_img)
            images.append(output_img)

    if not images:
        return jsonify({'error': 'No images found'}), 400

    gif_io = BytesIO()
    images[0].save(gif_io, format='GIF', save_all=True, append_images=images[1:], duration=500, loop=0)
    gif_io.seek(0)
    
    gif_b64 = base64.b64encode(gif_io.getvalue()).decode('utf-8')
    
    return jsonify({'gif_url': f"data:image/gif;base64,{gif_b64}"})


if __name__ == '__main__':
    app.run(debug=True)
