# Nyssa Backend

A cloud-native backend architecture built on Google Cloud Platform (GCP) leveraging Cloud Run, API Gateway, Eventarc, and Firebase.

## Overview

Nyssa Backend provides a scalable, event-driven system with serverless components to power the Nyssa application. The architecture is designed to be highly available, automatically scalable, and requires minimal operational overhead.

## Architecture Components

### Google Cloud Platform Services

- **Cloud Run**: Hosts containerized microservices that scale automatically based on traffic
- **API Gateway**: Serves as the entry point for client requests, providing routing, authentication, and rate limiting
- **Eventarc**: Enables event-driven architecture for asynchronous communication between services
- **Firebase**:
  - Firestore: NoSQL document database for application data
  - Firebase Storage: Object storage for user-generated content and media
  - Firebase Authentication: User authentication and authorization
  - Firebase Cloud Messaging (FCM): Push notification service for cross-platform messaging

### Cloud Functions

#### Gemini Image Generator
A Cloud Function that integrates with Google's Gemini AI model to generate images based on text prompts and optional reference images. Features include:
- Processing text and image inputs
- Generating images using Gemini 2.0 Flash model
- Storing generated images in Firebase Storage
- Returning both text responses and image URLs

#### Notification Service
A Cloud Function triggered by Firestore events to send notifications to users, using Eventarc to listen for database changes. Features include:
- Integration with Firebase Cloud Messaging (FCM)
- Device token management for multi-device support
- Customizable notification templates
- Support for both foreground and background notifications

## FCM Token Management

The Nyssa Backend implements a robust FCM token management system to ensure reliable delivery of push notifications:

### Token Registration
- Client devices register FCM tokens upon app installation or token refresh
- Tokens are stored in Firestore with user ID, device information, and timestamp
- Multiple tokens per user are supported for cross-device notifications

### Token Validation and Refresh
- Automatic token validation on each notification attempt
- Expired or invalid tokens are removed from the database
- Client SDK handles token refresh and server synchronization

### Security Considerations
- FCM tokens are stored with appropriate security rules in Firestore
- Access to token management endpoints is restricted by Firebase Authentication
- Tokens are encrypted during transmission using HTTPS

## Getting Started

### Prerequisites
- Google Cloud Platform account
- Firebase project
- Node.js and npm
- Python 3.9+
- Google Cloud CLI

### Installation

1. Clone the repository
   ```bash
   git clone https://github.com/krishmittal21/nyssa-backend.git
   cd nyssa-backend
   ```

2. Set up Firebase project
   ```bash
   # Install Firebase CLI if not already installed
   npm install -g firebase-tools
   
   # Login to Firebase
   firebase login
   
   # Initialize Firebase in the project directory
   firebase init
   ```

3. Configure Google Cloud project
   ```bash
   # Install Google Cloud SDK if not already installed
   # https://cloud.google.com/sdk/docs/install
   
   # Login to Google Cloud
   gcloud auth login
   
   # Set your project ID
   gcloud config set project YOUR_PROJECT_ID
   ```

### Configuration

1. Set up environment variables
   - Create a `.env` file in each service directory
   - Add required environment variables (see `.env.example` in each directory)

2. Configure Firebase
   - Enable Firestore, Storage, and Authentication in Firebase Console
   - Set up Firebase Cloud Messaging
   - Configure security rules for Firestore and Storage

3. Configure API Gateway
   - Create API configurations in GCP Console
   - Set up routes and authentication

### Deployment

#### Deploy Cloud Functions

```bash
# Deploy Gemini Image Generator
cd cf-geminiimagegenerator
gcloud functions deploy gemini-image-generator \
  --runtime python39 \
  --trigger-http \
  --allow-unauthenticated

# Deploy Notification Service
cd ../sendnotificationfirestoretrigger
gcloud functions deploy notification-service \
  --runtime nodejs16 \
  --trigger-event providers/cloud.firestore/eventTypes/document.create \
  --trigger-resource "projects/YOUR_PROJECT_ID/databases/(default)/documents/notifications/{notificationId}"
```

#### Deploy Cloud Run Services

```bash
# Build and deploy a service
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/service-name
gcloud run deploy service-name \
  --image gcr.io/YOUR_PROJECT_ID/service-name \
  --platform managed
```

## API Documentation

### Gemini Image Generator API

```
POST /generate-image
Content-Type: application/json

{
  "prompt": "A futuristic cityscape with flying cars",
  "referenceImageUrl": "https://storage.googleapis.com/...", // Optional
  "userId": "user123"
}
```

### Notification API

```
POST /send-notification
Content-Type: application/json
Authorization: Bearer {idToken}

{
  "userId": "user123",
  "title": "New Message",
  "body": "You have received a new message",
  "data": {
    "type": "message",
    "messageId": "msg456"
  }
}
```

## Security Considerations

- All API endpoints are secured with Firebase Authentication
- API Gateway provides rate limiting to prevent abuse
- Firestore security rules restrict data access to authorized users only
- Cloud Functions use principle of least privilege
- All data in transit is encrypted using HTTPS
- Sensitive environment variables are stored in Secret Manager

## Troubleshooting

### Common Issues

1. **FCM Token Registration Failures**
   - Verify Firebase configuration in client app
   - Check network connectivity
   - Ensure Firebase project is correctly set up

2. **Cloud Function Deployment Errors**
   - Check IAM permissions
   - Verify dependencies in requirements.txt or package.json
   - Review Cloud Build logs for detailed error messages

3. **API Gateway Connectivity Issues**
   - Verify API configuration
   - Check CORS settings
   - Ensure authentication is properly configured

### Logging and Monitoring

- Cloud Functions logs are available in Cloud Logging
- Set up Cloud Monitoring alerts for critical errors
- Use Firebase Crashlytics for client-side error reporting

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.