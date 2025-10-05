# Polyglot E-Book Demo (Flask)

## Overview
A demo e-book subscription backend using polyglot persistence:
- MySQL for users/payments
- MongoDB for e-book documents
- Neo4j for recommendations
- Redis for session caching
Includes a minimal HTML frontend and API endpoints.

## Quick start (local)
1. Install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Start databases locally or via Docker (MySQL, MongoDB, Redis, Neo4j).
3. Create `.env` from `.env.example` and adjust credentials.
4. Initialize MySQL schema: `mysql -u root < mysql/schema.sql` (or use your preferred client)
5. Seed sample data:
   ```bash
   python seed.py
   ```
6. Run the app:
   ```bash
   python app.py
   ```
7. Open `http://localhost:5000` to view the minimal frontend.

## Endpoints
- `POST /api/signup` — JSON `{username,email,password,tier}`
- `POST /api/login` — JSON `{email,password}` returns JWT
- `GET  /api/search?q=` — search ebooks
- `POST /api/choose` — JSON `{user_id,book_id}`
- `GET  /api/recommend?user_id=` — recommendations

## Notes
- This is a demo skeleton for rapid prototyping. Do not use in production without hardening (validate inputs, secure secrets, use TLS, rate-limit, etc.).
