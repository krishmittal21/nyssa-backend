const functions = require('@google-cloud/functions-framework');
const {Firestore} = require('@google-cloud/firestore');
const axios = require('axios');
const {v4: uuidv4} = require('uuid');

const db = new Firestore();

functions.http('chat', async (req, res) => {
  try {
    if (req.method !== 'POST') {
      res.status(405).send('Method Not Allowed');
      return;
    }

    const data = req.body;
    
    if (!data.userId || !data.tenantId) {
      res.status(400).send('Missing required parameters: userId, imageUrl, groupId, or tenantId');
      return;
    }

    const apiUrl = 'https://langchain-606795817007.us-central1.run.app';
    const requestData = {
      input: data.prompt || "Describe the image",
      userId: data.userId,
      threadId: data.threadId || "",
      image: data.imageUrl || ""
    };

    console.log('Sending request to LangChain API:', JSON.stringify(requestData));

    const response = await axios.post(apiUrl, requestData);
    
    if (!response.data || !response.data.success) {
      res.status(500).send('Failed to get a valid response from the LangChain API');
      return;
    }

    console.log('Received response from LangChain API:', JSON.stringify(response.data));

    const now = new Date().toISOString();
    const notificationId = uuidv4().toUpperCase();
    
    const notificationData = {
      category: "chats",
      createdBy: "ai_1",
      dateCreated: now,
      dateEdited: null,
      deeplink: `https://www.nysaa.ai/chat/${data.groupId}`,
      editedBy: null,
      from: "ai_1",
      isOffline: false,
      isUrgent: false,
      message: response.data.response,
      notificationId: notificationId,
      readAt: null,
      sentAt: now,
      status: "sent",
      tenantId: data.tenantId,
      type: "Nyssa",
      userId: data.userId
    };

    await db.collection('notifications').doc(notificationId).set(notificationData);

    console.log('Created notification:', notificationId);

    res.status(200).json({
      success: true,
      threadId: response.data.threadId,
      response: response.data.response,
      notificationId: notificationId
    });
    
  } catch (error) {
    console.error('Error in analyzeImageAndNotify:', error);
    res.status(500).send(`Error: ${error.message}`);
  }
});