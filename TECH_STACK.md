# Sneaker Studio: technology overview

## AI models

The application uses an OpenAI API key for both AI tasks:

| Task | Default model | Purpose |
| --- | --- | --- |
| Sneaker concept text | `gpt-4o-mini` | Creates the structured JSON design brief: name, materials, colorways, features, audience, and price. |
| Sneaker render | `gpt-image-2.5-flare` | Creates a product render from the completed concept. |

Both default models can be changed without editing code by adding `OPENAI_TEXT_MODEL` or `OPENAI_IMAGE_MODEL` to `.env`.

## Technology stack

- **Backend:** Python and Flask
- **AI provider:** OpenAI API, accessed with the `openai` Python package
- **Frontend:** HTML templates, vanilla JavaScript, and CSS
- **Image storage:** Generated PNG files are saved in `static/generated/` and served by Flask
- **Configuration:** `python-dotenv` loads local variables from `.env`

## Request flow

1. The browser sends the design choices to `POST /generate`.
2. The OpenAI text model creates the sneaker concept as JSON.
3. The concept and selected colors are turned into a product-render prompt.
4. The OpenAI image model creates a PNG sneaker render.
5. Flask saves the image and returns its URL with the concept JSON.
6. The Studio page displays the render and concept details.

## Required environment variable

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_TEXT_MODEL=gpt-4o-mini
OPENAI_IMAGE_MODEL=gpt-image-2.5-flare
HCAPTCHA_SITE_KEY=your_hcaptcha_site_key
HCAPTCHA_SECRET=your_hcaptcha_secret
```

Never commit `.env` or paste API keys into source files. Revoke any key that has
been shared publicly and replace it in `.env`.

The Studio page loads hCaptcha from `js.hcaptcha.com`, renders the widget using
`HCAPTCHA_SITE_KEY`, and sends the resulting token to Flask. Flask verifies that
token with hCaptcha using `HCAPTCHA_SECRET`. Configure both keys and allow the
domain where the app is running in the hCaptcha dashboard; local development
typically uses `localhost`.