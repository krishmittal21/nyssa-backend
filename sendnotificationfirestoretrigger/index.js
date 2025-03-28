const functions = require('@google-cloud/functions-framework');
const admin = require('firebase-admin');
const { v4: uuidv4 } = require('uuid');

admin.initializeApp();

const db = admin.firestore();

functions.cloudEvent('sendNotificationEvent', async (cloudEvent) => {
  try {
    const documentId = cloudEvent.subject ? cloudEvent.subject.split('/').pop() : null;
    if (!documentId) {
      console.log('No document ID found in the event.');
      return;
    }

    console.log(`Fetching notification with ID: ${documentId}`);

    const notificationDoc = await db.collection('notifications').doc(documentId).get();
    if (!notificationDoc.exists) {
      console.log(`Notification document with ID ${documentId} not found.`);
      return;
    }

    const notificationData = notificationDoc.data();

    const { userId, message, deeplink, tenantId, type, category, isUrgent, isOffline } = notificationData;

    if (!userId || !message || !type) {
      console.log('Missing required fields: userId, message, or type in notification data');
      return;
    }

    const userDoc = await db.collection('users').doc(userId).get();
    if (!userDoc.exists) {
      console.log(`User document for userId ${userId} not found.`);
      return;
    }

    const fcmToken = userDoc.get('fcmToken');
    if (!fcmToken) {
      console.log(`FCM token not found for user ${userId}.`);
      return;
    }

    const fcmTokeniPad = userDoc.get('fcmTokeniPad');
    const fcmTitle = type;

    const messagePayload = {
      notification: {
        title: fcmTitle,
        body: message,
      },
      data: {
        deeplink: deeplink || '',
        tenantId: tenantId || '',
        type: type || '',
        category: category || '',
        isUrgent: isUrgent ? 'true' : 'false',
        isOffline: isOffline ? 'true' : 'false',
        message: message
      },
      android: {
        priority: 'high',
        notification: {
          sound: 'default',
          priority: 'high',
          channelId: 'default',
        },
      },
      apns: {
        payload: {
          aps: {
            sound: 'default'
          },
        },
      },
    };

    await admin.messaging().send({ ...messagePayload, token: fcmToken });
    console.log('Notification sent successfully to primary device');

    if (fcmTokeniPad) {
      await admin.messaging().send({ ...messagePayload, token: fcmTokeniPad });
      console.log('Notification sent successfully to iPad');
    }

    await db.collection('notifications').doc(documentId).update({
      status: 'sent',
      sentAt: new Date().toISOString(),
    });

    console.log('Notification status updated successfully.');
  } catch (error) {
    console.error('Error sending notification:', error);
    await logError(error, cloudEvent, 'sendNotificationEvent');
  }
});

async function logError(error, cloudEvent, functionName) {
  const errorId = uuidv4().toUpperCase();

  const errorLog = {
    id: errorId,
    functionName,
    message: error.message,
    cloudEvent,
    createdAt: new Date().toISOString(),
  };

  try {
    await db.collection('errors').doc(errorId).set(errorLog);
    console.log('Error logged successfully.');
  } catch (logError) {
    console.error('Error logging the error:', logError);
  }
}