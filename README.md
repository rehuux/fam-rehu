# Fam ID to Phone Number API

A Flask-based API to retrieve phone numbers from Fam IDs with automatic unblocking feature.

## Features
- Get phone number from Fam ID
- Automatic unblocking after retrieval
- Authentication testing
- View blocked list
- Cache system for faster lookups

## Endpoints
- `GET /` - Home page with API info
- `GET /get-number?id=username@fam` - Main endpoint
- `GET /auth-test` - Test authentication
- `GET /blocked` - View blocked list
- `GET /credits` - Credits information
- `GET /health` - Health check

## Deployment on Vercel
1. Push these files to GitHub
2. Import to Vercel
3. Deploy automatically

## Credits
- Owner: Syed Rehan
- Developer: @istgrehu
- Version: 3.2
