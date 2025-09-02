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

# Feature flags / config
PHOTOBOMBER_ENABLED = (
    os.environ.get('PHOTOBOMBER_ENABLED', 'true').strip().lower() in ('1', 'true', 'yes', 'on')
)


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
    "prompt": "STRICT Renaissance oil painting on canvas: strong chiaroscuro + sfumato, muted umber/ochre/sienna palette, visible brushwork, warm varnish grade; apply uniformly to the entire image."
  },
  "cartoon": {
    "name": "Cartoon",
    "emoji": "😃",
    "prompt": "HARD cartoon conversion: thick uniform black outlines, 2–3 flat tones per region, saturated playful palette, no gradients or textures; apply to the whole image."
  },
  "statue": {
    "name": "Statue",
    "emoji": "🏛️",
    "prompt": "FULL marble conversion: turn all subjects and surfaces into carved white marble; grayscale stone with subtle chisel marks, soft studio top‑light; zero pigment color across the image."
  },
  "80s": {
    "name": "80s",
    "emoji": "✨",
    "prompt": "AUTHENTIC 1980s studio portrait: pastel airbrushed backdrop, direct flash with soft fill, mild film grain, gentle vignette, era‑correct color grade applied globally."
  },
  "19century": {
    "name": "19th Cent.",
    "emoji": "🎩",
    "prompt": "TRUE daguerreotype plate: monochrome silver tone, low dynamic range, halation glow, lens falloff + vignette, plate streaks/blemishes; accept slight motion blur; apply to all content."
  },
  "anime": {
    "name": "Anime",
    "emoji": "🍣",
    "prompt": "FORCE photorealistic‑anime look: crisp line art, controlled cel shading, soft skin gradients, clean backgrounds, saturated yet balanced palette, no photographic texture or grain; apply uniformly."
  },
  "psychedelic": {
    "name": "Psychedelic",
    "emoji": "🌈",
    "prompt": "BOLD 1960s psychedelic poster: flat high‑contrast complementary colors, swirling organic shapes, screenprint texture/misregistration; apply across the whole image."
  },
  "8bit": {
    "name": "8-bit",
    "emoji": "🎮",
    "prompt": "STRICT 8‑bit pixel art: ~80×80 grid, limited bright NES palette, hard 1–2 px outlines, no anti‑aliasing; use coarse dithering for gradients; convert the full image."
  },
  "beard": {
    "name": "Big Beard",
    "emoji": "🧔🏻",
    "prompt": "Add an oversized realistic beard ONLY; preserve original photographic lighting/grade/grain/sharpness elsewhere; do not alter other scene elements."
  },
  "comic": {
    "name": "Comic Book",
    "emoji": "💥",
    "prompt": "VINTAGE comic halftone: heavy black inks, 45° CMYK dots, limited colors, slight off‑register charm, paper texture; apply globally."
  },
  "old": {
    "name": "Old",
    "emoji": "👵🏻",
    "prompt": "HARD age‑up: convincing wrinkles, skin sag, age spots, gray/thin hair and posture changes; retain the original photo grade/lighting; avoid other scene edits."
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

        b64_random = None
        if PHOTOBOMBER_ENABLED:
            b64_random, photobomber_path = get_random_photobomber_b64(input_mime)
        else:
            photobomber_message = 'Photobomber disabled by PHOTOBOMBER_ENABLED=false'

        # Build prompt, auto-instructing the model to perform a photobomb when present
        base_prompt = prompt or modes.get(mode, {}).get('prompt', '')
        if b64_random:
            auto_instr = (
                """
You are an image editor. Use Image A as the base and insert the subject from Image B as a subtle photobomb. Adopt the selected mode’s art style as the single source of truth and apply it uniformly to the entire result and to the inserted subject.

Style lock (must match exactly):
- Rendering medium/technique (oil paint, cel‑shaded anime, halftone, marble, pixel grid)
- Line/edge handling and outline weight
- Palette and tonal range (hues, saturation, contrast)
- Texture/noise model (brush texture, paper grain, halftone dots, pixelation)
- Global grade/LUT, lens characteristics (FOV/distortion), and resolution/sharpness

Blend the insert naturally:
- Match perspective and camera height/horizon; scale/pose to local context
- Match lighting direction/intensity/color temperature; add contact shadows and soft AO
- Match depth of field and any motion blur; match grain/sharpening/compression
- Use plausible occlusion from Image A (doorframe, shoulder, plant, railing)
- Placement: prefer edge/background or reflections; avoid center and blocking important faces; avoid direct eye contact

Generative adjustment (preserve identity):
- You may re‑pose, scale, rotate, and reposition the photobomber; inpaint/outpaint missing or occluded regions; adjust clothing folds, hands/limbs, and minor accessories; nudge colors and shading; and locally relight to match the scene—so long as the person’s identity remains intact.
- Preserve recognizable identity cues: facial structure/proportions, eyes/nose/mouth spacing, hairstyle silhouette, and primary clothing pattern/colors. If a choice risks identity loss, choose the smallest edit that still blends perfectly.

Edge/matte quality:
- Hair‑aware matting; remove halos/fringing; feather to local frequency; no cutout look

Protections:
- Do not crop or resize Image A; preserve all original people and background
- Output only the edited Image A at its original resolution (no borders or captions)
"""
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
        'used_prompt': full_prompt,
        'model': api_model,
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
