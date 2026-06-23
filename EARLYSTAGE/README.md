# LionexAI - Early Stage Landing Site

A premium single-page landing site for **LionexAI**, built with HTML5, CSS3, and vanilla JavaScript only (no frameworks, no build step).

## Files

- `index.html` - semantic markup, SEO/Open Graph meta, JSON-LD structured data
- `styles.css` - design tokens, responsive layout, components, animations
- `script.js` - sticky nav, mobile menu, scroll reveal, hero particle canvas, form validation
- `logo.png` - brand logo

## Run locally

It's a static site - just open `index.html` in a browser. For a local server (recommended so relative paths/fonts behave like production):

```bash
# Python
python -m http.server 8080

# or Node
npx serve .
```

Then visit `http://localhost:8080`.

## Deploy

Upload the contents of this folder to any static host (Netlify, Vercel, Cloudflare Pages, GitHub Pages, S3, etc.). No build process required.

Before going live, update absolute URLs (`https://lionexai.com/`) in the SEO/OG/JSON-LD tags inside `index.html` if the domain changes.

## Notes

- The contact form is front-end only (client-side validation, no backend submission).
- Respects `prefers-reduced-motion`; the particle animation pauses when off-screen or when the tab is hidden.
- This site reflects a product in active development; content is informational only and not financial advice.
